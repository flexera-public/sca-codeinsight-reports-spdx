'''
Copyright 2023 Flexera Software LLC
See LICENSE.TXT for full license text
SPDX-License-Identifier: MIT

Author : sgeary  
Created On : Tue Aug 29 2023
Modified By : sarthak
Modified On: Mon 07 2025
File : report_data_files.py
'''
import logging, unicodedata, re
import report_data_db
import SPDX_license_mappings

logger = logging.getLogger(__name__)

#-------------------------------------------------
def manage_file_details(projectID, hasExtractedLicensingInfos, includeUnassociatedFiles, includeCopyrightsData):

    filePathToID, fileDetails = get_scanned_file_details(projectID, includeUnassociatedFiles)

    fileDetails, hasExtractedLicensingInfos = get_file_evidence(projectID, fileDetails, hasExtractedLicensingInfos, includeCopyrightsData)

    return filePathToID, fileDetails, hasExtractedLicensingInfos


#-----------------------------
def get_scanned_file_details(projectID, includeUnassociatedFiles):

    filePathToID = {} # Allow for mapping from inventory file path to details about the file itself
    filePathToID["inInventory"] = {}
    filePathToID["notInInventory"] = {}
    fileDetails = {}

    # Collect a list of the scanned files
    print("                + Collect data for all scanned files.")
    logger.info("                Collect data for all scanned.")
    scannedFiles = report_data_db.get_server_scanned_files(projectID, includeUnassociatedFiles)
    for file in scannedFiles:
        file["remote"] = False

    remoteFiles = report_data_db.get_remote_scanned_files(projectID, includeUnassociatedFiles)
    logger.info("                Collected remote scanned files data for %s files." %len(remoteFiles))
    for file in remoteFiles:
        file["remote"] = True
    
    allScannedFiles = scannedFiles + remoteFiles

    # Cycle through each scanned file
    for scannedFile in allScannedFiles:
        scannedFileDetails = {}

        scannedFileId = scannedFile["fileId"]
        fileName = scannedFile["filePath"]  
        
        # The custom query returns the inventory ID or None for inInventory
        inInventory = scannedFile["inInventory"] != None

        # Don't collect any data for the files we don't care about if the option is not set
        if not includeUnassociatedFiles and not inInventory:
            continue

        file_type_suffix = "-r" if scannedFile["remote"] else "-s"
        uniqueFileID = str(scannedFileId) + file_type_suffix

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

        if inInventory:
            filePathToID["inInventory"][fileName] = filePathDetails
        else:
            filePathToID["notInInventory"][fileName] = filePathDetails
      
    return filePathToID, fileDetails


#-----------------------------
def get_file_evidence(projectID, fileDetails, hasExtractedLicensingInfos, includeCopyrightsData):

    # Collect the copyright/license data per file and create dict based on
    print("                + Collect file level evidence.")
    logger.info("            + Collect file level evidence")
    projectEvidenceDetails = report_data_db.get_project_evidence(projectID)
    print("                - File level evidence has been collected.") 
    logger.info("               - File level evidence has been collected.") 

    # Structure the evidence details by ID
    structuredEvidenceDetails = structure_evidence_details(projectEvidenceDetails)
    for fileId, fileEvidenceDetails in structuredEvidenceDetails.items():

        remoteFile = False if fileEvidenceDetails["REMOTE_ID"] is None else True
        scannedFileId = fileEvidenceDetails["ID"]
        if includeCopyrightsData:
            copyrightEvidenceFound = fileEvidenceDetails["copyRightMatches"]
        licenseEvidenceFound = fileEvidenceDetails["licenseMatches"]

        uniqueFileID = str(scannedFileId) + ("-r" if remoteFile else "-s")

        # If the fileID is not in the dict move on (includeUnassociatedFiles?)
        if uniqueFileID not in fileDetails:
            continue

        if includeCopyrightsData and copyrightEvidenceFound:
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
        else:
            copyrightEvidenceFound = "NONE" if includeCopyrightsData else "NOASSERTION"

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

        # Catch any corner cases?
        if len(licenseEvidenceFound) == 0:
            licenseEvidenceFound = ["NONE"]
            
        # Add the evidence details to the appropriate area for this file
        fileDetails[uniqueFileID]["copyrightText"] = (copyrightEvidenceFound if includeCopyrightsData else "NOASSERTION")
        fileDetails[uniqueFileID]["licenseConcluded"]= "NOASSERTION"
        fileDetails[uniqueFileID]["licenseInfoInFiles"]= licenseEvidenceFound

    return fileDetails, hasExtractedLicensingInfos


#-----------------------------
def structure_evidence_details(projectEvidenceDetails):
    """
    Structure evidence details by ID, collecting non-None values for LICENSE, EMAILURL, COPYRIGHT, SEARCHSTRING into lists
    """
    structuredData = {}
    
    for evidence in projectEvidenceDetails:
        fileId = evidence["ID"]
        
        # Initialize the structure for this ID if it doesn't exist
        if fileId not in structuredData:
            structuredData[fileId] = {
                "ID": fileId,
                "PATH": evidence["PATH"],
                "ALIAS": evidence["ALIAS"],
                "DIGEST": evidence["DIGEST"],
                "MATCHES": evidence["MATCHES"],
                "REMOTE_ID": evidence["REMOTE_ID"],
                "licenseMatches": [],
                "copyRightMatches": [],
                "emailUrlMatches": [],
                "searchTextMatches": []
            }
        
        # Collect non-None values for each category
        if evidence["LICENSE"] is not None and evidence["LICENSE"] not in structuredData[fileId]["licenseMatches"]:
            structuredData[fileId]["licenseMatches"].append(evidence["LICENSE"])
            
        if evidence["COPYRIGHT"] is not None and evidence["COPYRIGHT"] not in structuredData[fileId]["copyRightMatches"]:
            structuredData[fileId]["copyRightMatches"].append(evidence["COPYRIGHT"])
            
        if evidence["EMAILURL"] is not None and evidence["EMAILURL"] not in structuredData[fileId]["emailUrlMatches"]:
            structuredData[fileId]["emailUrlMatches"].append(evidence["EMAILURL"])
            
        if evidence["SEARCHSTRING"] is not None and evidence["SEARCHSTRING"] not in structuredData[fileId]["searchTextMatches"]:
            structuredData[fileId]["searchTextMatches"].append(evidence["SEARCHSTRING"])
    
    return structuredData


if __name__ == "__main__":
    manage_file_details(20, {}, True, True)