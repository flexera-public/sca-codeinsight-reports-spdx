'''
Copyright 2021 Flexera Software LLC
See LICENSE.TXT for full license text
SPDX-License-Identifier: MIT

Author : sgeary  
Created On : Tue Apr 27 2021
File : report_artifacts.py
'''

import logging
from datetime import datetime

logger = logging.getLogger(__name__)

#--------------------------------------------------------------------------------#
def create_report_artifacts(reportData):
    logger.info("Entering create_report_artifacts")

    # Dict to hold the complete list of reports
    reports = {}
    packageReports = []

    reportName = reportData["reportName"]
    reportVersion = reportData["reportVersion"]
    SPDXVersion = reportData["SPDXVersion"]
    DataLicense = reportData["DataLicense"]

    # Create a seperate SPDX report for each inventory item
    for package in reportData["spdxPackages"]:
        spdtTextFile = generate_spdx_text_report(reportName, reportVersion, SPDXVersion, DataLicense, reportData["spdxPackages"][package] )
        packageReports.append(spdtTextFile)
    
    #reports["viewable"] = spdtTextFile
    reports["allFormats"] = packageReports

    logger.info("Exiting create_report_artifacts")
    
    return reports 

#--------------------------------------------------------------------------------#
def generate_spdx_text_report(reportName, reportVersion, SPDXVersion, DataLicense, packageData):
    logger.info("Entering generate_spdx_text_report")

    packageName = packageData["packageName"]
    packageFiles = packageData["files"]
  
    # Grab the current date/time for report date stamp
    now = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")

    textFile = reportName.replace(" ", "_") + "_" + packageName + ".spdx"
    logger.debug("textFile: %s" %textFile)

    try:
        report_ptr = open(textFile,"w")
    except:
        logger.error("Failed to open textFile %s:" %textFile)
        raise

    report_ptr.write("SPDXVersion: %s\n" %SPDXVersion)
    report_ptr.write("DataLicense: %s\n" %DataLicense)
    report_ptr.write("SPDXID: SPDXRef-DOCUMENT\n")
    report_ptr.write("DocumentName: %s\n" %packageName.replace(" ", "_"))
    report_ptr.write("DocumentNamespace:  *** TBD - Mandatory - Something unique to ref this doc\n")
    report_ptr.write("Creator: Tool:  Code Insight SPDX Report v%s\n" %reportVersion)
    report_ptr.write("Created:  %s\n" %now)

    report_ptr.write("\n")
    report_ptr.write("##------------------------------\n")
    report_ptr.write("##  Package Information\n")
    report_ptr.write("##------------------------------\n")
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
    report_ptr.write("##  File Information\n")
    report_ptr.write("##------------------------------\n")
    report_ptr.write("\n")

    for file in packageFiles:
        report_ptr.write("## ----------------------- File -----------------------\n")
        report_ptr.write("FileName: %s\n" %file)
        report_ptr.write("SPDXID: %s\n" %packageFiles[file]["SPDXID"])
        report_ptr.write("FileType: %s\n" %packageFiles[file]["FileType"])
        #report_ptr.write("FileChecksum: SHA1: %s\n" %packageFiles[file]["SHA1"]) # TODO Add SHA1
        report_ptr.write("FileChecksum: MD5: %s\n" %packageFiles[file]["fileMD5"])
        report_ptr.write("LicenseConcluded: %s\n" %packageFiles[file]["LicenseConcluded"])

        for license in packageFiles[file]["LicenseInfoInFile"]:
            report_ptr.write("LicenseInfoInFile: %s\n" %license)
        
        for copyright in packageFiles[file]["FileCopyrightText"]:
            report_ptr.write("FileCopyrightText: %s\n" %copyright)
        
        report_ptr.write("\n")

    report_ptr.write("##------------------------------\n")
    report_ptr.write("##  Relationship Information\n")
    report_ptr.write("##------------------------------\n")
    report_ptr.write("\n")

    report_ptr.write("Relationship: %s DESCIBES %s\n" %("SPDXRef-DOCUMENT", packageData["SPDXID"] ))
    report_ptr.write("Relationship: %s DESCRIBED_BY  %s\n" %(packageData["SPDXID"], "SPDXRef-DOCUMENT" ))

    report_ptr.write("\n")

    for file in packageFiles:
        report_ptr.write("## ----------------------- Relationship -----------------------\n")
        report_ptr.write("Relationship: %s CONTAINS  %s\n" %(packageData["SPDXID"], packageFiles[file]["SPDXID"] ))
        report_ptr.write("\n")

    report_ptr.close() 

    logger.info("    Exiting generate_spdx_text_report")

    return textFile

