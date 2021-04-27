'''
Copyright 2020 Flexera Software LLC
See LICENSE.TXT for full license text
SPDX-License-Identifier: MIT

Author : sgeary  
Created On : Wed Oct 21 2020
File : report_data.py
'''

import logging
import CodeInsight_RESTAPIs.project.get_project_inventory
import CodeInsight_RESTAPIs.project.get_scanned_files
import CodeInsight_RESTAPIs.project.get_project_evidence

import SPDX_license_mappings # To map evidence to an SPDX license name

logger = logging.getLogger(__name__)

#-------------------------------------------------------------------#
def gather_data_for_report(baseURL, projectID, authToken, reportName):
    logger.info("Entering gather_data_for_report")

    projectInventory = CodeInsight_RESTAPIs.project.get_project_inventory.get_project_inventory_details(baseURL, projectID, authToken)
    inventoryItems = projectInventory["inventoryItems"]

    spdxPackages = {}

    for inventoryItem in inventoryItems:
        packageName = inventoryItem["name"]
        filesInInventory = inventoryItem["filePaths"]
        selectedLicenseSPDXIdentifier = inventoryItem["selectedLicenseSPDXIdentifier"]

        
        # Contains the deatils for the package/inventory item
        spdxPackages[packageName] ={}
        spdxPackages[packageName]["SPDXID"] = "SPDXRef-Pkg-" + packageName
        spdxPackages[packageName]["PackageFileName"] = packageName
        spdxPackages[packageName]["PackageLicenseDeclared"] = selectedLicenseSPDXIdentifier
        spdxPackages[packageName]["containedFiles"] = filesInInventory


    # Dictionary to contain all of the file specific data
    fileDetails = {}
    fileDetails["remoteFiles"] = {}
    fileDetails["localFiles"] = {}

    # Collect the copyright/license data per file and create dict based on 
    projectEvidenceDetails = CodeInsight_RESTAPIs.project.get_project_evidence.get_project_evidence(baseURL, projectID, authToken)
  

    # Dictionary to contain all of the file specific data
    fileEvidence = {}
    fileEvidence["remoteFiles"] = {}
    fileEvidence["localFiles"] = {}
    for fileEvidenceDetails in projectEvidenceDetails["data"]:
        evidence = {}
        remote = fileEvidenceDetails["remote"]
        filePath = fileEvidenceDetails["filePath"]
        evidence["copyrightEvidienceFound"] = fileEvidenceDetails["copyRightMatches"]
        evidence["licenseEvidenceFound"] =  fileEvidenceDetails["licenseMatches"]

        if remote:
            fileEvidence["localFiles"][filePath] = evidence
        else: 
            fileEvidence["remoteFiles"][filePath] = evidence


    # Collect a list of the scanned files
    scannedFiles = CodeInsight_RESTAPIs.project.get_scanned_files.get_scanned_files_details(baseURL, projectID, authToken)

    # Cycle through each scanned file
    for scannedFile in scannedFiles:
        scannedFileDetails = {}
        remoteFile = scannedFile["remote"]
        FileName = scannedFile["filePath"]  

        scannedFileDetails["fileId"] = scannedFile["fileId"]
        scannedFileDetails["fileMD5"] = scannedFile["fileMD5"]
        scannedFileDetails["inInventory"] = scannedFile["inInventory"]

        scannedFileDetails["SPDXID"] = "SPDXRef-File-" + FileName

        fileContainsEvidence = scannedFile["containsEvidence"]   

        if fileContainsEvidence:

            if remoteFile:
                scannedFileDetails["FileCopyrightText"] = fileEvidence["remoteFiles"][FileName]["copyrightEvidienceFound"]
                scannedFileDetails["LicenseInfoInFile"] = fileEvidence["remoteFiles"][FileName]["licenseEvidenceFound"]
            else:
                scannedFileDetails["FileCopyrightText"] = fileEvidence["localFiles"][FileName]["copyrightEvidienceFound"]
                scannedFileDetails["LicenseInfoInFile"] = fileEvidence["localFiles"][FileName]["licenseEvidenceFound"]

        
        if remoteFile:
            fileDetails["localFiles"][FileName] = scannedFileDetails
        else: 
            fileDetails["remoteFiles"][FileName] = scannedFileDetails


    reportData = {}
    reportData["spdxPackages"] = spdxPackages
    reportData["fileDetails"] = fileDetails

    return reportData




