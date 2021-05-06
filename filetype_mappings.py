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

fileTypeMappings[".h"] = "SOURCE"
fileTypeMappings[".c"] = "SOURCE"
fileTypeMappings[".cc"] = "SOURCE"
fileTypeMappings[".cs"] = "SOURCE"
fileTypeMappings[".cxx"] = "SOURCE"
fileTypeMappings[".cpp"] = "SOURCE"
fileTypeMappings[".py"] = "SOURCE"
fileTypeMappings[".sh"] = "SOURCE"
fileTypeMappings[".inc"] = "SOURCE"
fileTypeMappings[".rb"] = "SOURCE"
fileTypeMappings[".pl"] = "SOURCE"
fileTypeMappings[".html"] = "SOURCE"
fileTypeMappings[".css"] = "SOURCE"
fileTypeMappings[".less"] = "SOURCE"   # dynamic style sheet
fileTypeMappings[".scss"] = "SOURCE"   # Sassy CSS
fileTypeMappings[".go"] = "SOURCE"
fileTypeMappings[".java"] = "SOURCE"
fileTypeMappings[".js"] = "SOURCE"
fileTypeMappings[".jsp"] = "SOURCE"
fileTypeMappings[".swift"] = "SOURCE"
fileTypeMappings[".m"] = "SOURCE"
fileTypeMappings[".vb"] = "SOURCE"

fileTypeMappings[".o"] = "BINARY"
fileTypeMappings[".a"] = "BINARY"
fileTypeMappings[".so"] = "BINARY"
fileTypeMappings[".dll"] = "BINARY"
fileTypeMappings[".exe"] = "BINARY"


fileTypeMappings[".tar"] = "ARCHIVE"
fileTypeMappings[".tgz"] = "ARCHIVE"
fileTypeMappings[".zip"] = "ARCHIVE"
fileTypeMappings[".gz"] = "ARCHIVE"
fileTypeMappings[".jar"] = "ARCHIVE"
fileTypeMappings[".bz2"] = "ARCHIVE"
fileTypeMappings[".rpm"] = "ARCHIVE"

fileTypeMappings[".txt"] = "TEXT"

fileTypeMappings[".md"] = "OTHER"
fileTypeMappings[".gitignore"] = "OTHER"
fileTypeMappings[".sample"] = "OTHER"
fileTypeMappings[".xib"] = "OTHER"  # Interface builder file


