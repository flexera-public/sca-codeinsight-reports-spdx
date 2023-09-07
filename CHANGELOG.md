# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [unreleased]

## [3.0.1] - 2023-09-07
### Fixed
- Worked around potential issue with mismatch between file data response and files in inventory
- Added logic to set non inventory file option to False if files are being ignored

## [3.0.0] - 2023-09-01
### Changed
- Changed submodule to https://github.com/flexera-public/sca-codeinsight-reports-common
- Used common functions from common module
- Consolidated all children projects into single report
- Unified requirement with other reports (Python v3.6.8)
### Added
- Support for JSON output
- Added option to ignore all file level data
- Code Insight Vesion into report
- Validated with SPDX Command Line Tools using the Spdx-Java-Library v1.1.7
### Removed
- Removed tag/value format

## [2.2.1] - 2023-06-27
### Fixed
- Main report name to reflect primary project
- Update APIs to get all scanned file in a single call (performance improvement)
- Resolved lack of parentInventoryID issue with OtherFiles pacakge
### Added
- Improved logging for main output to provide more context for current report location

## [2.2.0] - 2023-03-20
### Fixed
- Updated registration script to include registraion_config.json
- Fix dependency relationship for SPDX ID vs package name

## [2.1.0] - 2023-03-19
### Fixed
- Handle failure in purl creation gracefully (custom components will probably be skipped)
- Support file with evidence but no copyright or license
- Encoding fix for copyrights
- Improved debugging
### Added
- LicenseRef values
- Add package dependency support

## [2.0.3] - 2022-10-03
### Fixed
- File level license fixes for Public Domain

## [2.0.2] - 2022-09-09
### Fixed
- support packages without associated files

## [2.0.1] - 2022-09-01
### Fixed
- Fix declared vs concluded license determination
- Support non SPDX licenses with LicenseRef
- File level licese updates
- Special character replacement to avoid warnings
- NPM and pypi purl updates

## [1.3.2] - 2022-07-18
### Fixed
- Misc purl value fixes
- purl and package homepage for non associated files
- SHA1 handling for imported projects

## [1.3.1] - 2022-06-15
### Fixed
- SHA1 fix

## [1.3.0] - 2022-06-14
### Added
- Purl values
- Application name from project fields

## [1.2.7] - 2022-05-23
### Added
- Registration updates

## [1.2.6] - 2022-03-05
### Added
- Option to include unassociated files

## [1.2.5] - 2022-02-10
### Added
- Support for self signed certificates

## [1.2.4] - 2021-12-15
### Changed
- Updated requirements

## [1.2.3] - 2021-11-30
### Fixed
- Use just compenant name for package
### Added
- Added component version as separate tag
### Changed
- Migrated to flexera-public org

## [1.2.2] - 2021-11-16
### Fixed
- Fixed support for server_properties.json file

## [1.2.1] - 2021-11-09
### Added
- Support for report installer
- Logging cleanup
- Misc cleanup

## [1.1.2] - 2021-08-25
### Added
- Create a single SPDX report for each project vs each inventory item.

## [1.1.1] - 2021-07-27
### Added
- Updates for 2021R3 release
- Project Hierarchy Option

## [1.0.1] - 2021-05-18
### Added
- Initial public release of SPDX Report