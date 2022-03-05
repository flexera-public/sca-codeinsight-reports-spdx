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
import CodeInsight_RESTAPIs.project.get_project_inventory
import CodeInsight_RESTAPIs.project.get_scanned_files
import CodeInsight_RESTAPIs.project.get_project_evidence
import CodeInsight_RESTAPIs.project.get_child_projects

import SPDX_license_mappings # To map evidence to an SPDX license name
import filetype_mappings

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
    Creator = "Code Insight"

    # Create a list of project data sorted by the project name at each level for report display  
    # Add details for the parent node
    nodeDetails = {}
    nodeDetails["parent"] = "#"  # The root node
    nodeDetails["projectName"] = projectName
    nodeDetails["projectID"] = projectID
    nodeDetails["projectLink"] = baseURL + "/codeinsight/FNCI#myprojectdetails/?id=" + str(projectHierarchy["id"]) + "&tab=projectInventory"

    projectList.append(nodeDetails)

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

                componentName = inventoryItem["componentName"].replace(" ", "_")
                versionName = inventoryItem["componentVersionName"].replace(" ", "_").replace('/', '')
                inventoryID = inventoryItem["id"]
                packageName = componentName + "-" + versionName + "-" + str(inventoryID)

                PackageComment = {}
                PackageComment["inventoryItemName"] = inventoryItem["name"]
                PackageComment["componentId"] = inventoryItem["componentId"]
                PackageComment["componentVersionId"] = inventoryItem["componentVersionId"]
                PackageComment["selectedLicenseId"] = inventoryItem["selectedLicenseId"]

                logger.info("Processing %s" %(packageName))
                filesInInventory = inventoryItem["filePaths"]

                # Contains the deatils for the package/inventory item
                spdxPackages[packageName] ={}
                spdxPackages[packageName]["reportName"] = str(projectID) + "-" + packageName.replace(" ", "_") + ".spdx"
                spdxPackages[packageName]["packageName"] = componentName
                spdxPackages[packageName]["packageVersion"] = versionName
                spdxPackages[packageName]["SPDXID"] = "SPDXRef-Pkg-" + packageName
                spdxPackages[packageName]["PackageFileName"] = packageName
                spdxPackages[packageName]["DocumentName"] =  projectName + "-" + packageName.replace(" ", "_")
                spdxPackages[packageName]["DocumentNamespace"] = DocumentNamespaceBase + "/" + projectName + "-" + packageName.replace(" ", "_") + "-" + str(uuid.uuid1())
                spdxPackages[packageName]["PackageDownloadLocation"] = inventoryItem["componentUrl"]
                spdxPackages[packageName]["PackageComment"] = PackageComment
                spdxPackages[packageName]["containedFiles"] = filesInInventory

                ##########################################
                # Manage Concluded licenes
                logger.info("    Manage Concluded/Possible Licenses")
                PackageLicenseConcluded = []
                try:
                    possibleLicenses = inventoryItem["possibleLicenses"]
                    for license in possibleLicenses:
                        possibleLicenseSPDXIdentifier = license["licenseSPDXIdentifier"]
                        if possibleLicenseSPDXIdentifier in SPDX_license_mappings.LICENSEMAPPINGS:
                            logger.info("        \"%s\" maps to SPDX ID \"%s\"" %(possibleLicenseSPDXIdentifier, SPDX_license_mappings.LICENSEMAPPINGS[possibleLicenseSPDXIdentifier]) )
                            PackageLicenseConcluded.append(SPDX_license_mappings.LICENSEMAPPINGS[license["licenseSPDXIdentifier"]])
                            
                        else:
                            # There was not a valid SPDX ID 
                            logger.warning("        \"%s\" is not a valid SPDX identifier. - Using NOASSERTION." %(possibleLicenseSPDXIdentifier))
                            PackageLicenseConcluded.append("NOASSERTION")           
                except:
                    PackageLicenseConcluded.append(["NOASSERTION"])    

                if len(PackageLicenseConcluded) == 0:
                    PackageLicenseConcluded = "NOASSERTION"
                elif len(PackageLicenseConcluded) == 1:
                    PackageLicenseConcluded = PackageLicenseConcluded[0]
                else:
                    PackageLicenseConcluded = "(" + ' OR '.join(sorted(PackageLicenseConcluded)) + ")"


                spdxPackages[packageName]["PackageLicenseConcluded"] = PackageLicenseConcluded

                ##########################################
                # Manage Declared license
                logger.info("    Manage Declared License")
                selectedLicenseSPDXIdentifier = inventoryItem["selectedLicenseSPDXIdentifier"]

                # Need to make sure that there is a valid SPDX license mapping
                if selectedLicenseSPDXIdentifier in SPDX_license_mappings.LICENSEMAPPINGS:
                    logger.info("        \"%s\" maps to SPDX ID: \"%s\"" %(selectedLicenseSPDXIdentifier, SPDX_license_mappings.LICENSEMAPPINGS[selectedLicenseSPDXIdentifier] ))
                    PackageLicenseDeclared = (SPDX_license_mappings.LICENSEMAPPINGS[selectedLicenseSPDXIdentifier])
                else:
                    # There was not a valid SPDX license name returned
                    logger.warning("        \"%s\" is not a valid SPDX identifier. - Using NOASSERTION." %(selectedLicenseSPDXIdentifier))
                    PackageLicenseDeclared = "NOASSERTION"
                       
                spdxPackages[packageName]["PackageLicenseDeclared"] = PackageLicenseDeclared
                
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
            
            # Create a unique identifier based on fileID and scan location
            uniqueFileID = str(scannedFileId) + ("-r" if remoteFile else "-s")
     
            logger.info("        File level evidence for %s - %s" %(uniqueFileID, filePath))

            ##########################################
            # Manage File Level licenses
            if licenseEvidenceFound:
                logger.info("            License evidience discovered")
                # The license evidience is not in SPDX form so consolidate and map       
                for index, licenseEvidence in enumerate(licenseEvidenceFound):
                    if licenseEvidence in SPDX_license_mappings.LICENSEMAPPINGS:
                        licenseEvidenceFound[index] = SPDX_license_mappings.LICENSEMAPPINGS[licenseEvidence]
                        logger.info("                \"%s\" maps to SPDX ID: \"%s\"" %(licenseEvidence, SPDX_license_mappings.LICENSEMAPPINGS[licenseEvidence] ))
                    else:
                        logger.warning("                File contains '%s' which is not a valid SPDX ID. - Using NOASSERTION." %(licenseEvidence))

                        licenseEvidenceFound[index]  = "NOASSERTION"
            
                licenseEvidenceFound = licenseEvidenceFound  
            else:
                logger.info("            No license evidience discovered")
                licenseEvidenceFound = ["NONE"]

            ##########################################
            # Manage File Level Copyrights
            if copyrightEvidenceFound:
                logger.info("            Copyright evidience discovered")
            else:
                logger.info("            No copyright evidience discovered")
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

        invalidSHA1 = False # Default value
        for scannedFile in scannedFiles:
            scannedFileDetails = {}
            remoteFile = scannedFile["remote"]
            scannedFileId = scannedFile["fileId"]
            FileName = scannedFile["filePath"]  
            inInventory = scannedFile["inInventory"]  

            # Create a unique identifier based on fileID and scan location
            if remoteFile == "false":
                uniqueFileID = str(scannedFileId) + "-s"
            else:
                uniqueFileID = str(scannedFileId) + "-r"

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

            # See if there is a SHA1 key (2021R3 or later) and if so is it populated (Enabeld in DB)
            if "fileSHA1" in scannedFileDetails:
                if scannedFile["fileSHA1"]:
                    scannedFileDetails["fileSHA1"] = scannedFile["fileSHA1"]
                else:
                    logger.warning("        %s does not have a SHA1 calculation" %FileName)
                    scannedFileDetails["fileSHA1"] = hashlib.sha1(scannedFile["fileMD5"].encode('utf-8')).hexdigest()
                    invalidSHA1 = True # There was no SHA1 for at least one file
            else:
                logger.warning("        %s does not have a SHA1 key in the response" %FileName)
                scannedFileDetails["fileSHA1"] = hashlib.sha1(scannedFile["fileMD5"].encode('utf-8')).hexdigest()
                invalidSHA1 = True # There was no SHA1 for at least one file
            
            scannedFileDetails["SPDXID"] = "SPDXRef-File-" + uniqueFileID

            fileContainsEvidence = scannedFile["containsEvidence"]   

            if fileContainsEvidence:
                scannedFileDetails["LicenseInfoInFile"] = []

                if fileEvidence[uniqueFileID]["copyrightEvidenceFound"]:
                    scannedFileDetails["FileCopyrightText"] = fileEvidence[uniqueFileID]["copyrightEvidenceFound"]
                else:
                    scannedFileDetails["FileCopyrightText"] = ["NOASSERTION"]

                if fileEvidence[uniqueFileID]["licenseEvidenceFound"]:
                    scannedFileDetails["LicenseInfoInFile"] = fileEvidence[uniqueFileID]["licenseEvidenceFound"]

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

            for file in spdxPackages[package]["files"]:
                # Create a list of SHA1 values to hash
                fileHashes.append(spdxPackages[package]["files"][file]["fileSHA1"])
                # Collect licesne info from files
                fileLicenses.extend(spdxPackages[package]["files"][file]["LicenseInfoInFile"])

            # Create a hash of the file hashes for PackageVerificationCode 
            stringHash = ''.join(sorted(fileHashes))
            spdxPackages[package]["PackageVerificationCode"] = (hashlib.sha1(stringHash.encode('utf-8'))).hexdigest()
            spdxPackages[package]["PackageLicenseInfoFromFiles"] = set(fileLicenses)

        projectData[projectID]["spdxPackages"] = spdxPackages
        projectData[projectID]["DocumentName"] = projectName.replace(" ", "_") + "-" + str(projectID)
        projectData[projectID]["DocumentNamespace"] = DocumentNamespaceBase + "/" + projectName.replace(" ", "_") + "-" + str(projectID) + "-" + str(uuid.uuid1())

        # Was there any files that did not contains SHA1 details?
        projectData[projectID]["invalidSHA1"] = invalidSHA1

    SPDXData = {}
    SPDXData["SPDXVersion"] = SPDXVersion
    SPDXData["DataLicense"] = DataLicense
    SPDXData["Creator"] = Creator
    SPDXData["projectData"] = projectData
    SPDXData["DocumentNamespaceBase"] = DocumentNamespaceBase

    reportData = {}
    reportData["reportName"] = reportName
    reportData["projectName"] =  projectHierarchy["name"]
    reportData["projectID"] = projectHierarchy["id"]
    reportData["projectList"] = projectList
    reportData["reportVersion"] = reportVersion
    reportData["SPDXData"] = SPDXData

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


