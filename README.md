# Revenera Code Insight SPDX Report

The `sca-codeinsight-reports-spdx` repository is a example report for Revenera's Code Insight product. This report allows a user to generate an SPDX report representing the software bill of material (SBOM) information, including components, licenses, copyrights, and security references. 

Both JSON and tag/value SPDX documents will be created

A custom inventory field **Package Supplier** can be used to force a package supplier value for a given SBOM entry.

Project level custom fields, **Application Name**, **Application Version** and **Application Publisher** can also be used for the creation of the overall SPDX document name to replace the project name and the **Application Publisher** entry will be assigned to the top level package's supplier field.

 **Supported SPDX Version Output - 2.3**

## Prerequisites

 **Code Insight Release Requirements**
  
|Repository Tag | Minimum Code Insight Release  |
|--|--|
|1.0.x |2021R2  |
|1.1.x |2021R3  |
|1.2.x |2021R4  |
|1.3.x |2022R1  |
|3.x.x |2023R2  |
|3.1.x |2023R3  |
|4.0.x |2023R3  |

**Repository Cloning**

This repository should be cloned directly into the **$CODEINSIGHT_INSTALLDIR/custom_report_scripts** directory. If no prior custom reports has been installed, this directory will need to be created prior to cloning.

**Python Requirements**

This repository requires the python requests module to interact with the Code Insight REST APIs.  To install this as well as the the modules it depends on the [requirements.txt](requirements.txt) file has been supplied and can be used as follows.

    pip install -r requirements.txt

**Offline Mode**
The sca-codeinsight-reports-spdx custom report can be used in offline mode, meaning the Code Insight server does not need to be running.

For Windows:
Open a command prompt at the location:
$CODEINSIGHT_INSTALLDIR/custom_report_scripts/sca-codeinsight-reports-spdx
Run the following command
python create_report.py -pid <projectID> -reportOpts "{\"includeChildProjects\": \"True\", \"includeNonRuntimeInventory\": \"False\", \"includeFileDetails\": \"True\", \"includeUnassociatedFiles\": \"False\", \"createOtherFilesPackage\": \"False\", \"includeCopyrightsData\": \"False\"}"

For Linux:
Open a terminal at the location:
$CODEINSIGHT_INSTALLDIR/custom_report_scripts/sca-codeinsight-reports-spdx
Run the following command:
python3 create_report.py -pid <projectID> -reportOpts '{"includeChildProjects":"True","includeNonRuntimeInventory":"False","includeFileDetails":"True","includeUnassociatedFiles":"False","createOtherFilesPackage":"False","includeCopyrightsData":"False"}'

Notes:
The -pid flag is mandatory.
The -reportOpts flag is optional. If omitted, all values will set to default.
Example: python3 create_report.py -pid <projectID>

Report Locations:
Recently Generated Reports:
$CODEINSIGHT_INSTALLDIR/custom_report_scripts/sca-codeinsight-reports-spdx/DBReports
Older Reports:
$CODEINSIGHT_INSTALLDIR/custom_report_scripts/sca-codeinsight-reports-spdx/DBReports/Backup

## Configuration and Report Registration

It is optional but recommended to have the Code Insight server up and running if you intend to trigger this report from the Code Insight UI under the reports tab.
For registration purposes the file **server_properties.json** should be created and located in the **$CODEINSIGHT_INSTALLDIR/custom_report_scripts/** directory.  This file contains a json with information required to register the report within Code Insight as shown  here:

>     {
>         "core.server.url": "http://localhost:8888" ,
>         "core.server.token" : "Admin authorization token from Code Insight"
>     }

The value for core.server.url is also used within [create_report.py](create_report.py) for any project or inventory based links back to the Code Insight server within a generated report.

If the common **server_properties.json** files is not used then the information the the following files will need to be updated:

[registration.py](registration.py)  -  Update the **baseURL** and **adminAuthToken** values. These settings allow the report itself to be registered on the Code Insight server.

[create_report.py](create_report.py)  -  Update the **baseURL** value. This URL is used for links within the reports.

Report option default values can also be specified in [registration.py](registration.py) within the reportOptions dictionaries.

### Registering the Report

Prior to being able to call the script directly from within Code Insight it must be registered. The [registration.py](registration.py) file can be used to directly register the report once the contents of this repository have been added to the custom_report_script folder at the base Code Insight installation directory.

To register this report:

	python registration.py -reg

To unregister this report:
	
	python registration.py -unreg

To update this report configuration:
	
	python registration.py -update


## Usage

This report is executed directly from within Revenera's Code Insight product. From the project reports tab of each Code Insight project it is possible to *generate* the **SPDX Report** via the Report Framework.

**Report Options**
- Including child projects (True/False) - Determine if child project data will be included or not.
- Include Non Runtime dependency items (True/False) - Should the report include data for dependencies that are not of a Runtime scope?
- Including file level details (True/False) - Determine if any file data will be included or not.
- Including files not associated with inventory items (True/False) - Should files not associated with inventory items be included in the report
- Including Copyrights data (True/False) - Determine if copyright data will be included or not.
- Create OtherFiles package to contain all files that are not associated to other inventory items.  If the above option is true and this is false all files will be linked to the top level package instead of the OtherFiles Package

The generated reports will utilize the following Project Custom Fields if available
- Application Name
- Application Version

The Code Insight Report Framework will provide the following to the report when initiated:

- Project ID
- Report ID
- Authorization Token
 

For this example report these three items are passed on to a batch or sh file which will in turn execute a python script. This script will then:

- Collect data for the report via REST API using the Project ID and Authorization Token
- Take this collected data and generate an SPDX document in both JSON and tag/value format.
- The JSON SPDX file will be marked as the *"viewable"* file
- A zip file will be created containing the both the JSON and tag/value artifacts which will be the *"downloadable"* file.
- Create a zip file with the viewable file and the downloadable file
- Upload this combined zip file to Code Insight via REST API
- Delete the report artifacts that were created as the script ran


## License

[MIT](LICENSE.TXT)


