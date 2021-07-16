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
import os
import base64

logger = logging.getLogger(__name__)

#--------------------------------------------------------------------------------#
def create_report_artifacts(reportData):
    logger.info("Entering create_report_artifacts")

    # Dict to hold the complete list of reports
    reports = {}

    summaryFile = generate_spdx_html_summary_report(reportData)

    # Create a seperate SPDX report for each inventory item
    spdtTextFiles = generate_spdx_text_report(reportData)
    
    reports["viewable"] = summaryFile
    reports["allFormats"] = spdtTextFiles
    reports["allFormats"].append(summaryFile)

    logger.info("Exiting create_report_artifacts")
    
    return reports 

#--------------------------------------------------------------------------------#
def generate_spdx_html_summary_report(reportData):
    logger.info("Entering generate_spdx_html_summary_report")

    reportName = reportData["reportName"]
    projectName = reportData["projectName"].replace(" - ", "-").replace(" ", "_")
    SPDXData = reportData["SPDXData"]

    scriptDirectory = os.path.dirname(os.path.realpath(__file__))
    cssFile =  os.path.join(scriptDirectory, "html-assets/css/revenera_common.css")
    logoImageFile =  os.path.join(scriptDirectory, "html-assets/images/logo_reversed.svg")
    iconFile =  os.path.join(scriptDirectory, "html-assets/images/favicon-revenera.ico")

    #########################################################
    #  Encode the image files
    encodedLogoImage = encodeImage(logoImageFile)
    encodedfaviconImage = encodeImage(iconFile)
    
    # Grab the current date/time for report date stamp
    now = datetime.now().strftime("%B %d, %Y at %H:%M:%S")

    htmlFile = projectName + "-" + reportName.replace(" ", "_") + ".html"
    logger.debug("htmlFile: %s" %htmlFile)
    
    #---------------------------------------------------------------------------------------------------
    # Create a simple HTML file to display
    #---------------------------------------------------------------------------------------------------
    try:
        html_ptr = open(htmlFile,"w")
    except:
        logger.error("Failed to open htmlfile %s:" %htmlFile)
        raise

    html_ptr.write("<html>\n") 
    html_ptr.write("    <head>\n")

    html_ptr.write("        <!-- Required meta tags --> \n")
    html_ptr.write("        <meta charset='utf-8'>  \n")
    html_ptr.write("        <meta name='viewport' content='width=device-width, initial-scale=1, shrink-to-fit=no'> \n")

    html_ptr.write(''' 
        <link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.5.1/css/bootstrap.min.css" integrity="sha384-VCmXjywReHh4PwowAiWNagnWcLhlEJLA5buUprzK8rxFgeH0kww/aWY76TfkUoSX" crossorigin="anonymous">
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/twitter-bootstrap/4.1.3/css/bootstrap.css">
    ''')


    html_ptr.write("        <style>\n")

    # Add the contents of the css file to the head block
    try:
        f_ptr = open(cssFile)
        logger.debug("Adding css file details")
        for line in f_ptr:
            html_ptr.write("            %s" %line)
        f_ptr.close()
    except:
        logger.error("Unable to open %s" %cssFile)
        print("Unable to open %s" %cssFile)


    html_ptr.write("        </style>\n")  

    html_ptr.write("    	<link rel='icon' type='image/png' href='data:image/png;base64, {}'>\n".format(encodedfaviconImage.decode('utf-8')))
    html_ptr.write("        <title>%s</title>\n" %(reportName))
    html_ptr.write("    </head>\n") 

    html_ptr.write("<body>\n")
    html_ptr.write("<div class=\"container-fluid\">\n")

    #---------------------------------------------------------------------------------------------------
    # Report Header
    #---------------------------------------------------------------------------------------------------
    html_ptr.write("<!-- BEGIN HEADER -->\n")
    html_ptr.write("<div class='header'>\n")
    html_ptr.write("  <div class='logo'>\n")
    html_ptr.write("    <img src='data:image/svg+xml;base64,{}' style='width: 400px;'>\n".format(encodedLogoImage.decode('utf-8')))
    html_ptr.write("  </div>\n")
    html_ptr.write("<div class='report-title'>%s</div>\n" %(reportName))
    html_ptr.write("</div>\n")
    html_ptr.write("<!-- END HEADER -->\n")

    #---------------------------------------------------------------------------------------------------
    # Body of Report
    #---------------------------------------------------------------------------------------------------
    html_ptr.write("<!-- BEGIN BODY -->\n") 

    html_ptr.write("<H5>Individual SPDX report files for project <b>%s</b>, may be found within the downloadable zip file from the project reports tab.</H5><p>\n" %projectName)

    html_ptr.write("<ul class='list-group list-group-flush'>\n")
    for projectName in SPDXData["projectData"]:
        html_ptr.write("<li class='list-group-item'>Project: <b>%s</b></li>\n" %projectName)
        
        html_ptr.write("<ul class='list-group list-group-flush'>\n")

        for package in SPDXData["projectData"][projectName]["spdxPackages"]:
            spdxReportName = SPDXData["projectData"][projectName]["spdxPackages"][package]["reportName"]
            html_ptr.write("<li class='list-group-item'>Generated SPDX report: <b>%s</b></li>\n" %spdxReportName)

        html_ptr.write("</ul>\n")
        html_ptr.write("<hr>\n")  # Add color?
    html_ptr.write("</ul>\n")

    html_ptr.write("<!-- END BODY -->\n")  
    #---------------------------------------------------------------------------------------------------
    # Report Footer
    #---------------------------------------------------------------------------------------------------
    html_ptr.write("<!-- BEGIN FOOTER -->\n")
    html_ptr.write("<div class='report-footer'>\n")
    html_ptr.write("  <div style='float:left'>&copy; 2021 Flexera</div>\n")
    html_ptr.write("  <div style='float:right'>Generated on %s</div>\n" %now)
    html_ptr.write("</div>\n")
    html_ptr.write("<!-- END FOOTER -->\n")   

    html_ptr.write("</div>\n")    

    html_ptr.write("</body>\n") 
    html_ptr.write("</html>\n") 
    html_ptr.close() 

    logger.info("    Exiting generate_spdx_html_summary_report")

    return htmlFile


#--------------------------------------------------------------------------------#

def generate_spdx_text_report(reportData):
    logger.info("Entering generate_spdx_text_report")
    
    reportName = reportData["reportName"]
    reportVersion = reportData["reportVersion"]
    projectName = reportData["projectName"]
    SPDXData = reportData["SPDXData"]

    SPDXReports = []

    for projectName in SPDXData["projectData"]:

        for package in SPDXData["projectData"][projectName]["spdxPackages"]:

            packageData = SPDXData["projectData"][projectName]["spdxPackages"][package]

            packageName = packageData["packageName"]
            packageFiles = packageData["files"]
        
            # Grab the current date/time for report date stamp
            now = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")

            textFile = packageData["reportName"] 
            logger.debug("textFile: %s" %textFile)

            try:
                report_ptr = open(textFile,"w")
            except:
                logger.error("Failed to open textFile %s:" %textFile)
                raise

            report_ptr.write("SPDXVersion: %s\n" %SPDXData["SPDXVersion"])
            report_ptr.write("DataLicense: %s\n" %SPDXData["DataLicense"])
            report_ptr.write("SPDXID: SPDXRef-DOCUMENT\n")
            report_ptr.write("DocumentName: %s\n" %packageData["DocumentName"])
            report_ptr.write("DocumentNamespace: %s\n" %packageData["DocumentNamespace"])
            report_ptr.write("Creator: Tool: %s\n" %SPDXData["Creator"])
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
                report_ptr.write("FileChecksum: SHA1: %s\n" %packageFiles[file]["fileSHA1"])
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

            report_ptr.write("Relationship: %s DESCRIBES %s\n" %("SPDXRef-DOCUMENT", packageData["SPDXID"] ))
            report_ptr.write("Relationship: %s DESCRIBED_BY  %s\n" %(packageData["SPDXID"], "SPDXRef-DOCUMENT" ))

            report_ptr.write("\n")

            for file in packageFiles:
                report_ptr.write("## ----------------------- Relationship -----------------------\n")
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
