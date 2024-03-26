'''
Copyright 2021 Flexera Software LLC
See LICENSE.TXT for full license text
SPDX-License-Identifier: MIT

Author : sgeary  
Created On : Tue Apr 27 2021
File : report_artifacts.py
'''

import logging

import report_artifacts_json
import report_artifacts_tagvalue

logger = logging.getLogger(__name__)

DEBUG = False

#--------------------------------------------------------------------------------#
def create_report_artifacts(reportData):
    logger.info("Entering create_report_artifacts")

    # Dict to hold the complete list of reports
    reports = {}

    if DEBUG:
        reportData["reportFileNameBase"] = "testing_report"

    # Crete a report for each project within the hierarchy
    # and return a list of the files there were created.
    tagvalueFile = report_artifacts_tagvalue.generate_tagvalue_report(reportData)
    jsonFile = report_artifacts_json.generate_json_report(reportData)

    if DEBUG:
        import sys
        sys.exit()

    reports["viewable"] = jsonFile
    reports["allFormats"] = [jsonFile, tagvalueFile]

    logger.info("Exiting create_report_artifacts")
    
    return reports 

