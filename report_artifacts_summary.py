'''
Copyright 2021 Flexera Software LLC
See LICENSE.TXT for full license text
SPDX-License-Identifier: MIT

Author : sgeary  
Created On : Tue Nov 09 2021
File : report_artifacts_summary.py
'''

import logging
logger = logging.getLogger(__name__)

#--------------------------------------------------------------------------------#

def generate_spdx_summary_report(reportData, spdxTextFiles):
    logger.info("Entering generate_spdx_summary_report")

    reportFileNameBase = reportData["reportFileNameBase"]

    summaryTextFile = reportFileNameBase + ".txt"
    logger.debug("    Creating summaryTextFile: %s" %summaryTextFile)

    try:
        report_ptr = open(summaryTextFile,"w")
    except:
        logger.error("Failed to open summaryTextFile %s:" %summaryTextFile)
        raise

    report_ptr.write("An SPDX report has been generated for each project within the specified project hierachy.\n")
    report_ptr.write("\n")
    report_ptr.write("The following reports are included within the downloadable zip file:\n")
    report_ptr.write("\n")

    for spdx in spdxTextFiles:
        report_ptr.write("\t -  %s\n" %(spdx ))

    report_ptr.close() 
    logger.info("    Exiting generate_spdx_summary_report")

    return summaryTextFile