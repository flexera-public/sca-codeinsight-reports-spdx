'''
Copyright 2021 Flexera Software LLC
See LICENSE.TXT for full license text
SPDX-License-Identifier: MIT

Author : sgeary  
Created On : Tue Nov 09 2021
File : report_artifacts_tag_value.py
'''
import logging
import re
from datetime import datetime
logger = logging.getLogger(__name__)

#--------------------------------------------------------------------------------#

def generate_tag_value_spdx_report(reportData):
    logger.info("    Entering generate_spdx_text_report")
    
    reportName = reportData["reportName"]
    fileNameTimeStamp =  reportData["fileNameTimeStamp"] 
    projectID = reportData["projectID"]
    SPDXData = reportData["SPDXData"]

    SPDXReports = []


    for projectID in SPDXData["projectData"]:

        projectName = SPDXData["projectData"][projectID]["projectName"]
        # Clean up the project name in case there are special characters
        projectNameForFile = re.sub(r"[^a-zA-Z0-9]+", '-', projectName )

        spdxFile = projectNameForFile + "-" + projectID + "-" + reportName.replace(" ", "_") + "-" + fileNameTimeStamp + ".spdx"
        logger.debug("        Creating project SPDX file: %s" %spdxFile)

        try:
            report_ptr = open(spdxFile,"w")
        except:
            print("Fail open error due to project name??")
            logger.error("Failed to open textFile %s:" %spdxFile)
            raise
     

        # Enter top level SPDX details
        report_ptr.write("SPDXVersion: %s\n" %SPDXData["SPDXVersion"])
        report_ptr.write("DataLicense: %s\n" %SPDXData["DataLicense"])
        report_ptr.write("SPDXID: SPDXRef-DOCUMENT\n")
        report_ptr.write("DocumentName: %s\n" %SPDXData["projectData"][projectID]["DocumentName"])
        report_ptr.write("DocumentNamespace: %s\n" %SPDXData["projectData"][projectID]["DocumentNamespace"])
        report_ptr.write("Creator: Tool: %s\n" %SPDXData["Creator"])
        report_ptr.write("Created:  %s\n" %(datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")))

        report_ptr.write("\n")
        report_ptr.write("##------------------------------\n")
        report_ptr.write("##  Package Information\n")
        report_ptr.write("##------------------------------\n")
        report_ptr.write("\n")

        for package in SPDXData["projectData"][projectID]["spdxPackages"]:

            packageData = SPDXData["projectData"][projectID]["spdxPackages"][package]

            packageName = packageData["packageName"]
            packageFiles = packageData["files"]

            report_ptr.write("\n")
            report_ptr.write("#### Package: %s\n" %packageName)
            report_ptr.write("\n")
            report_ptr.write("PackageName: %s\n" %packageName)
            report_ptr.write("SPDXID: %s\n" %(packageData["SPDXID"]))
            report_ptr.write("PackageDownloadLocation: %s\n" %packageData["PackageDownloadLocation"])
            report_ptr.write("PackageVerificationCode: %s\n" %packageData["PackageVerificationCode"])

            report_ptr.write("PackageLicenseConcluded: %s\n" %packageData["PackageLicenseConcluded"])

            for licenseFromFile in packageData["PackageLicenseInfoFromFiles"]:
                report_ptr.write("PackageLicenseInfoFromFiles: %s\n" %licenseFromFile)

            report_ptr.write("PackageLicenseDeclared: %s\n" %packageData["PackageLicenseDeclared"])
            report_ptr.write("PackageCopyrightText: NOASSERTION\n")

            report_ptr.write("\n")
            report_ptr.write("##------------------------------\n")
            report_ptr.write("##  Package File Information\n")
            report_ptr.write("##------------------------------\n")
            report_ptr.write("\n")

            for file in packageFiles:
                report_ptr.write("## ----------------------- File -----------------------\n")
                report_ptr.write("FileName: %s\n" %file)
                report_ptr.write("SPDXID: %s\n" %packageFiles[file]["SPDXID"])
                report_ptr.write("FileType: %s\n" %packageFiles[file]["FileType"])
                report_ptr.write("FileChecksum: SHA1: %s\n" %packageFiles[file]["fileSHA1"])
                report_ptr.write("FileChecksum: MD5: %s\n" %packageFiles[file]["fileMD5"])
                report_ptr.write("LicenseConcluded: %s\n" %packageFiles[file]["FileLicenseConcluded"])

                for license in packageFiles[file]["LicenseInfoInFile"]:
                    report_ptr.write("LicenseInfoInFile: %s\n" %license)
                
                for copyright in packageFiles[file]["FileCopyrightText"]:
                    report_ptr.write("FileCopyrightText: %s\n" %copyright)
                
                report_ptr.write("\n")

            report_ptr.write("\n")
            report_ptr.write("##------------------------------\n")
            report_ptr.write("##  Package Relationship Information\n")
            report_ptr.write("##------------------------------\n")
            report_ptr.write("\n")


            packageData = SPDXData["projectData"][projectID]["spdxPackages"][package]

            packageName = packageData["packageName"]
            packageFiles = packageData["files"]

            report_ptr.write("Relationship: %s DESCRIBES %s\n" %("SPDXRef-DOCUMENT", packageData["SPDXID"] ))
            report_ptr.write("Relationship: %s DESCRIBED_BY  %s\n" %(packageData["SPDXID"], "SPDXRef-DOCUMENT" ))

            for file in packageFiles:
                report_ptr.write("Relationship: %s CONTAINS %s\n" %(packageData["SPDXID"], packageFiles[file]["SPDXID"] ))
            report_ptr.write("\n")

        report_ptr.close() 
        SPDXReports.append(spdxFile)

    logger.info("    Exiting generate_spdx_text_report")

    return SPDXReports
