'''
Copyright 2021 Flexera Software LLC
See LICENSE.TXT for full license text
SPDX-License-Identifier: MIT

Author : sgeary  
Created On : Tue Apr 27 2021
File : filetype_mappings.py
'''

fileTypeMappings = {}
fileTypeMappings[".c"] = "SOURCE"
fileTypeMappings[".cxx"] = "SOURCE"
fileTypeMappings[".cpp"] = "SOURCE"
fileTypeMappings[".py"] = "SOURCE"
fileTypeMappings[".sh"] = "SOURCE"
fileTypeMappings[".inc"] = "SOURCE"

fileTypeMappings[".tar"] = "BINARY"
fileTypeMappings[".zip"] = "BINARY"
fileTypeMappings[".gz"] = "BINARY"


fileTypeMappings[".md"] = "OTHER"
fileTypeMappings[".gitignore"] = "OTHER"
fileTypeMappings[".sample"] = "OTHER"

