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
import base64

logger = logging.getLogger(__name__)

#--------------------------------------------------------------------------------#
def create_report_artifacts(reportData):
    logger.info("Entering create_report_artifacts")

    # Dict to hold the complete list of reports
    reports = {}

    # Crete a report for each project within the hierarchy
    # and return a list of the files there were created.
    spdxTextFiles = generate_spdx_text_report(reportData)

    if len(reportData["projectList"]) == 1:
        reports["viewable"] = spdxTextFiles[0]
        reports["allFormats"] = spdxTextFiles
    else:
        sumamryFile = generate_spdx_summary_report(reportData, spdxTextFiles)
        reports["viewable"] = sumamryFile
        reports["allFormats"] = spdxTextFiles
        reports["allFormats"].append(sumamryFile)

    logger.info("Exiting create_report_artifacts")
    
    return reports 

#--------------------------------------------------------------------------------#

def generate_spdx_summary_report(reportData, spdxTextFiles):
    logger.info("Entering generate_spdx_summary_report")

    reportName = reportData["reportName"]
    fileNameTimeStamp = reportData["fileNameTimeStamp"]

    summaryTextFile = reportName.replace(" ", "_") + "-summary-" + fileNameTimeStamp + ".txt"
    logger.debug("summaryTextFile: %s" %summaryTextFile)

    try:
        report_ptr = open(summaryTextFile,"w")
    except:
        logger.error("Failed to open summaryTextFile %s:" %summaryTextFile)
        raise

    report_ptr.write("An SPDX report has been generated for each project within the specified hierachy. These reports can be found within the downloadable zipfile within Code Insight. \n\n")
    report_ptr.write("Below are the mappings between the project name and the associated SPDX report for the project:\n")
    report_ptr.write("\n")

    for spdx in spdxTextFiles:
        # The name of the SPDX file includes the project ID so we can grab that and map it back to the project name within projectList
        projectID = spdx.split("-")[-3] # project ID is the 3rd item from the last in the report name
        projectName = list(filter(lambda project: project['projectID'] == projectID, reportData["projectList"]))[0]["projectName"]
        report_ptr.write("\t-  SPDX report for project: %s --> %s\n" %(projectName, spdx ))


    report_ptr.close() 
    logger.info("    Exiting generate_spdx_summary_report")

    return summaryTextFile


#--------------------------------------------------------------------------------#

def generate_spdx_text_report(reportData):
    logger.info("Entering generate_spdx_text_report")
    
    reportName = reportData["reportName"]
    fileNameTimeStamp = reportData["fileNameTimeStamp"]
    projectID = reportData["projectID"]
    SPDXData = reportData["SPDXData"]

    SPDXReports = []


    for projectID in SPDXData["projectData"]:

        textFile = reportName.replace(" ", "_") + "-" + str(projectID)  + "-" + fileNameTimeStamp + ".spdx"
        logger.debug("textFile: %s" %textFile)

        try:
            report_ptr = open(textFile,"w")
        except:
            logger.error("Failed to open textFile %s:" %textFile)
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
        SPDXReports.append(textFile)

    logger.info("    Exiting generate_spdx_text_report")

    return SPDXReports

####################################################################
def encodeImage(imageFile):

    #############################################
    # Create base64 variable for branding image
    try:
        with open(imageFile,"rb") as image:
            logger.debug("Encoding image: %s" %imageFile)
            encodedImage = base64.b64encode(image.read())
            return encodedImage
    except:
        logger.error("Unable to open %s" %imageFile)
        raise
