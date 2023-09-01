'''
Copyright 2023 Flexera Software LLC
See LICENSE.TXT for full license text
SPDX-License-Identifier: MIT

Author : sgeary  
Created On : Fri Aug 18 2023
File : report_artifacts_json.py
'''
import logging, json
logger = logging.getLogger(__name__)

#--------------------------------------------------------------------------------#

def generate_json_report(reportData):
    logger.info("    Entering generate_json_report")

    reportFileNameBase = reportData["reportFileNameBase"]
    reportDetails = reportData["reportDetails"]

    jsonFile = reportFileNameBase + ".spdx.json"

    # Sine the data was gathered in the expected format just
    # write the data directly into the json file
    try:
        report_ptr = open(jsonFile,"w")
    except:
        print("Failed to open file %s:" %jsonFile)
        logger.error("Failed to open file %s:" %jsonFile)
        return {"errorMsg" : "Failed to open file %s:" %jsonFile}

    json.dump(reportDetails, report_ptr, indent=4)

    report_ptr.close() 

    logger.info("    Exiting generate_json_report")

    return jsonFile
