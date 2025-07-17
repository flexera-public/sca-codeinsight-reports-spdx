'''
Copyright 2020 Flexera Software LLC
See LICENSE.TXT for full license text
SPDX-License-Identifier: MIT

Author : sgeary  
Created On : Wed Oct 21 2020
Modified By : sarthak
Modified On: Mon 07 2025
File : create_report.py
'''
import shutil
import sys, os, logging, argparse, json, re
from datetime import datetime

import _version
import report_data
import report_artifacts
import report_errors
import upload_reports
import report_archive


###################################################################################
# Test the version of python to make sure it's at least the version the script
# was tested on, otherwise there could be unexpected results
if sys.version_info < (3, 6):
    raise Exception("The current version of Python is less than 3.6 which is unsupported.\n Script created/tested against python version 3.6.8. ")
else:
    pass

propertiesFile = "../server_properties.json"  # Created by installer or manually
propertiesFile = logfileName = os.path.dirname(os.path.realpath(__file__)) + "/" +  propertiesFile
logfileName = os.path.dirname(os.path.realpath(__file__)) + "/_spdx_report.log"

###################################################################################
#  Set up logging handler to allow for different levels of logging to be capture
logging.basicConfig(format='%(asctime)s,%(msecs)-3d  %(levelname)-8s [%(filename)-30s:%(lineno)-4d]  %(message)s', datefmt='%Y-%m-%d:%H:%M:%S', filename=logfileName, filemode='w',level=logging.DEBUG)
logger = logging.getLogger(__name__)
logging.getLogger("urllib3").setLevel(logging.WARNING)  # Disable logging for requests module

####################################################################################
# Create command line argument options
parser = argparse.ArgumentParser(
    description="""Usage Examples:

Windows:
  python create_report.py -pid <projectID> -reportOpts "{\\"includeChildProjects\\": \\"True\\", \\"includeNonRuntimeInventory\\": \\"False\\", \\"includeFileDetails\\": \\"True\\", \\"includeUnassociatedFiles\\": \\"False\\", \\"createOtherFilesPackage\\": \\"False\\", \\"includeCopyrightsData\\": \\"False\\"}"   #####      

Linux:
  python3 create_report.py -pid <projectID> -reportOpts '{"includeChildProjects":"True","includeNonRuntimeInventory":"False","includeFileDetails":"True","includeUnassociatedFiles":"False","createOtherFilesPackage":"False","includeCopyrightsData":"False"}'   #####      

Note:
  - The -pid flag is mandatory.
  - The -reportOpts flag is optional. If omitted, all values will default to "includeChildProjects":"True","includeNonRuntimeInventory":"False","includeFileDetails":"True","includeUnassociatedFiles":"False","createOtherFilesPackage":"False","includeCopyrightsData":"False".
  Example: python3 create_report.py -pid <projectID>
"""
)
parser.add_argument('-pid', "--projectID", help="Project ID")
parser.add_argument("-rid", "--reportID", help="Report ID(Optional)")
parser.add_argument("-authToken", "--authToken", help="Code Insight Authorization Token(Optional)")
parser.add_argument("-baseURL", "--baseURL", help="Code Insight Core Server Protocol/Domain Name/Port(Optional).  i.e. http://localhost:8888 or https://sca.codeinsight.com:8443")
parser.add_argument("-reportOpts", "--reportOptions", help="Options for report content(Optional)")

#----------------------------------------------------------------------#
def main():

	reportName = "SPDX Report"
	reportVersion = _version.__version__

	logger.info("Creating %s - %s" %(reportName, reportVersion))
	print("Creating %s - %s" %(reportName, reportVersion))
	print("    Logfile: %s" %(logfileName))

    #####################################################################################################

	if os.path.exists(propertiesFile):
		try:
			file_ptr = open(propertiesFile, "r")
			configData = json.load(file_ptr)
			baseURL = configData["core.server.url"]
			file_ptr.close()
			logger.info("Using baseURL from properties file: %s" %propertiesFile)
		except:
			logger.error("Unable to open properties file: %s" %propertiesFile)

		# Is there a self signed certificate to consider?
		try:
			certificatePath = configData["core.server.certificate"]
			os.environ["REQUESTS_CA_BUNDLE"] = certificatePath
			os.environ["SSL_CERT_FILE"] = certificatePath
			logger.info("Self signed certificate added to env")
		except:
			logger.info("No self signed certificate in properties file")

	else:
		baseURL = "http://localhost:8888"   # Required if the core.server.properties files is not used
		logger.info("Using baseURL from create_report.py")

	# See what if any arguments were provided
	args = parser.parse_args()
	projectID = (
        args.projectID
        if args.projectID is not None
        else sys.exit("Project ID -pid flag is mandatory")
    )
	reportID = (
        args.reportID
        if args.reportID is not None
        else print("Ignoring as -rid flag is not needed")
    )
	authToken = (
        args.authToken
        if args.authToken is not None
        else print("Ignoring as -authToken flag is not needed")
    )
	if args.reportOptions is not None:
		reportOptions = args.reportOptions
		if sys.platform.startswith("linux"):
			logger.info(f"Before Double Quote replacement: {reportOptions}")
			if '""' in reportOptions:
				reportOptions = reportOptions.replace('""', '"')[1:-1]
	else:
		reportOptions = '{"includeChildProjects":"True","includeNonRuntimeInventory":"False","includeFileDetails":"True","includeUnassociatedFiles":"False","createOtherFilesPackage":"False","includeCopyrightsData":"False"}'
		if sys.platform.startswith("linux"):
			reportOptions = '{"includeChildProjects":"True","includeNonRuntimeInventory":"False","includeFileDetails":"True","includeUnassociatedFiles":"False","createOtherFilesPackage":"False","includeCopyrightsData":"False"}'
	logger.info(f"Using default report options: {reportOptions}")

	fileNameTimeStamp = datetime.now().strftime("%Y%m%d-%H%M%S")
	reportTimeStamp = datetime.strptime(fileNameTimeStamp, "%Y%m%d-%H%M%S").strftime("%B %d, %Y at %H:%M:%S")
	spdxTimeStamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
	reportOptions = json.loads(reportOptions)
	reportOptions = verifyOptions(reportOptions) 

	logger.debug("Custom Report Provided Arguments:")	
	logger.debug("    projectID:  %s" %projectID)	
	logger.debug("    reportID:   %s" %reportID)	
	logger.debug("    baseURL:  %s" %baseURL)	
	logger.debug("    reportOptions:  %s" %reportOptions)

	reportData = {}
	reportData["projectID"] = projectID
	reportData["reportName"] = reportName
	reportData["reportVersion"] = reportVersion
	reportData["reportOptions"] = reportOptions
	reportData["releaseVersion"] = "N/A"
	reportData["fileNameTimeStamp"] = fileNameTimeStamp
	reportData["reportTimeStamp"] = reportTimeStamp
	reportData["spdxTimeStamp"] = spdxTimeStamp

	# Collect the data for the report
	
	if "errorMsg" in reportOptions.keys():

		reportFileNameBase = reportName.replace(" ", "_") + "-Creation_Error-" + fileNameTimeStamp

		reportData["errorMsg"] = reportOptions["errorMsg"]
		reportData["reportName"] = reportName
		reportData["reportFileNameBase"] = reportFileNameBase

		reports = report_errors.create_error_report(reportData)
		print("    *** ERROR  ***  Error found validating report options")
	else:
		print("    Collect data for %s" %reportName)
		reportData = report_data.gather_data_for_report(projectID, reportData)
		print("    Report data has been collected")

		projectName = reportData["topLevelProjectName"]
		projectNameForFile = re.sub(r"[^a-zA-Z0-9]+", '-', projectName )  # Remove special characters from project name for artifacts

		# Are there child projects involved?  If so have the artifact file names reflect this fact
		if len(reportData["projectList"])==1:
			reportFileNameBase = projectNameForFile + "-" + str(projectID) + "-" + reportName.replace(" ", "_") + "-" + fileNameTimeStamp
		else:
			reportFileNameBase = projectNameForFile + "-with-children-" + str(projectID) + "-" + reportName.replace(" ", "_") + "-" + fileNameTimeStamp

		reportData["reportFileNameBase"] = reportFileNameBase

		if "errorMsg" in reportData.keys():
			reports = report_errors.create_error_report(reportData)
			print("    Error report artifacts have been created")
		else:
			reports = report_artifacts.create_report_artifacts(reportData)
			print("    Report artifacts have been created")
			for report in reports["allFormats"]:
				print("       - %s"%report)

	print("    Create report archive for upload")
	uploadZipfile = report_archive.create_report_zipfile(reports, reportFileNameBase)
	print("    Upload zip file creation completed")
	if authToken is not None:
		upload_reports.upload_project_report_data(baseURL, projectID, reportID, authToken, uploadZipfile)
		print("    Report uploaded to Code Insight")

		#########################################################
		# Remove the file since it has been uploaded to Code Insight
		try:
			os.remove(uploadZipfile)
		except OSError:
			logger.error("Error removing %s" %uploadZipfile)
			print("Error removing %s" %uploadZipfile)
	else:
        # Get the current path and directory
		current_path = os.path.abspath(__file__)
		current_directory = os.path.dirname(current_path)
		logger.info(f"Current directory: {current_directory}")

        # Define the DBReports directory path
		quickDBReports_dir = os.path.join(current_directory, "reportsBackup")

        # Check if quickDBReports directory exists, if not create it
		if not os.path.exists(quickDBReports_dir):
			os.makedirs(quickDBReports_dir)
			logger.info(f"Created directory: {quickDBReports_dir}")

        # Check if there are any previous reports in quickDBReports directory
		previous_reports = [
            f
            for f in os.listdir(quickDBReports_dir)
            if os.path.isfile(os.path.join(quickDBReports_dir, f))
        ]
		if previous_reports:
            # Create a Backup directory inside quickDBReports
			backup_dir = os.path.join(quickDBReports_dir, "Backup")
			if not os.path.exists(backup_dir):
				os.makedirs(backup_dir)
				logger.info(f"Created backup directory: {backup_dir}")

            # Create a timestamped backup directory inside Backup
			timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
			timestamped_backup_dir = os.path.join(backup_dir, f"Backup_{timestamp}")
			os.makedirs(timestamped_backup_dir)
			logger.info(
                f"Created timestamped backup directory: {timestamped_backup_dir}"
            )

            # Move all previous reports to the timestamped backup directory
			for report in previous_reports:
				shutil.move(
                    os.path.join(quickDBReports_dir, report),
                    os.path.join(timestamped_backup_dir, report),
                )
				logger.info(f"Moved report {report} to backup directory")

        # Move new reports to the quickDBReports directory
		# Only move the uploadZipfile since that's the actual created file
		if os.path.exists(uploadZipfile):
			shutil.move(uploadZipfile, quickDBReports_dir)
			logger.info(f"Moved new report {uploadZipfile} to {quickDBReports_dir}")
		else:
			logger.error(f"Report file {uploadZipfile} does not exist")
			print(f"Error: Report file {uploadZipfile} does not exist")
		
		# Check if the base zip file exists before trying to move it
		base_zip_file = reportFileNameBase + ".zip"
		if os.path.exists(base_zip_file):
			shutil.move(base_zip_file, quickDBReports_dir)
			logger.info(f"Moved base report {base_zip_file} to {quickDBReports_dir}")
		else:
			logger.warning(f"Base zip file {base_zip_file} does not exist, skipping move")

	logger.info("Completed creating %s" %reportName)
	print("Completed creating %s" %reportName)


#----------------------------------------------------------------------# 
def verifyOptions(reportOptions):
	'''
	Expected Options for report:
		includeChildProjects - True/False
	'''
	reportOptions["errorMsg"] = []
	trueOptions = ["true", "t", "yes", "y"]
	falseOptions = ["false", "f", "no", "n"]

	includeChildProjects = reportOptions["includeChildProjects"]
	includeNonRuntimeInventory = reportOptions["includeNonRuntimeInventory"]
	includeFileDetails = reportOptions["includeFileDetails"]
	includeUnassociatedFiles = reportOptions["includeUnassociatedFiles"]
	createOtherFilesPackage = reportOptions["createOtherFilesPackage"]
	includeCopyrightsData = reportOptions["includeCopyrightsData"]

	if includeChildProjects.lower() in trueOptions:
		reportOptions["includeChildProjects"] = True
	elif includeChildProjects.lower() in falseOptions:
		reportOptions["includeChildProjects"] = False
	else:
		reportOptions["errorMsg"].append("Invalid option for including child projects: <b>%s</b>.  Valid options are <b>True/False</b>" %includeChildProjects)


	if includeNonRuntimeInventory.lower() in trueOptions:
		reportOptions["includeNonRuntimeInventory"] = True
	elif includeNonRuntimeInventory.lower() in falseOptions:
		reportOptions["includeNonRuntimeInventory"] = False
	else:
		reportOptions["errorMsg"].append("Invalid option for including Nonruntime inventory items: <b>%s</b>.  Valid options are <b>True/False</b>" %includeNonRuntimeInventory)


	if includeFileDetails.lower() in trueOptions:
		reportOptions["includeFileDetails"] = True
	elif includeFileDetails.lower() in falseOptions:
		reportOptions["includeFileDetails"] = False
	else:
		reportOptions["errorMsg"].append("Invalid option for including file details files: <b>%s</b>.  Valid options are <b>True/False</b>" %includeFileDetails)

	if includeUnassociatedFiles.lower() in trueOptions:
		reportOptions["includeUnassociatedFiles"] = True
	elif includeUnassociatedFiles.lower() in falseOptions or includeFileDetails.lower() in falseOptions:
		reportOptions["includeUnassociatedFiles"] = False
	else:
		reportOptions["errorMsg"].append("Invalid option for including unassocated files: <b>%s</b>.  Valid options are <b>True/False</b>" %includeUnassociatedFiles)

	if createOtherFilesPackage.lower() in trueOptions:
		reportOptions["createOtherFilesPackage"] = True
	elif createOtherFilesPackage.lower() in falseOptions or includeUnassociatedFiles.lower() in falseOptions:
		reportOptions["createOtherFilesPackage"] = False
	else:
		reportOptions["errorMsg"].append("Invalid option for where to map unassocated files: <b>%s</b>.  Valid options are <b>True/False</b>" %createOtherFilesPackage)

	if includeCopyrightsData.lower() in trueOptions:
		reportOptions["includeCopyrightsData"] = True
	elif includeCopyrightsData.lower() in falseOptions:
		reportOptions["includeCopyrightsData"] = False
	else:
		reportOptions["errorMsg"].append("Invalid option for including copyright projects: <b>%s</b>.  Valid options are <b>True/False</b>" %includeCopyrightsData)

	if not reportOptions["errorMsg"]:
		reportOptions.pop('errorMsg', None)

	return reportOptions

#----------------------------------------------------------------------#    
if __name__ == "__main__":
    main()  