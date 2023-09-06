'''
Copyright 2023 Flexera Software LLC
See LICENSE.TXT for full license text
SPDX-License-Identifier: MIT

Author : sgeary  
Created On : Tue Aug 29 2023
File : report_data.py
'''

import logging, uuid, re, hashlib
import common.application_details
import common.project_heirarchy
import common.api.project.get_project_inventory
import SPDX_license_mappings, purl
import report_data_files

logger = logging.getLogger(__name__)

#-------------------------------------------------------------------#
def gather_data_for_report(baseURL, projectID, authToken, reportData):
    logger.info("Entering gather_data_for_report")

    reportDetails={}
    packages = []
    hasExtractedLicensingInfos = {}
    relationships = []
    files = []
    filesNotInInventory = []
    filePathsNotInInventoryToID = {}

    reportOptions = reportData["reportOptions"]
    releaseVersion = reportData["releaseVersion"]

    # Parse report options
    includeChildProjects = reportOptions["includeChildProjects"]  # True/False
    includeFileDetails = reportOptions["includeFileDetails"]  # True/False
    includeUnassociatedFiles = reportOptions["includeUnassociatedFiles"]  # True/False

    applicationDetails = common.application_details.determine_application_details(projectID, baseURL, authToken)
    documentName = applicationDetails["applicationDocumentString"].replace(" ", "_")
    projectList = common.project_heirarchy.create_project_heirarchy(baseURL, authToken, projectID, includeChildProjects)
    topLevelProjectName = projectList[0]["projectName"]

    SPDXVersion = "SPDX-2.2"
    documentSPDXID = "SPDXRef-DOCUMENT"
    documentNamespace  = "http:/spdx.org/spdxdocs/" + documentName + "-" + str(uuid.uuid1())
    creator = "Tool: Revenera SCA - Code Insight %s" %releaseVersion
    dataLicense = "CC0-1.0"   

    #  Gather the details for each project and summerize the data
    for project in projectList:
        projectID = project["projectID"]
        projectName = project["projectName"]

        print("        Collect data for project: %s" %projectName)

        if includeFileDetails:

            # Collect file level details for files associated to this project
            print("            Collect file level details.")
            logger.info("            Collect file level details.")
            filePathtoID, projectFileDetails, hasExtractedLicensingInfos = report_data_files.manage_file_details(baseURL, authToken, projectID, hasExtractedLicensingInfos, includeUnassociatedFiles)

            # Create a full list of filename to ID mappings for non inventory items
            if includeUnassociatedFiles:
                filePathsNotInInventoryToID.update(filePathtoID["notInInventory"])

            # Combine the files associated to this project to the larger list
            files = files + list(projectFileDetails.values())     

            print("            File level details for project has been collected")
            logger.info("            File level details for project has been collected")


        print("            Collect inventory details.")
        logger.info("            Collect inventory details")
        projectInventory = common.api.project.get_project_inventory.get_project_inventory_details_without_vulnerabilities(baseURL, projectID, authToken)
        inventoryItems = projectInventory["inventoryItems"]
        print("            Inventory has been collected.")
        logger.info("            Inventory has been collected.")      

        for inventoryItem in inventoryItems:
            inventoryType = inventoryItem["type"]

            # Seperate out Inventory vs WIP or License Only items
            if inventoryType == "Component":

                externalRefs = []  # For now just holds the purl but in the future could hold more items
                componentName = re.sub('[^a-zA-Z0-9 \n\.]', '-', inventoryItem["componentName"]).lstrip('-') # Replace spec chars with dash
                versionName = re.sub('[^a-zA-Z0-9 \n\.]', '-', inventoryItem["componentVersionName"]).lstrip('-')  # Replace spec chars with dash
                inventoryID = inventoryItem["id"]
                packageName = componentName + "-" + versionName + "-" + str(inventoryID)  # Inventory ensure the value is unique
                packageSPDXID = "SPDXRef-Pkg-" + packageName
                
                # Manage the homepage value
                if inventoryItem["componentUrl"] != "" or inventoryItem["componentUrl"] is not None:
                    homepage = inventoryItem["componentUrl"]
                else:
                    homepage = "NOASSERTION"

                # Manage the purl value - To be replaced in 2023R4
                try:
                    purlString = purl.get_purl_string(inventoryItem, baseURL, authToken)
                except:
                    logger.warning("Unable to create purl string for inventory item %s." %packageName)
                    purlString = ""

                if "@" in purlString:
                    perlRef = {}
                    perlRef["referenceCategory"] = "PACKAGE-MANAGER"
                    perlRef["referenceLocator"] = purlString
                    perlRef["referenceType"] = "purl"
                    externalRefs.append(perlRef)
     
                ##########################################
                # Manage Declared Licenses - These are the "possible" license based on data collection
                declaredLicenses, hasExtractedLicensingInfos = manage_package_declared_licenses(inventoryItem, hasExtractedLicensingInfos)

                ##########################################
                # Manage Concluded license
                concludedLicense, hasExtractedLicensingInfos = manage_package_concluded_license(inventoryItem, hasExtractedLicensingInfos)
               
                packageDetails = {}
                packageDetails["SPDXID"] = packageSPDXID
                packageDetails["name"] = packageName
                packageDetails["versionInfo"] = versionName
                packageDetails["externalRefs"] = externalRefs
                packageDetails["homepage"] = homepage
                packageDetails["downloadLocation"] = "NOASSERTION"  # TODO - use a inventory custom field to store this?
                packageDetails["copyrightText"] = "NOASSERTION"     # TODO - use a inventory custom field to store this?
                packageDetails["licenseDeclared"] = declaredLicenses
                packageDetails["licenseConcluded"] = concludedLicense

                # Manage file details related to this package
                filePaths = inventoryItem["filePaths"]
                
                # Are there any files assocaited to this inventory item?
                if len(filePaths) == 0 or not includeFileDetails: 
                    packageDetails["filesAnalyzed"] = False
                else:

                    licenseInfoFromFiles = []
                    fileHashes = []
                    for filePath in filePaths:
                        if filePath in filePathtoID["inInventory"]:
                            uniqueFileID = filePathtoID["inInventory"][filePath]["uniqueFileID"]
                            fileHashes.append(filePathtoID["inInventory"][filePath]["fileSHA1"])
                        elif filePath in filePathtoID["notInInventory"]:
                            uniqueFileID = filePathtoID["notInInventory"][filePath]["uniqueFileID"]
                            logger.critical("File path asscoited to inventory but not according to file details response!!")
                            logger.critical("    File ID: %s   File Path: %s" %(uniqueFileID, filePath))

                            fileHashes.append(filePathtoID["notInInventory"][filePath]["fileSHA1"])
                        else:
                            logger.error("File path does not seem to be in or out of inventory!!")
                            return {"errorMsg" : "File path does not seem to be in or out of inventory!!"}
                        
                        fileDetail = projectFileDetails[uniqueFileID]
                        fileSPDXID = fileDetail["SPDXID"]

                        # Define the relationship of the file to the package
                        fileRelationship = {}
                        fileRelationship["spdxElementId"] = packageSPDXID
                        fileRelationship["relationshipType"] = "CONTAINS"
                        fileRelationship["relatedSpdxElement"] = fileSPDXID
                        relationships.append(fileRelationship)

                        # Surfaces the file level evidence to the assocaited package
                        licenseInfoFromFiles = licenseInfoFromFiles + fileDetail["licenseInfoInFiles"]

                    # Create a hash of the file hashes for PackageVerificationCode 
                    try:
                        stringHash = ''.join(sorted(fileHashes))
                    except:
                        logger.error("Failure sorting file hashes for %s" %packageName)
                        logger.debug(stringHash)
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
             
                packages.append(packageDetails)

                # Manange the relationship for this pacakge to the docuemnt
                packageRelationship = {}
                packageRelationship["spdxElementId"] = documentSPDXID
                packageRelationship["relationshipType"] = "DESCRIBES"
                packageRelationship["relatedSpdxElement"] = packageSPDXID
                relationships.append(packageRelationship)
        
        # See if there are any files that are not contained in inventory
        if includeFileDetails:
            # Manage the items from this project that were not associated to inventory
            for filePath in filePathtoID["notInInventory"]:
                uniqueFileID = filePathtoID["notInInventory"][filePath]["uniqueFileID"]
                filesNotInInventory.append(projectFileDetails[uniqueFileID])


    ##############################
    if includeUnassociatedFiles:
        unassociatedFilesPackage, unassociatedFilesRelationships = manage_unassociated_files(filesNotInInventory, filePathsNotInInventoryToID, documentSPDXID)
        packages.append(unassociatedFilesPackage)
        relationships= relationships + unassociatedFilesRelationships


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

    return reportData

#----------------------------------------------
def manage_package_declared_licenses(inventoryItem, hasExtractedLicensingInfos):

    declaredLicenses = [] # There could be mulitple licenses so create a list

    try:
        possibleLicenses = inventoryItem["possibleLicenses"]
    except:
        possibleLicenses = []
        declaredLicenses.append("NO ASSERTION")

    for license in possibleLicenses:
        licenseName = license["licenseSPDXIdentifier"]
        possibleLicenseSPDXIdentifier = license["licenseSPDXIdentifier"]

        if licenseName == "Public Domain":
            logger.info("        Added to NONE declaredLicenses since Public Domain.")
            declaredLicenses.append("NONE")
        
        elif possibleLicenseSPDXIdentifier in SPDX_license_mappings.LICENSEMAPPINGS:
            logger.info("        \"%s\" maps to SPDX ID: \"%s\"" %(possibleLicenseSPDXIdentifier, SPDX_license_mappings.LICENSEMAPPINGS[possibleLicenseSPDXIdentifier]) )
            declaredLicenses.append(SPDX_license_mappings.LICENSEMAPPINGS[license["licenseSPDXIdentifier"]])

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

    selectedLicenseSPDXIdentifier = inventoryItem["selectedLicenseSPDXIdentifier"]
    selectedLicenseName = inventoryItem["selectedLicenseName"]

    # Need to make sure that there is a valid SPDX license mapping
    if selectedLicenseName == "Public Domain":
        logger.info("        Setting concludedLicense to NONE since Public Domain.")
        concludedLicense = "NONE"

    elif selectedLicenseName == "I don't know":
        concludedLicense = "NOASSERTION"

    elif selectedLicenseSPDXIdentifier in SPDX_license_mappings.LICENSEMAPPINGS:
        logger.info("        \"%s\" maps to SPDX ID: \"%s\"" %(selectedLicenseSPDXIdentifier, SPDX_license_mappings.LICENSEMAPPINGS[selectedLicenseSPDXIdentifier] ))
        concludedLicense = (SPDX_license_mappings.LICENSEMAPPINGS[selectedLicenseSPDXIdentifier])

    else:
        # There was not a valid SPDX license name returned
        logger.warning("        \"%s\" is not a valid SPDX identifier for Concluded License. - Using LicenseRef." %(selectedLicenseSPDXIdentifier))

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
def manage_unassociated_files(filesNotInInventory, filePathtoID, documentSPDXID):

    packageDetails = {}
    relationships = []
    fileHashes = []
    licenseInfoFromFiles = []

    unassociatedFilesPackageName = "OtherFiles"
    packageSPDXID = "SPDXRef-Pkg-" + unassociatedFilesPackageName

    # Manange the relationship for this pacakge to the docuemnt
    packageRelationship = {}
    packageRelationship["spdxElementId"] = documentSPDXID
    packageRelationship["relationshipType"] = "DESCRIBES"
    packageRelationship["relatedSpdxElement"] = packageSPDXID
    relationships.append(packageRelationship)

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

    # Create a hash of the file hashes for PackageVerificationCode 
    try:
        stringHash = ''.join(sorted(fileHashes))
    except:
        logger.error("Failure sorting file hashes for %s" %unassociatedFilesPackageName)
        logger.debug(stringHash)
        stringHash = ''.join(fileHashes)
    
    packageVerificationCodeValue = (hashlib.sha1(stringHash.encode('utf-8'))).hexdigest()

    # Was there any file level information
    if len(licenseInfoFromFiles) == 0 :
        licenseInfoFromFiles = ["NOASSERTION"]
    else:
        licenseInfoFromFiles = sorted(list(dict.fromkeys(licenseInfoFromFiles)))

    packageDetails["SPDXID"] = packageSPDXID
    packageDetails["name"] = unassociatedFilesPackageName
    packageDetails["versionInfo"] = "N/A"
    packageDetails["homepage"] = "NOASSERTION"
    packageDetails["downloadLocation"] = "NOASSERTION"  # TODO - use a inventory custom field to store this?
    packageDetails["copyrightText"] = "NOASSERTION"     # TODO - use a inventory custom field to store this?
    packageDetails["licenseDeclared"] = "NOASSERTION"
    packageDetails["licenseConcluded"] = "NOASSERTION"
    packageDetails["licenseInfoFromFiles"] = licenseInfoFromFiles
    packageDetails["packageVerificationCode"] = {}
    packageDetails["packageVerificationCode"]["packageVerificationCodeValue"] = packageVerificationCodeValue

    return packageDetails, relationships