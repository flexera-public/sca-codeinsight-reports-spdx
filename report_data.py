'''
Copyright 2023 Flexera Software LLC
See LICENSE.TXT for full license text
SPDX-License-Identifier: MIT

Author : sgeary  
Created On : Tue Aug 29 2023
Modified By : sarthak
Modified On: Mon 07 2025
File : report_data.py
'''

import logging, unicodedata, uuid, re, hashlib
import report_data_db
import SPDX_license_mappings, purl
import report_data_files

logger = logging.getLogger(__name__)

#-------------------------------------------------------------------#
def gather_data_for_report(projectID, reportData):
    logger.info("Entering gather_data_for_report")

    SPDXIDPackageNamePattern = r"[^a-zA-Z0-9\-\.]"  # PackageName is a unique string containing letters, numbers, ., and/or - so get rid of the rest
    reportDetails={}
    packages = []
    #packageFiles = {} # Needed for tag/value format since files needed to be inline with packages
    hasExtractedLicensingInfos = {}
    relationships = []
    files = []
    filesNotInInventory = []
    filePathsNotInInventoryToID = {}
    projectCopyrights = []

    reportOptions = reportData["reportOptions"]
    releaseVersion = "N/A"

    # Parse report options
    includeChildProjects = reportOptions["includeChildProjects"]  # True/False
    includeNonRuntimeInventory = reportOptions["includeNonRuntimeInventory"]  # True/False
    includeFileDetails = reportOptions["includeFileDetails"]  # True/False
    includeUnassociatedFiles = reportOptions["includeUnassociatedFiles"]  # True/False
    createOtherFilesPackage = reportOptions["createOtherFilesPackage"]  # True/False
    includeCopyrightsData = reportOptions["includeCopyrightsData"] # True/False

    project_Name = report_data_db.get_projects_data(projectID)
    documentName = project_Name.replace(" ", "_")
    if reportOptions["includeChildProjects"]:
        projectList = report_data_db.get_child_projects(projectID)
    else:
        projectList = []
        projectList.append(projectID)
    topLevelProjectName = project_Name

    SPDXVersion = "SPDX-2.3"
    documentSPDXID = "SPDXRef-DOCUMENT"
    documentNamespace  = "http://spdx.org/spdxdocs/" + documentName + "-" + str(uuid.uuid1())
    creator = "Tool: Revenera SCA - Code Insight %s" %releaseVersion
    dataLicense = "CC0-1.0"   

    # Create a root pacakge to reflect the application itself
    rootPackageName = re.sub('[^a-zA-Z0-9 \n\.]', '-', topLevelProjectName.replace(" ", "-")) # Replace spec chars with dash
    rootSPDXID = "SPDXRef-Pkg-" + rootPackageName + "-" + str(projectID)

    packageDetails = {}
    packageDetails["SPDXID"] = rootSPDXID
    packageDetails["name"] = topLevelProjectName
    packageDetails["supplier"] = "Organization: None"
    packageDetails["homepage"] = "NOASSERTION"
    packageDetails["downloadLocation"] = "NOASSERTION"
    packageDetails["copyrightText"] = "NOASSERTION" 
    packageDetails["licenseDeclared"] = "NOASSERTION"
    packageDetails["licenseConcluded"] = "NOASSERTION"
    packageDetails["filesAnalyzed"] = False
    

    packages.append(packageDetails)

    # Manange the relationship for this top level package
    packageRelationship = {}
    packageRelationship["spdxElementId"] = documentSPDXID
    packageRelationship["relationshipType"] = "DESCRIBES"
    packageRelationship["relatedSpdxElement"] = rootSPDXID
    
    if packageRelationship not in relationships:
        relationships.append(packageRelationship)

    #  Gather the details for each project and summerize the data
    for project in projectList:
        projectID = project
        projectName = report_data_db.get_projects_data(projectID)

        print("        Collect data for project: %s" %projectName)

        if includeFileDetails:

            # Collect file level details for files associated to this project
            print("            Collect file level details.")
            logger.info("            Collect file level details.")
            filePathtoID, projectFileDetails, hasExtractedLicensingInfos = report_data_files.manage_file_details(projectID, hasExtractedLicensingInfos, includeUnassociatedFiles, includeCopyrightsData)
            # Create a full list of filename to ID mappings for non inventory items
            if includeUnassociatedFiles:
                filePathsNotInInventoryToID.update(filePathtoID["notInInventory"])

            print("            File level details for project has been collected")
            logger.info("            File level details for project has been collected")

        print("            Collect inventory details.")
        logger.info("            Collect inventory details")
        inventoryItems = report_data_db.get_inventory_data(projectID)
        if inventoryItems is None:
            inventoryItems = []
        inventoryItemsCustom = report_data_db.get_inventory_data_custom(projectID)
        if inventoryItemsCustom is not None and inventoryItemsCustom != []:
            inventoryItems += inventoryItemsCustom
        print("            Inventory has been collected.")
        logger.info("            Inventory has been collected.")      
        
        # To check inventory type between License Only or WIP
        inventoriesNotInRepo = report_data_db.get_inventories_not_in_repo(projectID)    # To handle WIP and License Only inventories
        inventoryItems += inventoriesNotInRepo

        for inventoryItem in inventoryItems:
            supplier = None # Set a default value to compare with
            inventoryType = inventoryItem["type"]

            # Check to see if this is a runtime dependency or not (added in 2023R3)
            if "dependencyScope" in inventoryItem:
                dependencyScope = inventoryItem["dependencyScope"]
                
                # Set dependency scope based on the value
                if dependencyScope is None:
                    dependencyScope = "NOT_AVAILABLE"
                elif dependencyScope == "1":
                    dependencyScope = "NON_RUNTIME_DEPENDENCY"
                elif dependencyScope == "0":
                    dependencyScope = "RUNTIME_DEPENDENCY"
                else:
                    dependencyScope = "NOT_AVAILABLE"
                
                # Update the inventory item with the processed value
                inventoryItem["dependencyScope"] = dependencyScope
                
                if dependencyScope == "NON_RUNTIME_DEPENDENCY":
                    # This is a non runtime dependency so should it be included or not?
                    if not includeNonRuntimeInventory:
                        continue
            else:
                # If dependencyScope key doesn't exist, set it to NOT_AVAILABLE
                inventoryItem["dependencyScope"] = "NOT_AVAILABLE"


            externalRefs = []  # For now just holds the purl but in the future could hold more items

            inventoryID = inventoryItem["inventoryID"]

            # See if there is a custom filed at the inventory level for the "Package Supplier"

            packageSupplier = report_data_db.get_custom_field_value(inventoryID, "Package Supplier")
            if packageSupplier is None:
                packageSupplier = "N/A"
            

            if inventoryType != "Component":
                name =  inventoryItem["inventoryItemName"].split("(")[0] # Get rid of ( SPDX ID ) from name
                SPDXIDPackageName = name + "-" + str(inventoryID)  # Inventory ensure the value is unique
                SPDXIDPackageName = re.sub(SPDXIDPackageNamePattern, "-", SPDXIDPackageName)          # Remove special characters
                componentName = name

                if supplier is None:
                    supplier = "Organization: Various, People: Various" 

            else:
                componentName = inventoryItem["componentName"].strip()
                versionName = str(inventoryItem["componentVersionName"]).strip()
                SPDXIDPackageName = componentName + "-" + versionName + "-" + str(inventoryID)  # Inventory ensure the value is unique
                SPDXIDPackageName = re.sub(SPDXIDPackageNamePattern, "-", SPDXIDPackageName)          # Remove special characters

                forge = inventoryItem["forge"]

                ##########################################
                # Create supplier string from forge and component 
                if supplier is None:
                    supplier = create_supplier_string(forge, componentName)

                # Attempt to generate a purl string for the component
                try:
                    purlString = purl.get_purl_string(
                        inventoryItem,
                        inventoryItem["componentVersionName"],
                        inventoryItem["inventoryItemName"]
                    )
                except:
                    logger.warning("Unable to create purl string for inventory item.")
                    purlString = ""

                if "@" in purlString:
                    perlRef = {}
                    perlRef["referenceCategory"] = "PACKAGE-MANAGER"
                    perlRef["referenceLocator"] = purlString
                    perlRef["referenceType"] = "purl"
                    externalRefs.append(perlRef)    

            # Common for Components and License Only items
            packageSPDXID = "SPDXRef-Pkg-" + SPDXIDPackageName
            
            # Manage the homepage value
            if inventoryType == "Component" and inventoryItem["componentUrl"] not in ["", "N/A", "NA", None]:
                homepage = inventoryItem["componentUrl"]
            else:
                homepage = "NOASSERTION"
    
            ##########################################
            # Manage Declared Licenses - These are the "possible" license based on data collection
            declaredLicenses, hasExtractedLicensingInfos = manage_package_declared_licenses(inventoryItem, hasExtractedLicensingInfos)

            ##########################################
            # Manage Concluded license
            concludedLicense, hasExtractedLicensingInfos = manage_package_concluded_license(inventoryItem, hasExtractedLicensingInfos)
    
            packageDetails = {}
            packageDetails["SPDXID"] = packageSPDXID
            packageDetails["name"] = componentName

            if inventoryType == "Component":
                packageDetails["versionInfo"] = versionName

            if externalRefs:
                packageDetails["externalRefs"] = externalRefs
            packageDetails["homepage"] = homepage
            packageDetails["downloadLocation"] = "NOASSERTION"  # TODO - use a inventory custom field to store this?
            packageDetails["copyrightText"] = (process_copyrights(inventoryItem["copyright"]) if includeCopyrightsData else "NOASSERTION")
            packageDetails["licenseDeclared"] = declaredLicenses
            packageDetails["licenseConcluded"] = concludedLicense
            packageDetails["supplier"] = supplier

            # Manage file details related to this package
            filePaths = report_data_db.get_inventory_item_file_paths(inventoryID, projectID)
            
            # Manange the relationship for this pacakge to the root item
            packageRelationship = {}
            packageRelationship["spdxElementId"] = packageSPDXID
            packageRelationship["relationshipType"] = "PACKAGE_OF"
            packageRelationship["relatedSpdxElement"] = rootSPDXID
            
            if packageRelationship not in relationships:
                relationships.append(packageRelationship)


            # Are there any files assocaited to this inventory item?
            if len(filePaths) == 0 or not includeFileDetails: 
                packageDetails["filesAnalyzed"] = False
            else:
                packageDetails["filesAnalyzed"] = True

                #packageFiles[packageSPDXID] = [] # Create array to hold all required file data for tag/value report

                licenseInfoFromFiles = []
                fileHashes = []
                for filePath in filePaths:
                    if filePath["PATH_"] in filePathtoID["inInventory"]:
                        uniqueFileID = filePathtoID["inInventory"][filePath["PATH_"]]["uniqueFileID"]
                        fileHashes.append(filePathtoID["inInventory"][filePath["PATH_"]]["fileSHA1"])
                    elif filePath["PATH_"] in filePathtoID["notInInventory"]:
                        uniqueFileID = filePathtoID["notInInventory"][filePath["PATH_"]]["uniqueFileID"]
                        logger.critical("File path associated to inventory but not according to file details response!!")
                        logger.critical("    File ID: %s   File Path: %s" %(uniqueFileID, filePath["PATH_"]))

                        fileHashes.append(filePathtoID["notInInventory"][filePath["PATH_"]]["fileSHA1"])
                    else:
                        logger.critical("File path does not seem to be in or out of inventory!!")
                        logger.critical("    File Path: %s" %(filePath["PATH_"]))
                        continue
                    
                    fileDetail = projectFileDetails[uniqueFileID]
                    fileSPDXID = fileDetail["SPDXID"]

                    #packageFiles[packageSPDXID].append(fileDetail) # add for tag/value output
                    # See if the file has alrady been added for another package or not for json output
                    if fileDetail not in files:   
                        files.append(fileDetail)  # add for json output

                    # Define the relationship of the file to the package
                    fileRelationship = {}
                    fileRelationship["spdxElementId"] = packageSPDXID
                    fileRelationship["relationshipType"] = "CONTAINS"
                    fileRelationship["relatedSpdxElement"] = fileSPDXID
                    relationships.append(fileRelationship)

                    # Surfaces the file level evidence to the assocaited package
                    licenseInfoFromFiles = licenseInfoFromFiles + fileDetail["licenseInfoInFiles"]
    
                # Create a hash of the file hashes for PackageVerificationCode 
                # Filter out None values from fileHashes before processing
                fileHashes = [hash_val for hash_val in fileHashes if hash_val is not None]
                try:
                    stringHash = ''.join(sorted(fileHashes))
                except:
                    logger.error("Failure sorting file hashes for %s" %SPDXIDPackageName)
                    stringHash = ''.join(fileHashes)
                
                packageVerificationCodeValue = (hashlib.sha1(stringHash.encode('utf-8'))).hexdigest()

                # Was there any file level information
                if len(licenseInfoFromFiles) == 0 :
                    licenseInfoFromFiles = ["NOASSERTION"]
                else:
                    licenseInfoFromFiles = sorted(list(dict.fromkeys(licenseInfoFromFiles)))
                
                packageDetails["licenseInfoFromFiles"] = licenseInfoFromFiles
                packageDetails["packageVerificationCode"] = {}
                packageDetails["packageVerificationCode"]["packageVerificationCodeValue"] = packageVerificationCodeValue
            
            if packageDetails not in packages:
                packages.append(packageDetails)
            
            # Collect copyrights for project
            if includeCopyrightsData:
                # Handle None values in copyright data
                copyright_data = inventoryItem["copyright"]
                if copyright_data is not None:
                    # Ensure we have a list to work with
                    if not isinstance(copyright_data, list):
                        copyright_data = [copyright_data] if copyright_data else []
                    projectCopyrights = list(set(projectCopyrights) | set(copyright_data))

    
        # See if there are any files that are not contained in inventory
        if includeFileDetails:
            # Manage the items from this project that were not associated to inventory
            for filePath in filePathtoID["notInInventory"]:
                uniqueFileID = filePathtoID["notInInventory"][filePath]["uniqueFileID"]

                # Make sure it's only being added once in case a child project has many parents
                if projectFileDetails[uniqueFileID] not in filesNotInInventory:
                    filesNotInInventory.append(projectFileDetails[uniqueFileID])


    ##############################
    if includeFileDetails and includeUnassociatedFiles and len(filesNotInInventory) > 0:
        unassociatedFilesPackage, unassociatedFilesRelationships = manage_unassociated_files(filesNotInInventory, filePathsNotInInventoryToID, rootSPDXID, createOtherFilesPackage, projectCopyrights, includeCopyrightsData)

        if unassociatedFilesPackage["SPDXID"] == rootSPDXID:
            # Since this is the top level pacakge we need to update a few things for the package
            packages[0].pop("filesAnalyzed")
            packages[0]["licenseInfoFromFiles"] = unassociatedFilesPackage["licenseInfoFromFiles"]
            packages[0]["packageVerificationCode"] = unassociatedFilesPackage["packageVerificationCode"]
        else:
            packages.append(unassociatedFilesPackage)

        relationships= relationships + unassociatedFilesRelationships
        files = files + filesNotInInventory
        #packageFiles[unassociatedFilesPackage["SPDXID"]] = filesNotInInventory # add for tag/value output

    # Grabbing Copyrights in Package is Copyright in associated files and unassociated files in inventory
    if includeCopyrightsData:
        for item in packages:
            if item["copyrightText"] == "NOASSERTION":
                item["copyrightText"] = process_copyrights(projectCopyrights)

    # Clean up the hasExtractedLicensingInfos comment field to remove the array and make a string
    for extractedLicense in hasExtractedLicensingInfos:
        comment =  hasExtractedLicensingInfos[extractedLicense]["comment"]
        hasExtractedLicensingInfos[extractedLicense]["comment"] = " | ".join(comment)

    # Build up the top level dictionary with the required elements
    reportDetails["SPDXID"] =  documentSPDXID
    reportDetails["spdxVersion"] =  SPDXVersion
    reportDetails["creationInfo"] = {}
    reportDetails["creationInfo"]["created"] = reportData["spdxTimeStamp"]
    reportDetails["creationInfo"]["creators"] = [creator]

    reportDetails["name"] =  documentName
    reportDetails["dataLicense"] = dataLicense
    reportDetails["documentNamespace"] = documentNamespace

    reportDetails["hasExtractedLicensingInfos"] = list(hasExtractedLicensingInfos.values())  # remove the keys since not needed
    reportDetails["packages"] = packages
    
    if includeFileDetails:
        reportDetails["files"] = files

    reportDetails["relationships"] = relationships

    reportData["topLevelProjectName"] = topLevelProjectName
    reportData["reportDetails"] = reportDetails
    reportData["projectList"] = projectList
    #reportData["packageFiles"] = packageFiles

    return reportData

#----------------------------------------------
def manage_package_declared_licenses(inventoryItem, hasExtractedLicensingInfos):

    declaredLicenses = [] # There could be mulitple licenses so create a list

    try:
        possibleLicenses = report_data_db.get_component_possible_Licenses(inventoryItem["component_id"])
    except:
        possibleLicenses = []
        declaredLicenses.append("NOASSERTION")

    for license in possibleLicenses:

        licenseName = license["licenseName"]
        if license["spdxIdentifier"] is None and license["shortName"] != "":
            possibleLicenseSPDXIdentifier = license["shortName"]
        elif license["spdxIdentifier"] is not None:
            possibleLicenseSPDXIdentifier = license["spdxIdentifier"]
        else:
            possibleLicenseSPDXIdentifier = license["licenseName"]

        if licenseName == "Public Domain":
            logger.info("        Added to NONE declaredLicenses since Public Domain.")
            declaredLicenses.append("NONE")
        
        elif possibleLicenseSPDXIdentifier in SPDX_license_mappings.LICENSEMAPPINGS:
            logger.info("        \"%s\" maps to SPDX ID: \"%s\"" %(possibleLicenseSPDXIdentifier, SPDX_license_mappings.LICENSEMAPPINGS[possibleLicenseSPDXIdentifier]) )
            declaredLicenses.append(SPDX_license_mappings.LICENSEMAPPINGS[possibleLicenseSPDXIdentifier])

        else:
            # There was not a valid SPDX ID 
            logger.warning("        \"%s\" is not a valid SPDX identifier for Declared License. - Using LicenseRef." %(possibleLicenseSPDXIdentifier))

            possibleLicenseSPDXIdentifier = possibleLicenseSPDXIdentifier.split("(", 1)[0].rstrip()  # If there is a ( in string remove everything after and space
            possibleLicenseSPDXIdentifier = re.sub('[^a-zA-Z0-9 \n\.]', '-', possibleLicenseSPDXIdentifier) # Replace spec chars with dash
            possibleLicenseSPDXIdentifier = possibleLicenseSPDXIdentifier.replace(" ", "-") # Replace space with dash
            licenseReference = "LicenseRef-%s" %possibleLicenseSPDXIdentifier
            declaredLicenses.append(licenseReference)
            declaredLicenseComment = "SCA Revenera - Declared license details for this package"

            # Since this is an non SPDX ID we need to add to the hasExtractedLicensingInfos section
            if licenseReference not in hasExtractedLicensingInfos:
                # It's not there so create a new entry
                hasExtractedLicensingInfos[licenseReference] = {}
                hasExtractedLicensingInfos[licenseReference]["licenseId"] = licenseReference
                hasExtractedLicensingInfos[licenseReference]["name"] = possibleLicenseSPDXIdentifier
                hasExtractedLicensingInfos[licenseReference]["extractedText"] = possibleLicenseSPDXIdentifier
                hasExtractedLicensingInfos[licenseReference]["comment"] = [declaredLicenseComment]
            else:
                # It's aready there so but is the comment the same as any previous entry
                if declaredLicenseComment not in hasExtractedLicensingInfos[licenseReference]["comment"]:
                    hasExtractedLicensingInfos[licenseReference]["comment"].append(declaredLicenseComment)

    #  Clean up the declared licenses 
    if len(declaredLicenses) == 0:
        declaredLicenses = "NOASSERTION"
    elif len(declaredLicenses) == 1:
        declaredLicenses = declaredLicenses[0]
    else:
        if "NONE" in declaredLicenses:
            declaredLicenses = "NONE"
        else:
            declaredLicenses = "(" + ' OR '.join(sorted(declaredLicenses)) + ")"

    return declaredLicenses, hasExtractedLicensingInfos


#----------------------------------------------
def manage_package_concluded_license(inventoryItem, hasExtractedLicensingInfos):

    selectedLicenseName = inventoryItem["selectedLicenseName"]
    if inventoryItem["selectedLicenseSPDXIdentifier"] is None and inventoryItem["shortName"] != "":
        selectedLicenseSPDXIdentifier = inventoryItem["shortName"]
    elif inventoryItem["selectedLicenseSPDXIdentifier"] is not None:
        selectedLicenseSPDXIdentifier = inventoryItem["selectedLicenseSPDXIdentifier"]
    else:
        selectedLicenseSPDXIdentifier = inventoryItem["selectedLicenseName"]

    # Need to make sure that there is a valid SPDX license mapping
    if selectedLicenseName == "Public Domain":
        logger.info("        Setting concludedLicense to NONE since Public Domain.")
        concludedLicense = "NONE"

    elif selectedLicenseName == "I don't know":
        concludedLicense = "NOASSERTION"

    elif selectedLicenseName == "N/A":
        concludedLicense = "NOASSERTION"

    elif selectedLicenseSPDXIdentifier in SPDX_license_mappings.LICENSEMAPPINGS:
        logger.info("        \"%s\" maps to SPDX ID: \"%s\"" %(selectedLicenseSPDXIdentifier, SPDX_license_mappings.LICENSEMAPPINGS[selectedLicenseSPDXIdentifier] ))
        concludedLicense = (SPDX_license_mappings.LICENSEMAPPINGS[selectedLicenseSPDXIdentifier])

    else:
        # There was not a valid SPDX license name returned
        logger.warning("        \"%s\" is not a valid SPDX identifier for Concluded License. - Using LicenseRef." %(selectedLicenseSPDXIdentifier))
        if selectedLicenseSPDXIdentifier is not None:
            selectedLicenseSPDXIdentifier = selectedLicenseSPDXIdentifier.split("(", 1)[0].rstrip()  # If there is a ( in string remove everything after and space
            selectedLicenseSPDXIdentifier = re.sub('[^a-zA-Z0-9 \n\.]', '-', selectedLicenseSPDXIdentifier) # Replace spec chars with dash
            selectedLicenseSPDXIdentifier = selectedLicenseSPDXIdentifier.replace(" ", "-") # Replace space with dash
        licenseReference = "LicenseRef-%s" %selectedLicenseSPDXIdentifier
        concludedLicense = licenseReference 

        concludedLicenseComment = "SCA Revenera - Concluded license details for this package"

        # Since this is an non SPDX ID we need to add to the hasExtractedLicensingInfos section
        if licenseReference not in hasExtractedLicensingInfos:
            # It's not there so create a new entry
            hasExtractedLicensingInfos[licenseReference] = {}
            hasExtractedLicensingInfos[licenseReference]["licenseId"] = licenseReference
            hasExtractedLicensingInfos[licenseReference]["name"] = selectedLicenseSPDXIdentifier
            hasExtractedLicensingInfos[licenseReference]["extractedText"] = selectedLicenseSPDXIdentifier
            hasExtractedLicensingInfos[licenseReference]["comment"] = [concludedLicenseComment]
        else:
            # It's aready there so but is the comment the same as any previous entry
            if concludedLicenseComment not in hasExtractedLicensingInfos[licenseReference]["comment"]:
                hasExtractedLicensingInfos[licenseReference]["comment"].append(concludedLicenseComment)

    return concludedLicense, hasExtractedLicensingInfos


#-------------------------------------------------------
def manage_unassociated_files(filesNotInInventory, filePathtoID, rootSPDXID, createOtherFilesPackage, projectCopyrights, includeCopyrightsData):

    packageDetails = {}
    relationships = []
    fileHashes = []
    licenseInfoFromFiles = []
    unassociatedFilesCopyrights =[]

    # Are we creating a new pacakge for the unassocaited files or using the top level pacakage
    if createOtherFilesPackage:
        unassociatedFilesPackageName = "OtherFiles"
        versionName = None
        packageSPDXID = "SPDXRef-Pkg-" + unassociatedFilesPackageName

        # Manange the relationship for this pacakge to the docuemnt
        packageRelationship = {}
        packageRelationship["spdxElementId"] = rootSPDXID
        packageRelationship["relationshipType"] = "CONTAINS"
        packageRelationship["relatedSpdxElement"] = packageSPDXID
        relationships.append(packageRelationship)
    else:
        packageSPDXID = rootSPDXID
        unassociatedFilesPackageName = None

    for fileDetails in filesNotInInventory:
 
        fileSPDXID = fileDetails["SPDXID"]
        fileName = fileDetails["fileName"]
        
        fileHashes.append(filePathtoID[fileName]["fileSHA1"])

        # Surfaces the file level evidence to the assocaited package
        licenseInfoFromFiles = licenseInfoFromFiles + fileDetails["licenseInfoInFiles"]
  
       # Define the relationship of the file to the package
        fileRelationship = {}
        fileRelationship["spdxElementId"] = packageSPDXID
        fileRelationship["relationshipType"] = "CONTAINS"
        fileRelationship["relatedSpdxElement"] = fileSPDXID
        relationships.append(fileRelationship)
        
        # Collecting all unassociated files copyrights
        if includeCopyrightsData and fileDetails["copyrightText"] != "NONE":
            unassociatedFilesCopyrights.extend(fileDetails["copyrightText"] if isinstance(fileDetails["copyrightText"], list) else [fileDetails["copyrightText"]])
            projectCopyrights.extend(fileDetails["copyrightText"] if isinstance(fileDetails["copyrightText"], list) else [fileDetails["copyrightText"]])

    # Create a hash of the file hashes for PackageVerificationCode 
    # Filter out None values from fileHashes before processing
    fileHashes = [hash_val for hash_val in fileHashes if hash_val is not None]
    try:
        stringHash = ''.join(sorted(fileHashes))
    except:
        logger.error("Failure sorting file hashes for %s" %unassociatedFilesPackageName)
        stringHash = ''.join(fileHashes)
    
    packageVerificationCodeValue = (hashlib.sha1(stringHash.encode('utf-8'))).hexdigest()

    # Was there any file level information
    if len(licenseInfoFromFiles) == 0 :
        licenseInfoFromFiles = ["NOASSERTION"]
    else:
        licenseInfoFromFiles = sorted(list(dict.fromkeys(licenseInfoFromFiles)))

    packageDetails["SPDXID"] = packageSPDXID
    packageDetails["name"] = unassociatedFilesPackageName
    packageDetails["homepage"] = "NOASSERTION"
    packageDetails["downloadLocation"] = "NOASSERTION"  # TODO - use a inventory custom field to store this?
    packageDetails["copyrightText"] = (process_copyrights(unassociatedFilesCopyrights) if includeCopyrightsData else "NOASSERTION")
    packageDetails["licenseDeclared"] = "NOASSERTION"
    packageDetails["licenseConcluded"] = "NOASSERTION"
    packageDetails["supplier"] = "Organization: Various, Person: Various"
    packageDetails["licenseInfoFromFiles"] = licenseInfoFromFiles
    packageDetails["packageVerificationCode"] = {}
    packageDetails["packageVerificationCode"]["packageVerificationCodeValue"] = packageVerificationCodeValue

    return packageDetails, relationships

#-------------------------------------------------------
def create_supplier_string(forge, componentName):


    if forge in ["github", "gitlab"]:
        # Is there a way to determine Person vs Organization?
        supplier = "Organization: %s:%s" %(forge, componentName)
    elif forge in ["other"]:
        supplier = "Organization: Undetermined" 
    else:
        if forge != "":
            supplier = "Organization: %s:%s" %(forge, componentName)
        else:
            # Have a default value just in case one can't be created
            supplier = "Organization: Undetermined" 
   
    return supplier

#---------------------------------------------------------
def process_copyrights(copyrights_list):
    logger = logging.getLogger(__name__)
    
    # Handle None or empty values
    if copyrights_list is None:
        logger.info("No Inventory copyright evidence discovered (None)")
        return "NONE"
    
    # Ensure we have a list to work with
    if not isinstance(copyrights_list, list):
        copyrights_list = [copyrights_list] if copyrights_list else []
    
    # Filter out None values and normalize encoding issues and remove non-ASCII characters
    copyrights_list = [unicodedata.normalize('NFKD', str(x)).encode('ASCII', 'ignore').decode('utf-8') 
                      for x in copyrights_list if x is not None]
    
    if copyrights_list:
        logger.info("Inventory Copyright evidence discovered")
        return " | ".join(copyrights_list)
    else:
        logger.info("No Inventory copyright evidence discovered")
        return "NONE"
    