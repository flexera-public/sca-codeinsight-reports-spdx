'''
Copyright 2023 Flexera Software LLC
See LICENSE.TXT for full license text
SPDX-License-Identifier: MIT

Author : sgeary  
Created On : Wed Dec 06 2023
File : report_artifacts_tagvalue.py
'''
import logging
logger = logging.getLogger(__name__)

#--------------------------------------------------------------------------------#

def generate_tagvalue_report(reportData):
    logger.info("    Entering generate_tagvalue_report")

    reportFileNameBase = reportData["reportFileNameBase"]
    reportDetails = reportData["reportDetails"]

    tagvalueFile = reportFileNameBase + ".spdx"

    # Sine the data was gathered in the expected format just
    # write the data directly into the json file
    try:
        report_ptr = open(tagvalueFile,"w")
    except:
        print("Failed to open file %s:" %tagvalueFile)
        logger.error("Failed to open file %s:" %tagvalueFile)
        return {"errorMsg" : "Failed to open file %s:" %tagvalueFile}

    report_ptr.write("SPDXVersion: %s\n" %reportDetails["spdxVersion"])
    report_ptr.write("DataLicense: %s\n" %reportDetails["dataLicense"])
    report_ptr.write("SPDXID: %s\n" %reportDetails["SPDXID"])
    report_ptr.write("DocumentName: %s\n" %reportDetails["name"])
    report_ptr.write("DocumentNamespace: %s\n" %reportDetails["documentNamespace"])
    for creator in reportDetails["creationInfo"]["creators"]:
        report_ptr.write("Creator: %s\n" %creator)
    report_ptr.write("Created:  %s\n" %reportDetails["creationInfo"]["created"])

 
    report_ptr.write("\n")
    
    ##########################################################
    #  Enter the extracted license informatino into the report
    if "hasExtractedLicensingInfos" in reportDetails:

        report_ptr.write("##------------------------------\n")
        report_ptr.write("##  License Identifiers\n")
        report_ptr.write("##------------------------------\n")
        report_ptr.write("\n")
 
        for licenseReferencePacakgeIdentifier in reportDetails["hasExtractedLicensingInfos"]:
            
            report_ptr.write("LicenseID: %s\n" %(licenseReferencePacakgeIdentifier["licenseId"]))
            report_ptr.write("LicenseName: %s\n" %(licenseReferencePacakgeIdentifier["name"]))
            report_ptr.write("ExtractedText:  %s\n" %(licenseReferencePacakgeIdentifier["extractedText"]))
            
            # Split the comment based on the |

            if len(licenseReferencePacakgeIdentifier["comment"]) > 0:
                report_ptr.write("LicenseComment: <text>%s</text>\n" %licenseReferencePacakgeIdentifier["comment"])
        
        report_ptr.write("\n")

    report_ptr.write("##------------------------------\n")
    report_ptr.write("##  Package Information\n")
    report_ptr.write("##------------------------------\n")
    report_ptr.write("\n")

    ##########################################################
    #  Enter the package level details into the report
    for packageDetails in reportDetails["packages"]:

        report_ptr.write("#### Package: %s\n" %packageDetails["name"])
        report_ptr.write("\n")
        report_ptr.write("PackageName: %s\n" %packageDetails["name"])
        report_ptr.write("SPDXID: %s\n" %(packageDetails["SPDXID"]))
        if "versionInfo" in packageDetails:
            report_ptr.write("PackageVersion: %s\n" %packageDetails["versionInfo"])
        report_ptr.write("PackageSupplier: %s\n" %packageDetails["supplier"])
        report_ptr.write("PackageHomePage: %s\n" %packageDetails["homepage"])
        report_ptr.write("PackageDownloadLocation: %s\n" %packageDetails["downloadLocation"])   

        if "packageVerificationCode" in packageDetails:
            report_ptr.write("PackageVerificationCode: %s\n" %packageDetails["packageVerificationCode"]["packageVerificationCodeValue"])

        if "packageLicenseInfoFromFiles" in packageDetails:
            for licenseFromFile in packageDetails["packageLicenseInfoFromFiles"]:
                report_ptr.write("PackageLicenseInfoFromFiles: %s\n" %licenseFromFile)

        report_ptr.write("PackageLicenseConcluded: %s\n" %packageDetails["licenseConcluded"])
        report_ptr.write("PackageLicenseDeclared: %s\n" %packageDetails["licenseDeclared"])
        report_ptr.write("PackageCopyrightText: %s\n" %packageDetails["copyrightText"])

        # Is there file data?
        if "filesAnalyzed" in packageDetails:
            report_ptr.write("FilesAnalyzed: %s\n" %packageDetails["filesAnalyzed"])
        else:
            for license in packageDetails["licenseInfoFromFiles"]:
                report_ptr.write("PackageLicenseInfoFromFiles: %s\n" %license)

        if packageDetails["name"] != "OtherFiles":
            if "externalRefs" in packageDetails:
                for externalRef in packageDetails["externalRefs"]:
                    report_ptr.write("ExternalRef: %s %s %s\n" %(externalRef["referenceCategory"], externalRef["referenceType"], externalRef["referenceLocator"]))

        report_ptr.write("\n")

        if packageDetails["SPDXID"] in reportData["packageFiles"]:

            report_ptr.write("##------------------------------\n")
            report_ptr.write("##  Package File Details\n")
            report_ptr.write("##------------------------------\n")
            report_ptr.write("\n")

            for fileDetails in reportData["packageFiles"][packageDetails["SPDXID"]]:
                report_ptr.write("## ----------------------- File -----------------------\n")
                report_ptr.write("FileName: ./%s\n" %fileDetails["fileName"])
                report_ptr.write("SPDXID: %s\n" %fileDetails["SPDXID"])

                for checksum in fileDetails["checksums"]:
                    report_ptr.write("FileChecksum: %s: %s\n" %(checksum["algorithm"], checksum["checksumValue"] ))
                                    
                report_ptr.write("LicenseConcluded: %s\n" %fileDetails["licenseConcluded"])

                if len(fileDetails["copyrightText"]) > 0:
                    report_ptr.write("FileCopyrightText: <text>%s</text>\n" %fileDetails["copyrightText"])
                    

                for license in fileDetails["licenseInfoInFiles"]:
                    report_ptr.write("LicenseInfoInFile: %s\n" %license)

                report_ptr.write("\n")


    ##########################################################
    #  Enter the relationship details in to the report
    if "relationships" in reportDetails: 
        report_ptr.write("##------------------------------\n")
        report_ptr.write("##  Relationships\n")
        report_ptr.write("##------------------------------\n")
        report_ptr.write("\n")

        for relationship in reportDetails["relationships"]:
            report_ptr.write("Relationship: %s %s %s\n" %(relationship["spdxElementId"], relationship["relationshipType"], relationship["relatedSpdxElement"]))

    report_ptr.close() 

    logger.info("    Exiting generate_tagvalue_report")

    return tagvalueFile