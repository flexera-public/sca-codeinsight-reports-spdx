'''
Copyright 2021 Flexera Software LLC
See LICENSE.TXT for full license text
SPDX-License-Identifier: MIT

Author : sgeary  
Created On : Tue Apr 27 2021
File : filetype_mappings.py
'''

fileTypeMappings = {}

fileTypeMappings[".spdx"] = "SPDX"

fileTypeMappings[".md"] = "DOCUMENTATION"

fileTypeMappings[".c"] = "SOURCE"
fileTypeMappings[".cxx"] = "SOURCE"
fileTypeMappings[".cpp"] = "SOURCE"
fileTypeMappings[".py"] = "SOURCE"
fileTypeMappings[".sh"] = "SOURCE"
fileTypeMappings[".inc"] = "SOURCE"
fileTypeMappings[".rb"] = "SOURCE"
fileTypeMappings[".pl"] = "SOURCE"
fileTypeMappings[".html"] = "SOURCE"
fileTypeMappings[".css"] = "SOURCE"
fileTypeMappings[".go"] = "SOURCE"

fileTypeMappings[".o"] = "BINARY"
fileTypeMappings[".a"] = "BINARY"
fileTypeMappings[".so"] = "BINARY"
fileTypeMappings[".dll"] = "BINARY"


fileTypeMappings[".tar"] = "ARCHIVE"
fileTypeMappings[".zip"] = "ARCHIVE"
fileTypeMappings[".gz"] = "ARCHIVE"
fileTypeMappings[".jar"] = "ARCHIVE"
fileTypeMappings[".bz2"] = "ARCHIVE"

fileTypeMappings[".jpg"] = "IMAGE"
fileTypeMappings[".gif"] = "IMAGE"

fileTypeMappings[".mp3"] = "AUDIO"

fileTypeMappings[".mp4"] = "VIDEO"


fileTypeMappings[".md"] = "OTHER"
fileTypeMappings[".gitignore"] = "OTHER"
fileTypeMappings[".sample"] = "OTHER"

