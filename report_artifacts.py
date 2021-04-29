'''
Copyright 2021 Flexera Software LLC
See LICENSE.TXT for full license text
SPDX-License-Identifier: MIT

Author : sgeary  
Created On : Tue Apr 27 2021
File : report_artifacts.py
'''

import logging
import os
from datetime import datetime
import base64

logger = logging.getLogger(__name__)

#--------------------------------------------------------------------------------#
def create_report_artifacts(reportData):
    logger.info("Entering create_report_artifacts")

    # Dict to hold the complete list of reports
    reports = {}
    packageReports = []

    reportName = reportData["reportName"]
    SPDXVersion = reportData["SPDXVersion"]

    # Create a seperate SPDX report for each inventory item
    for package in reportData["spdxPackages"]:
        spdtTextFile = generate_spdx_text_report(reportName, SPDXVersion, reportData["spdxPackages"][package] )
        packageReports.append(spdtTextFile)
    
    #reports["viewable"] = spdtTextFile
    reports["allFormats"] = packageReports

    logger.info("Exiting create_report_artifacts")
    
    return reports 

#--------------------------------------------------------------------------------#
def generate_spdx_text_report(reportName, SPDXVersion, packageData):
    logger.info("Entering generate_spdx_text_report")

    packageName = packageData["packageName"]
    packageFiles = packageData["files"]
   
    # Grab the current date/time for report date stamp
    now = datetime.now().strftime("%B %d, %Y at %H:%M:%S")

    textFile = reportName.replace(" ", "_") + "_" + packageName.replace(" ", "_")   + ".txt"
    logger.debug("textFile: %s" %textFile)

    try:
        report_ptr = open(textFile,"w")
    except:
        logger.error("Failed to open textFile %s:" %textFile)
        raise

    report_ptr.write("SPDXVersion: %s\n" %SPDXVersion)
    report_ptr.write("\n")
    report_ptr.write("##------------------------------------------------------\n")
    report_ptr.write("##  SPDX 2.0 by Revenera\n")
    report_ptr.write("##------------------------------------------------------\n")
    report_ptr.write("\n")
    report_ptr.write("\n")
    report_ptr.write("##------------------------------\n")
    report_ptr.write("##  Document Information\n")
    report_ptr.write("##------------------------------\n")
    report_ptr.write("DataLicense: CC0-1.0\n")
    report_ptr.write("SPDXID: SPDXRef-DOCUMENT\n")
    report_ptr.write("DocumentName: wr-lx-setup-master.zip\n")
    report_ptr.write("DocumentNamespace:  http://spdx.windriver.com/Reports2.0/604d9f2f5e1b8a11031a6b7d646ae2f1351df70b\n")
    report_ptr.write('''DocumentComment: <text>This file contains computer automated SPDX data. Computer automated data is created by using only computer automation analysis on the source code files contained in the package. That is, no human experts participated in the source code analysis. Although we continuously work to improve the quality by adding and/or improving various heuristics, and accessing different databases and rule-based systems, the quality is bounded by what can be achieved by way of computer automation. Please send your feedback to: spdx@WindRiver.com.  DISCLAIMER: This document is provided "as is" without any warranty whatsoever. This documentation may not be referenced or relied upon for its accuracy or comprehensiveness, or to determine legal obligations with respect to open source code contained in the software package it represents. Such determinations should be based upon recipient's independent legal analysis and by reference to the notices and licenses contained within the open source code itself. Wind River may change the contents of this document at any time at its sole discretion, and Wind River shall have no liability whatsoever arising from recipient's use of this information. </text>\n''')

    report_ptr.write("\n")
    report_ptr.write("##------------------------------\n")
    report_ptr.write("##  Package Information\n")
    report_ptr.write("##------------------------------\n")
    report_ptr.write("\n")
    report_ptr.write("PackageName: %s\n" %packageName)
    report_ptr.write("SPDXID: SPDXRef-Pkg-%s\n" %packageName)
    report_ptr.write("PackageFileName: wr-lx-setup-master.zip\n")
    report_ptr.write("PackageDownloadLocation: NOASSERTION\n")
    report_ptr.write("PackageVerificationCode: 760dcf682a7ce765292e7b0596b12dd046b13023\n")
    report_ptr.write("PackageChecksum: SHA1: 604d9f2f5e1b8a11031a6b7d646ae2f1351df70b\n")
    report_ptr.write("PackageChecksum: SHA256: 2cd4cef56f843f7c9e2b255609ad49978bbd9667db3ab74f9bbc4204b2f5be84\n")
    report_ptr.write("PackageChecksum: MD5: e853376e709a1280a443d687a8d7215f\n")

    report_ptr.write("## -------------- Package Licensing --------------\n")
    report_ptr.write("PackageLicenseConcluded: GPL-2.0\n")
    report_ptr.write("PackageLicenseDeclared: GPL-2.0\n")
    report_ptr.write("PackageLicenseInfoFromFiles: GPL-2.0\n")
    report_ptr.write("PackageCopyrightText: NOASSERTION\n")

    report_ptr.write("\n")
    report_ptr.write("##------------------------------\n")
    report_ptr.write("##  File Information\n")
    report_ptr.write("##------------------------------\n")
    report_ptr.write("\n")

    for file in packageFiles:
        report_ptr.write("## ----------------------- File -----------------------\n")
        report_ptr.write("##\n")
        report_ptr.write("FileName: %s\n" %file)
        report_ptr.write("SPDXID: %s\n" %packageFiles[file]["SPDXID"])
        report_ptr.write("FileType: %s\n" %packageFiles[file]["FileType"])
        report_ptr.write("FileChecksum: MD5:: %s\n" %packageFiles[file]["fileMD5"])
        report_ptr.write("LicenseConcluded: %s\n" %packageFiles[file]["LicenseConcluded"])
        report_ptr.write("LicenseInfoInFile: %s\n" %packageFiles[file]["LicenseInfoInFile"])
        report_ptr.write("FileCopyrightText: %s\n" %packageFiles[file]["FileCopyrightText"])
        report_ptr.write("\n")

    report_ptr.write("##------------------------------\n")
    report_ptr.write("##  Relationship Information\n")
    report_ptr.write("##------------------------------\n")
    report_ptr.write("")



    report_ptr.close() 

    logger.info("    Exiting generate_spdx_text_report")

    return textFile

