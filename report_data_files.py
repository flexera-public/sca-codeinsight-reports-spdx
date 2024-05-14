'''
Copyright 2023 Flexera Software LLC
See LICENSE.TXT for full license text
SPDX-License-Identifier: MIT

Author : sgeary  
Created On : Tue Aug 29 2023
File : report_data_files.py
'''
import logging, unicodedata, re
import common.api.project.get_scanned_files
import common.api.project.get_project_evidence
import SPDX_license_mappings

logger = logging.getLogger(__name__)

#-------------------------------------------------
def manage_file_details(baseURL, authToken, projectID, hasExtractedLicensingInfos, includeUnassociatedFiles):

    filePathToID, fileDetails = get_scanned_file_details(baseURL, authToken, projectID, includeUnassociatedFiles)

    fileDetails, hasExtractedLicensingInfos = get_file_evidence(baseURL, authToken, projectID, fileDetails, hasExtractedLicensingInfos)

    return filePathToID, fileDetails, hasExtractedLicensingInfos


#-----------------------------
def get_scanned_file_details(baseURL, authToken, projectID, includeUnassociatedFiles):

    filePathToID = {} # Allow for mapping from inventory file path to details about the file itself
    filePathToID["inInventory"] = {}
    filePathToID["notInInventory"] = {}
    fileDetails = {}

    # Collect a list of the scanned files
    print("                + Collect data for all scanned files.")
    logger.info("                Collect data for all scanned.")
    scannedFiles = common.api.project.get_scanned_files.get_scanned_files_details_with_MD5_and_SHA1(baseURL, projectID, authToken)
    print("                - Collected data for %s scanned file(s)." %len(scannedFiles))
    logger.info("                Collected data for %s files." %len(scannedFiles))

    # Cycle through each scanned file
    for scannedFile in scannedFiles:
        scannedFileDetails = {}

        scannedFileId = scannedFile["fileId"]
        fileName = scannedFile["filePath"]  
        inInventory = scannedFile["inInventory"]
        remoteFile = scannedFile["remote"]

        # # Don't collect any data for the files we don't care about
        # if inInventory == "false" and not includeUnassociatedFiles:
        #     continue 

        # Create a unique identifier based on fileID and scan location
        if remoteFile == "false":
            uniqueFileID = str(scannedFileId) + "-s"
        else:
            uniqueFileID = str(scannedFileId) + "-r"

        scannedFileDetails["SPDXID"] = "SPDXRef-File-" + uniqueFileID
        scannedFileDetails["fileName"] = fileName
        scannedFileDetails["checksums"] = []
        
        if scannedFile["fileMD5"] is not None:
            checksum = {}
            checksum["algorithm"] = "MD5"
            checksum["checksumValue"] = scannedFile["fileMD5"]
            scannedFileDetails["checksums"].append(checksum)

        if scannedFile["fileSHA1"] is not None:
            checksum = {}
            checksum["algorithm"] = "SHA1"
            checksum["checksumValue"] = scannedFile["fileSHA1"]
            scannedFileDetails["checksums"].append(checksum)
            
        scannedFileDetails["licenseConcluded"] = "NOASSERTION"  # TODO - Requires custom fields at file level

        fileDetails[uniqueFileID] = scannedFileDetails

        # Create a mapping beteween the filepath and its ID and SHA1

        filePathDetails = {}
        filePathDetails["uniqueFileID"] = uniqueFileID
        filePathDetails["fileSHA1"] = scannedFile["fileSHA1"]

        if inInventory == "true":
            filePathToID["inInventory"][fileName] = filePathDetails
        else:
            filePathToID["notInInventory"][fileName] = filePathDetails
      
    return filePathToID, fileDetails


#-----------------------------
def get_file_evidence(baseURL, authToken, projectID, fileDetails, hasExtractedLicensingInfos):

    # Collect the copyright/license data per file and create dict based on
    print("                + Collect file level evidence.")
    logger.info("            + Collect file level evidence")
    projectEvidenceDetails = common.api.project.get_project_evidence.get_project_evidence(baseURL, projectID, authToken)
    print("                - File level evidence has been collected.") 
    logger.info("               - File level evidence has been collected.") 

    for fileEvidenceDetails in projectEvidenceDetails["data"]:

        remoteFile = bool(fileEvidenceDetails["remote"])
        scannedFileId = fileEvidenceDetails["scannedFileId"]
        copyrightEvidenceFound= fileEvidenceDetails["copyRightMatches"]
        licenseEvidenceFound = list(set(fileEvidenceDetails["licenseMatches"]))

        uniqueFileID = str(scannedFileId) + ("-r" if remoteFile else "-s")

        # If the fileID is not in the dict move on (includeUnassociatedFiles?)
        if uniqueFileID not in fileDetails:
            continue

        ##########################################
        # Manage File Level Copyrights
        # Normalize the copyrights in case there are any encoding issues 
        copyrightEvidenceFound = [unicodedata.normalize('NFKD', x).encode('ASCII', 'ignore').decode('utf-8') for x in copyrightEvidenceFound]

        if copyrightEvidenceFound:
            logger.info("            Copyright evidence discovered")
            # The response has the copyright details as a list so convert to a string
            copyrightEvidenceFound = " | ".join(copyrightEvidenceFound)
        else:
            logger.info("            No copyright evidence discovered")
            copyrightEvidenceFound = "NONE"

        ##########################################
        # Manage File Level Licenses
        if licenseEvidenceFound:

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
                    licenseReference = "LicenseRef-%s" %licenseEvidence
                    licenseEvidenceFound[index]  = licenseReference
                    
                    licenseReferenceComment = "SCA Revenera - Observed license details within file"

                    # Since this is an non SPDX ID we need to add to the hasExtractedLicensingInfos section
                    if licenseReference not in hasExtractedLicensingInfos:
                        # It's not there so create a new entry
                        hasExtractedLicensingInfos[licenseReference] = {}
                        hasExtractedLicensingInfos[licenseReference]["licenseId"] = licenseReference
                        hasExtractedLicensingInfos[licenseReference]["name"] = licenseEvidence
                        hasExtractedLicensingInfos[licenseReference]["extractedText"] = licenseEvidence
                        hasExtractedLicensingInfos[licenseReference]["comment"] = [licenseReferenceComment]
                    else:
                        # It's aready there but is the comment the same as any previous entry
                        if licenseReferenceComment not in hasExtractedLicensingInfos[licenseReference]["comment"]:
                            hasExtractedLicensingInfos[licenseReference]["comment"].append(licenseReferenceComment)
        else:
            licenseEvidenceFound = ["NONE"]

        # Add the evidence details to the appropriate area for this file
        fileDetails[uniqueFileID]["copyrightText"]= copyrightEvidenceFound
        fileDetails[uniqueFileID]["licenseConcluded"]= "NOASSERTION"
        fileDetails[uniqueFileID]["licenseInfoInFiles"]= licenseEvidenceFound

    return fileDetails, hasExtractedLicensingInfos