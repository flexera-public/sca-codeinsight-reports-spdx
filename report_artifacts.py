'''
Copyright 2021 Flexera Software LLC
See LICENSE.TXT for full license text
SPDX-License-Identifier: MIT

Author : sgeary  
Created On : Tue Apr 27 2021
File : report_artifacts.py
'''

import logging

import report_artifacts_tag_value
import report_artifacts_summary

logger = logging.getLogger(__name__)

#--------------------------------------------------------------------------------#
def create_report_artifacts(reportData):
    logger.info("Entering create_report_artifacts")

    # Dict to hold the complete list of reports
    reports = {}

    # Crete a report for each project within the hierarchy
    # and return a list of the files there were created.
    spdxTagValueFiles = report_artifacts_tag_value.generate_tag_value_spdx_report(reportData)

    if len(reportData["projectList"]) == 1:
        reports["viewable"] = spdxTagValueFiles[0]
        reports["allFormats"] = spdxTagValueFiles
    else:
        sumamryFile = report_artifacts_summary.generate_spdx_summary_report(reportData, spdxTagValueFiles)
        reports["viewable"] = sumamryFile
        reports["allFormats"] = spdxTagValueFiles
        reports["allFormats"].append(sumamryFile)

    logger.info("Exiting create_report_artifacts")
    
    return reports 

