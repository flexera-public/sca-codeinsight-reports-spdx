'''
Copyright 2020 Flexera Software LLC
See LICENSE.TXT for full license text
SPDX-License-Identifier: MIT

Author : sgeary  
Created On : Wed Oct 21 2020
File : report_data.py
'''

import logging
import os
import hashlib
import uuid
import mimetypes
import re
import unicodedata
import CodeInsight_RESTAPIs.project.get_project_inventory
import CodeInsight_RESTAPIs.project.get_scanned_files
import CodeInsight_RESTAPIs.project.get_project_evidence
import CodeInsight_RESTAPIs.project.get_child_projects
import CodeInsight_RESTAPIs.project.get_project_information

import SPDX_license_mappings # To map evidence to an SPDX license name
import filetype_mappings
import purl

logger = logging.getLogger(__name__)

#-------------------------------------------------------------------#
def gather_data_for_report(baseURL, projectID, authToken, reportName, reportVersion, reportOptions):
    logger.info("Entering gather_data_for_report")

    # Parse report options
    includeChildProjects = reportOptions["includeChildProjects"]  # True/False
    includeUnassociatedFiles = reportOptions["includeUnassociatedFiles"]  # True/False

    projectList = [] # List to hold parent/child details for report
    projectData = {} # Create a dictionary containing the project level summary data using projectID as keys

    # Get the list of parent/child projects start at the base project
    projectHierarchy = CodeInsight_RESTAPIs.project.get_child_projects.get_child_projects_recursively(baseURL, projectID, authToken)
    projectName = projectHierarchy["name"]

    SPDXVersion = "SPDX-2.2"
    DataLicense = "CC0-1.0"
    DocumentNamespaceBase = "http:/spdx.org/spdxdocs"  # This shold be modified for each Code Insight instance
    Creator = "Revenera Code Insight 2022"  # TODO - Get value from API

    # Create a list of project data sorted by the project name at each level for report display  
    # Add details for the parent node
    nodeDetails = {}
    nodeDetails["parent"] = "#"  # The root node
    nodeDetails["projectName"] = projectName
    nodeDetails["projectID"] = projectID
    nodeDetails["projectLink"] = baseURL + "/codeinsight/FNCI#myprojectdetails/?id=" + str(projectHierarchy["id"]) + "&tab=projectInventory"

    projectList.append(nodeDetails)
    
    applicationDetails = determine_application_details(baseURL, projectName, projectID, authToken)
    applicationDocumentString = applicationDetails["applicationDocumentString"]


    if includeChildProjects == "true":
        projectList = create_project_hierarchy(projectHierarchy, projectID, projectList, baseURL)
    else:
        logger.debug("Child hierarchy disabled")

    #  Gather the details for each project and summerize the data
    for project in projectList:

        projectID = project["projectID"]
        projectName = project["projectName"]

        projectInventory = CodeInsight_RESTAPIs.project.get_project_inventory.get_project_inventory_details_without_vulnerabilities(baseURL, projectID, authToken)
        inventoryItems = projectInventory["inventoryItems"]

        # Create empty dictionary for project level data for this project
        projectData[projectID] = {}
        projectData[projectID]["projectName"] = projectName
  
        spdxPackages = {}
        filesNotInComponents = []

        for inventoryItem in inventoryItems:
            
            inventoryType = inventoryItem["type"]
            
            # Seperate out Inventory vs WIP or License Only items
            if inventoryType == "Component":

                componentName = re.sub('[^a-zA-Z0-9 \n\.]', '-', inventoryItem["componentName"]).lstrip('-') # Replace spec chars with dash
                versionName = re.sub('[^a-zA-Z0-9 \n\.]', '-', inventoryItem["componentVersionName"]).lstrip('-')  # Replace spec chars with dash
                inventoryID = inventoryItem["id"]
                packageName = componentName + "-" + versionName + "-" + str(inventoryID)

                PackageComment = {}
                PackageComment["inventoryItemName"] = inventoryItem["name"]
                PackageComment["componentId"] = inventoryItem["componentId"]
                PackageComment["componentVersionId"] = inventoryItem["componentVersionId"]
                PackageComment["selectedLicenseId"] = inventoryItem["selectedLicenseId"]

                logger.info("Processing %s" %(packageName))
                filesInInventory = inventoryItem["filePaths"]

                # Attempt to generate a purl string for the component
                try:
                    purlString = purl.get_purl_string(inventoryItem, baseURL, authToken)
                except:
                    logger.warning("Unable to create purl string for inventory item %s." %packageName)
                    purlString = ""


                # Contains the deatils for the package/inventory item
                spdxPackages[packageName] ={}
                spdxPackages[packageName]["reportName"] = str(projectID) + "-" + packageName + ".spdx"
                spdxPackages[packageName]["packageName"] = componentName
                spdxPackages[packageName]["packageVersion"] = versionName
                spdxPackages[packageName]["SPDXID"] = "SPDXRef-Pkg-" + packageName
                spdxPackages[packageName]["PackageFileName"] = packageName
                spdxPackages[packageName]["DocumentName"] =  projectName + "-" + packageName
                spdxPackages[packageName]["DocumentNamespace"] = DocumentNamespaceBase + "/" + projectName + "-" + packageName + "-" + str(uuid.uuid1())
                
                if inventoryItem["componentUrl"] != "" or inventoryItem["componentUrl"] is not None:
                    spdxPackages[packageName]["PackageHomePage"] = inventoryItem["componentUrl"]
                else:
                    spdxPackages[packageName]["PackageHomePage"] = "NOASSERTION"
                
                spdxPackages[packageName]["PackageDownloadLocation"] = "NOASSERTION"
                spdxPackages[packageName]["PackageComment"] = PackageComment
                spdxPackages[packageName]["containedFiles"] = filesInInventory
                spdxPackages[packageName]["purlString"] = purlString

                ##########################################
                # Manage Declared Licenses
                logger.info("    Manage Declared/Possible Licenses")
                PackageLicenseDeclared = []
                try:
                    possibleLicenses = inventoryItem["possibleLicenses"]
                    for license in possibleLicenses:
                        licenseName = license["licenseSPDXIdentifier"]
                        possibleLicenseSPDXIdentifier = license["licenseSPDXIdentifier"]

                        if licenseName == "Public Domain":
                            logger.info("        Appending NONE to PackageLicenseDeclared for %s" %packageName)
                            PackageLicenseDeclared.append("NONE")   

                        elif possibleLicenseSPDXIdentifier in SPDX_license_mappings.LICENSEMAPPINGS:
                            logger.info("        \"%s\" maps to SPDX ID \"%s\"" %(possibleLicenseSPDXIdentifier, SPDX_license_mappings.LICENSEMAPPINGS[possibleLicenseSPDXIdentifier]) )
                            PackageLicenseDeclared.append(SPDX_license_mappings.LICENSEMAPPINGS[license["licenseSPDXIdentifier"]])
                            
                        else:
                            # There was not a valid SPDX ID 
                            logger.warning("        \"%s\" is not a valid SPDX identifier for Declared License. - Using LicenseRef." %(possibleLicenseSPDXIdentifier))
                            possibleLicenseSPDXIdentifier = possibleLicenseSPDXIdentifier.split("(", 1)[0].rstrip()  # If there is a ( in string remove everything after and space
                            possibleLicenseSPDXIdentifier = re.sub('[^a-zA-Z0-9 \n\.]', '-', possibleLicenseSPDXIdentifier) # Replace spec chars with dash
                            possibleLicenseSPDXIdentifier = possibleLicenseSPDXIdentifier.replace(" ", "-") # Replace space with dash
                            PackageLicenseDeclared.append("LicenseRef-%s" %possibleLicenseSPDXIdentifier)           
                except:
                    PackageLicenseDeclared.append(["NOASSERTION"])    

                if len(PackageLicenseDeclared) == 0:
                    PackageLicenseDeclared = "NOASSERTION"
                elif len(PackageLicenseDeclared) == 1:
                    PackageLicenseDeclared = PackageLicenseDeclared[0]
                else:
                    if "NONE" in PackageLicenseDeclared:
                        PackageLicenseDeclared = "NONE"
                    else:
                        PackageLicenseDeclared = "(" + ' OR '.join(sorted(PackageLicenseDeclared)) + ")"


                spdxPackages[packageName]["PackageLicenseDeclared"] = PackageLicenseDeclared

                ##########################################
                # Manage Concluded license
                logger.info("    Manage Concluded License")

                selectedLicenseSPDXIdentifier = inventoryItem["selectedLicenseSPDXIdentifier"]
                selectedLicenseName = inventoryItem["selectedLicenseName"]

                # Need to make sure that there is a valid SPDX license mapping
                if selectedLicenseName == "Public Domain":
                    logger.info("        Setting PackageLicenseConcluded to NONE for %s" %packageName)
                    PackageLicenseConcluded = "NONE"
                elif selectedLicenseName == "I don't know":
                    PackageLicenseConcluded = "NOASSERTION"
                elif selectedLicenseSPDXIdentifier in SPDX_license_mappings.LICENSEMAPPINGS:
                    logger.info("        \"%s\" maps to SPDX ID: \"%s\"" %(selectedLicenseSPDXIdentifier, SPDX_license_mappings.LICENSEMAPPINGS[selectedLicenseSPDXIdentifier] ))
                    PackageLicenseConcluded = (SPDX_license_mappings.LICENSEMAPPINGS[selectedLicenseSPDXIdentifier])
                else:
                    # There was not a valid SPDX license name returned
                    logger.warning("        \"%s\" is not a valid SPDX identifier for Concluded License. - Using LicenseRef." %(selectedLicenseSPDXIdentifier))
                    selectedLicenseSPDXIdentifier = selectedLicenseSPDXIdentifier.split("(", 1)[0].rstrip()  # If there is a ( in string remove everything after and space
                    selectedLicenseSPDXIdentifier = re.sub('[^a-zA-Z0-9 \n\.]', '-', selectedLicenseSPDXIdentifier) # Replace spec chars with dash
                    selectedLicenseSPDXIdentifier = selectedLicenseSPDXIdentifier.replace(" ", "-") # Replace space with dash
                    PackageLicenseConcluded = "LicenseRef-%s" %selectedLicenseSPDXIdentifier 
                       
                spdxPackages[packageName]["PackageLicenseConcluded"] = PackageLicenseConcluded
                
            else:
                # This is a WIP or License only item so take the files assocated here and include them in
                # in the files without inventory bucket
                for file in inventoryItem["filePaths"]:
                    filesNotInComponents.append(file)

        # Create a package to hold files not associated to an inventory item directly
        if includeUnassociatedFiles:
            nonInventoryPackageName = "OtherFiles"
            spdxPackages[nonInventoryPackageName] ={}
            spdxPackages[nonInventoryPackageName]["reportName"] = str(projectID)  + "-" + nonInventoryPackageName + ".spdx"
            spdxPackages[nonInventoryPackageName]["packageName"] = nonInventoryPackageName
            spdxPackages[nonInventoryPackageName]["packageVersion"] = "N/A"
            spdxPackages[nonInventoryPackageName]["containedFiles"] = []
            spdxPackages[nonInventoryPackageName]["SPDXID"] = "SPDXRef-Pkg-" + nonInventoryPackageName
            spdxPackages[nonInventoryPackageName]["PackageFileName"] = nonInventoryPackageName
            spdxPackages[nonInventoryPackageName]["DocumentName"] =  projectName + "-" + nonInventoryPackageName.replace(" ", "_")
            spdxPackages[nonInventoryPackageName]["DocumentNamespace"] = DocumentNamespaceBase + "/" + projectName + "-" + nonInventoryPackageName.replace(" ", "_") + "-" + str(uuid.uuid1())
            spdxPackages[nonInventoryPackageName]["PackageHomePage"] = "NOASSERTION"
            spdxPackages[nonInventoryPackageName]["PackageDownloadLocation"] = "NOASSERTION"
            spdxPackages[nonInventoryPackageName]["PackageLicenseConcluded"] = "NOASSERTION"
            spdxPackages[nonInventoryPackageName]["PackageLicenseDeclared"] = "NOASSERTION"
    
        ############################################################################
        # Dictionary to contain all of the file specific data
        fileDetails = {}

        # Collect the copyright/license data per file and create dict based on 
        projectEvidenceDetails = CodeInsight_RESTAPIs.project.get_project_evidence.get_project_evidence(baseURL, projectID, authToken)
 

        # Dictionary to contain all of the file specific data
        fileEvidence = {}

        for fileEvidenceDetails in projectEvidenceDetails["data"]:
            remoteFile = bool(fileEvidenceDetails["remote"])
            scannedFileId = fileEvidenceDetails["scannedFileId"]
            filePath = fileEvidenceDetails["filePath"]
            copyrightEvidenceFound= fileEvidenceDetails["copyRightMatches"]
            licenseEvidenceFound = list(set(fileEvidenceDetails["licenseMatches"]))

            # Normalize the copyrights in case there are any encoding issues 
            copyrightEvidenceFound = [unicodedata.normalize('NFKD', x).encode('ASCII', 'ignore').decode('utf-8') for x in copyrightEvidenceFound]
       
            
            # Create a unique identifier based on fileID and scan location
            uniqueFileID = str(scannedFileId) + ("-r" if remoteFile else "-s")
     
            logger.info("        File level evidence for %s - %s" %(uniqueFileID, filePath))

            ##########################################
            # Manage File Level licenses
            if licenseEvidenceFound:
                logger.info("            License evidence discovered")

                # Remove duplicates and sort data
                licenseEvidenceFound = sorted(list(dict.fromkeys(licenseEvidenceFound)))
                # Remove Public Domain license if present
                if  "Public Domain" in licenseEvidenceFound: 
                    licenseEvidenceFound.remove("Public Domain")  

                # The license evidence is not in SPDX form so consolidate and map       
                for index, licenseEvidence in enumerate(licenseEvidenceFound):
                    if licenseEvidence in SPDX_license_mappings.LICENSEMAPPINGS:
                        licenseEvidenceFound[index] = SPDX_license_mappings.LICENSEMAPPINGS[licenseEvidence]
                        logger.info("                \"%s\" maps to SPDX ID: \"%s\"" %(licenseEvidence, SPDX_license_mappings.LICENSEMAPPINGS[licenseEvidence] ))
                    else:
                        # There was not a valid SPDX license name returned
                        logger.warning("                \"%s\" is not a valid SPDX identifier for file level license. - Using LicenseRef." %(licenseEvidence))
                        licenseEvidence = licenseEvidence.split("(", 1)[0].rstrip()  # If there is a ( in string remove everything after and space
                        licenseEvidence = re.sub('[^a-zA-Z0-9 \n\.]', '-', licenseEvidence) # Replace spec chars with dash
                        licenseEvidence = licenseEvidence.replace(" ", "-") # Replace space with dash
                        licenseEvidenceFound[index]  = "LicenseRef-%s" %licenseEvidence 
           
            else:
                logger.info("            No license evidence discovered")

            # Remove duplicates
            licenseEvidenceFound = sorted(list(dict.fromkeys(licenseEvidenceFound)))
            
            # if there is no file license evidence then...
            if not len(licenseEvidenceFound):
                licenseEvidenceFound = ["NOASSERTION"]

            ##########################################
            # Manage File Level Copyrights
            if copyrightEvidenceFound:
                logger.info("            Copyright evidence discovered")
            else:
                logger.info("            No copyright evidence discovered")
                copyrightEvidenceFound = ["NONE"]

            fileEvidence[uniqueFileID] = {}
            fileEvidence[uniqueFileID]["Filename"]= filePath
            fileEvidence[uniqueFileID]["copyrightEvidenceFound"]= copyrightEvidenceFound
            fileEvidence[uniqueFileID]["licenseEvidenceFound"]= licenseEvidenceFound     

        # Collect a list of the scanned files
        scannedFiles = CodeInsight_RESTAPIs.project.get_scanned_files.get_scanned_files_details_with_MD5_and_SHA1(baseURL, projectID, authToken)

        # A dict to allow going from file path to unique ID (could be mulitple?)
        filePathToID = {}
        # Cycle through each scanned file
        
        for scannedFile in scannedFiles:
            scannedFileDetails = {}
            remoteFile = scannedFile["remote"]
            scannedFileId = scannedFile["fileId"]
            FileName = scannedFile["filePath"]  
            inInventory = scannedFile["inInventory"]  

            logger.debug("    Scanned File: %s" %FileName)

            # Create a unique identifier based on fileID and scan location
            if remoteFile == "false":
                uniqueFileID = str(scannedFileId) + "-s"
            else:
                uniqueFileID = str(scannedFileId) + "-r"

            logger.debug("        uniqueFileID: %s" %uniqueFileID)    

            # Add the ID to a list or create the list in the first place
            try:
               filePathToID[FileName].append(uniqueFileID)
            except:
                filePathToID[FileName] = [uniqueFileID]      

            # Check to see if the file was associated to an WIP or License only item
            # If it is set the inInvenetory flag to false
            if FileName in filesNotInComponents:
                inInventory = "false"

            # Is the file already in inventory or do we need to deal wtih it?
            if inInventory == "false" and includeUnassociatedFiles:
                try:
                    spdxPackages[nonInventoryPackageName]["containedFiles"].append(FileName)
                except:
                    spdxPackages[nonInventoryPackageName]["containedFiles"] = [FileName]

            # Determine the file type.  Default to any specific mappings
            filename, file_extension = os.path.splitext(FileName)
            if file_extension in filetype_mappings.fileTypeMappings:
                scannedFileDetails["FileType"] = filetype_mappings.fileTypeMappings[file_extension]

            else:
                # See if there is a MIME type associated to the file
                fileType = mimetypes.MimeTypes().guess_type(FileName)[0]

                if fileType:
                    scannedFileDetails["FileType"] = fileType.split("/")[0].upper()
                else:
                    logger.info("        Unmapped file type extension for file: %s" %FileName)
                    scannedFileDetails["FileType"] = "OTHER"
            
            scannedFileDetails["FileLicenseConcluded"] = "NOASSERTION"
            scannedFileDetails["FileName"] = FileName
            scannedFileDetails["fileId"] = uniqueFileID
            scannedFileDetails["fileMD5"] = scannedFile["fileMD5"]

            # See if there is a SHA1 value and if not create one from the MD5 value
            if "fileSHA1" in scannedFile:
                fileSHA1 = scannedFile["fileSHA1"]
                logger.debug("        fileSHA1: %s" %fileSHA1)  

            if fileSHA1 is None:
                logger.warning("        %s does not have a SHA1 calculation" %FileName)
                fileSHA1 = hashlib.sha1(scannedFile["fileMD5"].encode('utf-8')).hexdigest()
            else:
                fileSHA1 = scannedFile["fileSHA1"]


            scannedFileDetails["fileSHA1"]  = fileSHA1

            scannedFileDetails["SPDXID"] = "SPDXRef-File-" + uniqueFileID

            fileContainsEvidence = scannedFile["containsEvidence"]   

            if fileContainsEvidence:
                try:
                    scannedFileDetails["FileCopyrightText"] = fileEvidence[uniqueFileID]["copyrightEvidenceFound"]
                except:
                    scannedFileDetails["FileCopyrightText"] = ["NOASSERTION"]
                try:
                    scannedFileDetails["LicenseInfoInFile"] = fileEvidence[uniqueFileID]["licenseEvidenceFound"]
                except:
                    scannedFileDetails["LicenseInfoInFile"] = []
                   

            fileDetails[uniqueFileID] = scannedFileDetails
        # Are there any files not asscoaited to an inventory item?
        if includeUnassociatedFiles:
            if not len(spdxPackages[nonInventoryPackageName]["containedFiles"]):
                logger.debug("All files are asscoiated to at least one inventory item")
                spdxPackages.pop(nonInventoryPackageName)

        # Merge the results to map each package (inventory item) with the assocaited files
        for package in spdxPackages:
        
            spdxPackages[package]["files"] = {}  

            for file in spdxPackages[package]["containedFiles"]:

                # Do we have data for this file?
                fileIDList = filePathToID[file]

                # It is be possible to have multiple files with the same path
                for fileID in fileIDList:
                    spdxPackages[package]["files"][file] = fileDetails[fileID]

            fileHashes = []
            fileLicenses = []

            # Are there any files assocaited?
            if len(spdxPackages[package]["files"]) > 0:

                for file in spdxPackages[package]["files"]:
                    # Create a list of SHA1 values to hash
                    fileHashes.append(spdxPackages[package]["files"][file]["fileSHA1"])
    
                    # Collect licesne info from files
                    fileLicenses.extend(spdxPackages[package]["files"][file]["LicenseInfoInFile"])

                # Create a hash of the file hashes for PackageVerificationCode 
                try:
                    stringHash = ''.join(sorted(fileHashes))
                except:
                    logger.error("Failure sorting file hashes for %s" %package)
                    logger.debug(stringHash)
                    stringHash = ''.join(fileHashes)

                spdxPackages[package]["PackageVerificationCode"] = (hashlib.sha1(stringHash.encode('utf-8'))).hexdigest()
                spdxPackages[package]["PackageLicenseInfoFromFiles"] = sorted(set(fileLicenses))
            else:
                logger.info("No files assocaited to package %s" %package)

        projectData[projectID]["spdxPackages"] = spdxPackages
        projectData[projectID]["DocumentName"] = applicationDocumentString.replace(" ", "_") + "-" + str(projectID)
        projectData[projectID]["DocumentNamespace"] = DocumentNamespaceBase + "/" + applicationDocumentString.replace(" ", "_") + "-" + str(projectID) + "-" + str(uuid.uuid1())

    SPDXData = {}
    SPDXData["SPDXVersion"] = SPDXVersion
    SPDXData["DataLicense"] = DataLicense
    SPDXData["Creator"] = Creator
    SPDXData["projectData"] = projectData
    SPDXData["DocumentNamespaceBase"] = DocumentNamespaceBase

    reportData = {}
    reportData["reportName"] = reportName
    reportData["projectName"] =  projectName
    reportData["applicationDocumentString"] =  applicationDocumentString
    reportData["projectID"] = projectHierarchy["id"]
    reportData["projectList"] = projectList
    reportData["reportVersion"] = reportVersion
    reportData["SPDXData"] = SPDXData
    reportData["applicationDetails"]=applicationDetails

    return reportData


#----------------------------------------------#
def create_project_hierarchy(project, parentID, projectList, baseURL):
    logger.debug("Entering create_project_hierarchy")

    # Are there more child projects for this project?
    if len(project["childProject"]):

        # Sort by project name of child projects
        for childProject in sorted(project["childProject"], key = lambda i: i['name'] ) :

            nodeDetails = {}
            nodeDetails["projectID"] = str(childProject["id"])
            nodeDetails["parent"] = parentID
            nodeDetails["projectName"] = childProject["name"]
            nodeDetails["projectLink"] = baseURL + "/codeinsight/FNCI#myprojectdetails/?id=" + str(childProject["id"]) + "&tab=projectInventory"

            projectList.append( nodeDetails )

            create_project_hierarchy(childProject, childProject["id"], projectList, baseURL)

    return projectList



#----------------------------------------------#
def determine_application_details(baseURL, projectName, projectID, authToken):
    logger.debug("Entering determine_application_details.")
    # Create a application name for the report if the custom fields are populated
    # Default values
    applicationName = projectName
    applicationVersion = ""
    applicationPublisher = ""
    applicationDocumentString = ""

    projectInformation = CodeInsight_RESTAPIs.project.get_project_information.get_project_information_summary(baseURL, projectID, authToken)

    # Project level custom fields added in 2022R1
    if "customFields" in projectInformation:
        customFields = projectInformation["customFields"]

        # See if the custom project fields were propulated for this project
        for customField in customFields:

            # Is there the reqired custom field available?
            if customField["fieldLabel"] == "Application Name":
                if customField["value"]:
                    applicationName = customField["value"]

            # Is the custom version field available?
            if customField["fieldLabel"] == "Application Version":
                if customField["value"]:
                    applicationVersion = customField["value"]     

            # Is the custom Publisher field available?
            if customField["fieldLabel"] == "Application Publisher":
                if customField["value"]:
                    applicationPublisher = customField["value"]    



    # Join the custom values to create the application name for the report artifacts
    if applicationName != projectName:
        if applicationVersion != "":
            applicationNameVersion = applicationName + " - " + applicationVersion
        else:
            applicationNameVersion = applicationName
    else:
        applicationNameVersion = projectName

    if applicationPublisher != "":
        applicationDocumentString = applicationPublisher

    # This will either be the project name or the supplied application name
    applicationDocumentString += "_" + applicationName

    if applicationVersion != "":
        applicationDocumentString += "_" + applicationVersion


    applicationDetails = {}
    applicationDetails["applicationName"] = applicationName
    applicationDetails["applicationVersion"] = applicationVersion
    applicationDetails["applicationPublisher"] = applicationPublisher
    applicationDetails["applicationNameVersion"] = applicationNameVersion
    applicationDetails["applicationDocumentString"] = applicationDocumentString

    logger.info("    applicationDetails: %s" %applicationDetails)

    return applicationDetails