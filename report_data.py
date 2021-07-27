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
def gather_data_for_report(baseURL, projectID, authToken, reportName, reportVersion):
    logger.info("Entering gather_data_for_report")

    # Replace with report option
    includeChildProjects  = "true"

    SPDXVersion = "SPDX-2.2"
    DataLicense = "CC0-1.0"
    DocumentNamespaceBase = "http:/spdx.org/spdxdocs"  # This shold be modified for each Code Insight instance
    Creator = "Code Insight"

    projectList = [] # List to hold parent/child details for report
    projectData = {} # Create a dictionary containing the project level summary data using projectID as keys

    # Get the list of parent/child projects start at the base project
    projectHierarchy = CodeInsight_RESTAPIs.project.get_child_projects.get_child_projects_recursively(baseURL, projectID, authToken)

    # Create a list of project data sorted by the project name at each level for report display  
    # Add details for the parent node
    nodeDetails = {}
    nodeDetails["parent"] = "#"  # The root node
    nodeDetails["projectName"] = projectHierarchy["name"]
    nodeDetails["projectID"] = projectHierarchy["id"]
    nodeDetails["projectLink"] = baseURL + "/codeinsight/FNCI#myprojectdetails/?id=" + str(projectHierarchy["id"]) + "&tab=projectInventory"

    projectList.append(nodeDetails)

    if includeChildProjects == "true":
        projectList = create_project_hierarchy(projectHierarchy, projectHierarchy["id"], projectList, baseURL)
    else:
        logger.debug("Child hierarchy disabled")


    #  Gather the details for each project and summerize the data
    for project in projectList:

        projectID = project["projectID"]
        projectName = project["projectName"].replace(" - ", "-").replace(" ", "_")

        projectInventory = CodeInsight_RESTAPIs.project.get_project_inventory.get_project_inventory_details_without_vulnerabilities(baseURL, projectID, authToken)
        inventoryItems = projectInventory["inventoryItems"]

        # Create empty dictionary for project level data for this project
        projectData[projectName] = {}
  
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

                logger.info("Processing %s" %(packageName))
                filesInInventory = inventoryItem["filePaths"]

                PackageLicenseDeclared = []
                try:
                    possibleLicenses = inventoryItem["possibleLicenses"]
                    for license in possibleLicenses:
                        
                        if license["licenseSPDXIdentifier"] in SPDX_license_mappings.LICENSEMAPPINGS:
                            PackageLicenseDeclared.append(SPDX_license_mappings.LICENSEMAPPINGS[license["licenseSPDXIdentifier"]])
                        else:
                            PackageLicenseDeclared.append(license["licenseSPDXIdentifier"]) 
                        
                except:

                    PackageLicenseDeclared.append(["NOASSERTION"])     
                
                selectedLicenseSPDXIdentifier = inventoryItem["selectedLicenseSPDXIdentifier"]
                
                # Contains the deatils for the package/inventory item
                spdxPackages[packageName] ={}
                spdxPackages[packageName]["reportName"] = str(projectID) + "-" + packageName.replace(" ", "_") + ".spdx"
                spdxPackages[packageName]["packageName"] = packageName
                spdxPackages[packageName]["SPDXID"] = "SPDXRef-Pkg-" + packageName
                spdxPackages[packageName]["PackageFileName"] = packageName
                spdxPackages[packageName]["DocumentName"] =  projectName + "-" + packageName.replace(" ", "_")
                spdxPackages[packageName]["DocumentNamespace"] = DocumentNamespaceBase + "/" + projectName + "-" + packageName.replace(" ", "_") + "-" + str(uuid.uuid1())
                spdxPackages[packageName]["PackageDownloadLocation"] = inventoryItem["componentUrl"]
                
                if len(PackageLicenseDeclared) == 0:
                    spdxPackages[packageName]["PackageLicenseConcluded"] = "NOASSERTION"
                elif len(PackageLicenseDeclared) == 1:
                    spdxPackages[packageName]["PackageLicenseConcluded"] = PackageLicenseDeclared[0]
                else:
                    spdxPackages[packageName]["PackageLicenseConcluded"] = "(" + ' OR '.join(sorted(PackageLicenseDeclared)) + ")"
            

                spdxPackages[packageName]["PackageLicenseDeclared"] = selectedLicenseSPDXIdentifier
                spdxPackages[packageName]["containedFiles"] = filesInInventory

                

            else:
                # This is a WIP or License only item so take the files assocated here and include them in
                # in the files without inventory bucket
                for file in inventoryItem["filePaths"]:
                    filesNotInComponents.append(file)

        # Create a package to hold files not associated to an inventory item directly
        nonInventoryPackageName = "OtherFiles"
        spdxPackages[nonInventoryPackageName] ={}
        spdxPackages[nonInventoryPackageName]["reportName"] = str(projectID)  + "-" + nonInventoryPackageName + ".spdx"
        spdxPackages[nonInventoryPackageName]["packageName"] = nonInventoryPackageName
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
     
            # The license evidience is not in SPDX form so consolidate and map       
            for index, licenseEvidence in enumerate(licenseEvidenceFound):
                if licenseEvidence in SPDX_license_mappings.LICENSEMAPPINGS:
                    licenseEvidenceFound[index] = SPDX_license_mappings.LICENSEMAPPINGS[licenseEvidence]
                else:
                    logger.info("Unmapped License to SPDX ID in file evidence: %s" %licenseEvidence)

                
            # If there is no evidience add NONE
            if len(licenseEvidenceFound) == 0:
                licenseEvidenceFound = ["NONE"]
            else:
                licenseEvidenceFound = licenseEvidenceFound  

            if len(copyrightEvidenceFound) == 0:
                copyrightEvidenceFound = ["NONE"]
            else:
                copyrightEvidenceFound = copyrightEvidenceFound  

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
            if inInventory == "false":
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
                    logger.info("Unmapped file type extension for file: %s" %FileName)
                    scannedFileDetails["FileType"] = "OTHER"
            
            scannedFileDetails["LicenseConcluded"] = "NOASSERTION"
            scannedFileDetails["FileName"] = FileName
            scannedFileDetails["fileId"] = uniqueFileID
            scannedFileDetails["fileMD5"] = scannedFile["fileMD5"]
            scannedFileDetails["fileSHA1"] = scannedFile["fileSHA1"]

            # SPDX requires a SHA1 value so if the SHA1 option is not enabled 
            # in the database exit out and create an error report with details.
            if not scannedFileDetails["fileSHA1"]:
                logger.debug("No SHA1 value for %s" %uniqueFileID)
                reportData = {}
                reportData["errorMsg"] = ["SHA1 Error:  An encountered file did not have a corresponding SHA1 value."]
                return reportData
            
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

        projectData[projectName]["spdxPackages"] = spdxPackages

    SPDXData = {}
    SPDXData["SPDXVersion"] = SPDXVersion
    SPDXData["DataLicense"] = DataLicense
    SPDXData["Creator"] = Creator
    SPDXData["projectData"] = projectData

    reportData = {}
    reportData["reportName"] = reportName
    reportData["projectID"] = projectID
    reportData["reportVersion"] = reportVersion
    reportData["projectName"] = projectName
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
            nodeDetails["projectID"] = childProject["id"]
            nodeDetails["parent"] = parentID
            nodeDetails["projectName"] = childProject["name"]
            nodeDetails["projectLink"] = baseURL + "/codeinsight/FNCI#myprojectdetails/?id=" + str(childProject["id"]) + "&tab=projectInventory"

            projectList.append( nodeDetails )

            create_project_hierarchy(childProject, childProject["id"], projectList, baseURL)

    return projectList


