#! /usr/bin/python
license = (  # @ReservedAssignment
'''_opy_Copyright 2014, 2015, 2016, 2017 Jacques de Hooge, GEATEC engineering, www.geatec.com

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.'''
)

import re
import os
import sys
import errno
import keyword
import importlib  # @UnusedImport
import random
import codecs
import shutil
import six
import copy

PROGRAM_NAME = 'opy'
DEFAULT_ENCODING = 'utf-8'
from . _version import __version__  
from . opy_config import OpyConfig 
from . import opy_parser            

mainCount=0
isPython2=six.PY2
if isPython2 : 
    import __builtin__ # @UnresolvedImport
else:
    import builtins   

def __fetchStandardExclusions():
    filePath = os.path.join( os.path.dirname(__file__),
                             'standard_exclusions.txt' )
    with codecs.open( filePath, 'r', 'utf-8' ) as f:
        lines = f.read().split( '\n' )
    cleanLines = [ l.strip() for l in lines if len( l.strip() ) > 0 ]    
    cleanList = list( set( cleanLines ) )
    return cleanList
standardExclusions = __fetchStandardExclusions()

class OpyError( Exception ): pass
       
class OpyResults:
    def __init__(self):
        self.obfuscatedFiles = None
        self.obfuscatedIds   = None   
        self.obfuscatedMods  = None    
        self.maskedIds       = None
        self.clearTextMods   = None
        self.clearTextPublic = None    
        self.clearTextIds    = None           

class RunOptions:
    def __init__( self ) :
        self.printHelp           = False
        self.sourceRootDirectory = None
        self.targetRootDirectory = None
        self.configFilePath      = None # None == default, False == use configSettings
        self.configSettings      = None
   
def obfuscate( sourceRootDirectory = None
             , targetRootDirectory = None
             , configFilePath      = None
             , configSettings      = None
             ):    
    runOptions = RunOptions()
    runOptions.printHelp           = False
    runOptions.sourceRootDirectory = sourceRootDirectory
    runOptions.targetRootDirectory = targetRootDirectory
    runOptions.configSettings      = configSettings
    runOptions.configFilePath = ( 
        configFilePath if configSettings is None else False )        
    return __obfuscate( runOptions )
    
def analyze( sourceRootDirectory = None
           , configSettings      = OpyConfig()
           , fileList            = []             
           ):    
    runOptions = RunOptions()
    runOptions.printHelp           = False
    runOptions.sourceRootDirectory = sourceRootDirectory
    runOptions.targetRootDirectory = None
    runOptions.configFilePath      = False    
    runOptions.configSettings = copy.copy( configSettings )    
    if fileList and len(fileList) > 0:
        runOptions.configSettings.subset_files = fileList
    return __analyze( runOptions )

def printHelp():    
    runOptions = RunOptions()
    runOptions.printHelp = True
    __main( runOptions )   

def __obfuscate( runOptions=None ):    
    # first analyze, then auto configure OR error out if a problem is detected
    isStandardExc = runOptions.configSettings.apply_standard_exclusions
    isPreserve    = runOptions.configSettings.preserve_unresolved_imports    
    analysis      = __analyze( runOptions )
    obMods        = analysis.obfuscatedMods    
    # ignore obfuscated mods which are included in the project            
    if len( obMods ) > 0:
        # TODO: Handle imports of child mods/packages... 
        obFiles  = analysis.obfuscatedFiles.keys()        
        projMods = [opy_parser.rootFileName(f) for f in obFiles]
        obMods   = [m for m in obMods if m not in projMods]
    # apply standard exclusions
    if len( obMods ) > 0 and isStandardExc:                
        stdEx  = [m for m in obMods if m in standardExclusions]
        obMods = [m for m in obMods if m not in stdEx]
        if len( stdEx ) > 0: 
            print( "Applying standard exclusions...\n" )        
            try:    runOptions.configSettings.external_modules.extend( stdEx )
            except: runOptions.configSettings.external_modules = stdEx
    # handle unresolved imports
    if len( obMods ) > 0:                                
        if isPreserve:
            for m in obMods: print( "WARNING - unresolved import: %s" % (m,) )
            print("")
            try:    runOptions.configSettings.external_modules.extend( obMods )
            except: runOptions.configSettings.external_modules = obMods
        else:                    
            raise OpyError( "Unresolved import(s): %s" % (",".join(obMods),) ) 
    print("")
    # run the main process     
    return __main( runOptions )

def __analyze( runOptions ):
    # allow for the same runOptions to work for both analyze and obfuscate                  
    savedDryRun = runOptions.configSettings.dry_run    
    runOptions.configSettings.dry_run = True
    results = __main( runOptions )    
    runOptions.configSettings.dry_run = savedDryRun
    return results

def __main( runOptions ):    
    global obfuscatedFileDict, obfuscatedWordDict, obfuscatedModImports    
    global skippedPublicSet, skipWordList
    
    global mainCount    
    global stringIndex, commentIndex, stringNr
    
    if mainCount==0:
        print ('{} (TM) Configurable Multi Module Python Obfuscator Version {}'.format (PROGRAM_NAME.capitalize (), __version__))
        print ('Copyright (C) Geatec Engineering. License: Apache 2.0 at  http://www.apache.org/licenses/LICENSE-2.0\n')
    mainCount+=1

    if runOptions:
        if runOptions.configSettings.dry_run:
            print( ">>> ANALYZING: " )
            print( "source directory: %s" % (runOptions.sourceRootDirectory,) )
            print( "configuration: \n%s"  % (runOptions.configSettings,) )                
        else :
            print( ">>> OBFUSCATING: " )
            print( "source directory: %s" % (runOptions.sourceRootDirectory,) )
            print( "target directory: %s" % (runOptions.targetRootDirectory,) )
            print( "config file path: %s" % (runOptions.configFilePath,) )
            print( "configuration: \n%s"  % (runOptions.configSettings,) )    

    opy_parser._reset()

    random.seed ()

    charBase = 2048         # Choose high to prevent string recoding from generating special chars like ', " and \
    stringNr = charBase
    charModulus = 7

    # =========== Utilities   

    def createFilePath (filePath, open = False):  # @ReservedAssignment
        try:
            os.makedirs (filePath.rsplit ('/', 1) [0])
        except OSError as exception:
            if exception.errno != errno.EEXIST:
                raise
                
        if open:
            return codecs.open (filePath, encoding = DEFAULT_ENCODING, mode = 'w')
            
    def getObfuscatedName (obfuscationIndex, name):
        return '{0}{1}{2}'.format (
            '__' if name.startswith ('__') else '_' if name.startswith ('_') else 'l',
            bin (obfuscationIndex) [2:] .replace ('0', 'l'),
            obfuscatedNameTail
        )
                    
    def scramble (stringLiteral):
        global stringNr
        
        if isPython2:
            recodedStringLiteral = unicode () .join ([unichr (charBase + ord (char) + (charIndex + stringNr) % charModulus) for charIndex, char in enumerate (stringLiteral)]) # @UndefinedVariable
            stringKey = unichr (stringNr) # @UndefinedVariable
        else:
            recodedStringLiteral = str () .join ([chr (charBase + ord (char) + (charIndex + stringNr) % charModulus) for charIndex, char in enumerate (stringLiteral)])
            stringKey = chr (stringNr)
            
        rotationDistance = stringNr % len (stringLiteral)
        rotatedStringLiteral = recodedStringLiteral [:-rotationDistance] + recodedStringLiteral [-rotationDistance:]
        keyedStringLiteral = rotatedStringLiteral + stringKey
        
        stringNr += 1
        return 'u"' + keyedStringLiteral + '"'      
        
    def getUnScrambler (stringBase):  # @UnusedVariable
        return '''
from sys import version_info as __opyVerInfo

isPython2{0} = __opyVerInfo[0] == 2
charBase{0} = {1}
charModulus{0} = {2}

def unScramble{0} (keyedStringLiteral):
    global stringNr{0}
    
    stringNr = ord (keyedStringLiteral [-1])
    rotatedStringLiteral = keyedStringLiteral [:-1]
    
    rotationDistance = stringNr % len (rotatedStringLiteral)
    recodedStringLiteral = rotatedStringLiteral [:rotationDistance] + rotatedStringLiteral [rotationDistance:]
        
    if isPython2{0}:
        stringLiteral = unicode () .join ([unichr (ord (char) - charBase{0} - (charIndex + stringNr) % charModulus{0}) for charIndex, char in enumerate (recodedStringLiteral)])
    else:
        stringLiteral = str () .join ([chr (ord (char) - charBase{0} - (charIndex + stringNr) % charModulus{0}) for charIndex, char in enumerate (recodedStringLiteral)])
        
    return eval (stringLiteral)
    '''.format (plainMarker, charBase, charModulus) 
            
    def printHelpAndExit (errorLevel):
        print (r'''
===============================================================================
{0} will obfuscate your extensive, real world, multi module Python source code for free!
And YOU choose per project what to obfuscate and what not, by editting the config file.

- BACKUP YOUR CODE AND VALUABLE DATA TO AN OFF-LINE MEDIUM FIRST TO PREVENT ACCIDENTAL LOSS OF WORK!!!
Then copy the default config file to the source top directory <topdir> and run {0} from there.
It will generate an obfuscation directory <topdir>/../<topdir>_{1}

- At first some identifiers may be obfuscated that shouldn't be, e.g. some of those imported from external modules.
Adapt your config file to avoid this, e.g. by adding external module names that will be recursively scanned for identifiers.
You may also exclude certain words or files in your project from obfuscation explicitly.

- Source directory, obfuscation directory and config file path can also be supplied as command line parameters.
The config file path should be something like C:/config_files/opy.cnf, so including the file name and extension.
opy [<source directory> [<target directory> [<config file path>]]]

- Comments and string literals can be marked as plain, bypassing obfuscation
Be sure to take a look at the comments in the config file opy_config.txt to discover all features.

Known limitations:

- A comment after a string literal should be preceded by whitespace
- A ' or " inside a string literal should be escaped with \ rather then doubled
- If the pep8_comments option is False (the default), a {2} in a string literal can only be used at the start, so use 'p''{2}''r' rather than 'p{2}r'
- If the pep8_comments option is set to True, however, only a <blank><blank>{2}<blank> cannot be used in the middle or at the end of a string literal
- Obfuscation of string literals is unsuitable for sensitive information since it can be trivially broken
- No renaming backdoor support for methods starting with __ (non-overridable methods, also known as private methods)

Licence:
{3}
===============================================================================

        '''.format (PROGRAM_NAME.capitalize (), PROGRAM_NAME, r'#', license))
        if errorLevel is not None: exit (errorLevel)
        
    # ============ Assign directories ============

    if runOptions:
        # Use library settings 
        if runOptions.printHelp: printHelpAndExit(None)                   
                    
        if runOptions.sourceRootDirectory is not None:                    
            sourceRootDirectory = runOptions.sourceRootDirectory.replace ('\\', '/')
        else:
            sourceRootDirectory = os.getcwd () .replace ('\\', '/')

        if runOptions.targetRootDirectory is not None:
            targetRootDirectory = runOptions.targetRootDirectory.replace ('\\', '/')
        else:
            targetRootDirectory = '{0}/{1}_{2}'.format (* (sourceRootDirectory.rsplit ('/', 1) + [PROGRAM_NAME]))

        if runOptions.configFilePath==False :
            configFilePath = ""
        elif runOptions.configFilePath is not None:
            configFilePath = runOptions.configFilePath.replace ('\\', '/')
        else:
            configFilePath = '{0}/{1}_config.txt'.format (sourceRootDirectory, PROGRAM_NAME)    
    else:
        # Use command line arguments
        if len (sys.argv) > 1:
            for switch in '?', '-h', '--help':
                if switch in sys.argv [1]:
                    printHelpAndExit (0)
            sourceRootDirectory = sys.argv [1] .replace ('\\', '/')
        else:
            sourceRootDirectory = os.getcwd () .replace ('\\', '/')

        if len (sys.argv) > 2:
            targetRootDirectory = sys.argv [2] .replace ('\\', '/')
        else:
            targetRootDirectory = '{0}/{1}_{2}'.format (* (sourceRootDirectory.rsplit ('/', 1) + [PROGRAM_NAME]))

        if len (sys.argv) > 3:
            configFilePath = sys.argv [3] .replace ('\\', '/')
        else:
            configFilePath = '{0}/{1}_config.txt'.format (sourceRootDirectory, PROGRAM_NAME)
            
    # =========== Read config file

    global obfuscate_strings, ascii_strings, obfuscated_name_tail
    global plain_marker, pep8_comments, source_extensions, skip_extensions
    global skip_path_fragments, external_modules, mask_external_modules
    global skip_public, plain_files, plain_names, dry_run, prepped_only
    global subset_files

    if configFilePath=="":
        configFile = runOptions.configSettings.toVirtualFile()
    else :        
        try:
            configFile = open (configFilePath)
        except Exception as exception:
            print (exception)
            printHelpAndExit (1)
        
    exec (configFile.read (), globals())
    configFile.close ()
    
    def getConfig (parameter, default):
        try:
            return eval (parameter)
        except:
            return default
    
    obfuscateStrings = getConfig ('obfuscate_strings', False)
    asciiStrings = getConfig ('ascii_strings', False)
    obfuscatedNameTail = getConfig ('obfuscated_name_tail', '_{}_')
    plainMarker = getConfig ('plain_marker', '_{}_'.format (PROGRAM_NAME))
    pep8Comments = getConfig ('pep8_comments', True)
    sourceFileNameExtensionList = getConfig ('source_extensions.split ()', ['py', 'pyx'])
    skipFileNameExtensionList = getConfig ('skip_extensions.split ()', ['pyc'])
    skipPathFragmentList = getConfig ('skip_path_fragments.split ()', [])
    externalModuleNameList = getConfig ('external_modules.split ()', [])
    maskExternalModules = getConfig ('mask_external_modules', False)
    skipPublicIdentifiers = getConfig ('skip_public', False)
    plainFileRelPathList = getConfig ('plain_files.split ()', [])
    extraPlainWordList = getConfig ('plain_names.split ()', [])
    dryRun = getConfig ('dry_run', False)
    preppedOnly = getConfig ('prepped_only', False)
    subsetFilesList = getConfig ('subset_files.split ()', [])

    #TODO: Handle spaces between key/colon/value, e.g. 'key : value'     
    replacementModulesDict = {}
    replacementModulesPairList = getConfig ('replacement_modules.split ()', [])
    for pair in replacementModulesPairList:
        pairParts = pair.split(":") 
        try: replacementModulesDict[ pairParts[0].strip() ]= pairParts[1].strip()
        except: continue        
        
    # ============ Gather source file names

    rawSourceFilePathList = [
        '{0}/{1}'.format (directory.replace ('\\', '/'), fileName)
        for directory, subDirectories, fileNames in os.walk (sourceRootDirectory)
        for fileName in fileNames
    ]
    
    def hasSkipPathFragment (sourceFilePath):
        for skipPathFragment in skipPathFragmentList:
            if skipPathFragment in sourceFilePath:
                return True
        return False
    
    sourceFilePathList = [sourceFilePath for sourceFilePath in rawSourceFilePathList if not hasSkipPathFragment (sourceFilePath)]

    if len(subsetFilesList) > 0 :        
        def inSubsetFilesList( sourceFilePath ):
            if sourceFilePath in subsetFilesList : return True
            baseName = os.path.basename( sourceFilePath )
            if baseName in subsetFilesList : return True
            return False
        sourceFilePathList = [sourceFilePath for sourceFilePath in sourceFilePathList if inSubsetFilesList (sourceFilePath)]

    # =========== Define comment swapping tools
            
    shebangCommentRegEx = re.compile (r'^{0}!'.format (r'#'))
    codingCommentRegEx = re.compile ('coding[:=]\s*([-\w.]+)')
    keepCommentRegEx = re.compile ('.*{0}.*'.format (plainMarker), re.DOTALL)  # @UndefinedVariable
        
    def getCommentPlaceholderAndRegister (matchObject):
        comment = matchObject.group (0)
        if keepCommentRegEx.search (comment):   # Rare, so no need for speed
            replacedComments.append (comment.replace (plainMarker, ''))
            return commentPlaceholder
        else:
            return ''
        
    def getComment (matchObject):  # @UnusedVariable
        global commentIndex
        commentIndex += 1
        return replacedComments [commentIndex]
        
    commentRegEx = (
            re.compile (r'{0}{1}{2}.*?$'.format (
                r"(?<!')",
                r'(?<!")',
                r'  # '  # According to PEP8 an inline comment should start like this.
            ), re.MULTILINE) # @UndefinedVariable
        if pep8Comments else  
            re.compile (r'{0}{1}{2}.*?$'.format (
                r"(?<!')",
                r'(?<!")',
                r'#'
            ), re.MULTILINE) # @UndefinedVariable
    )
    commentPlaceholder = '_{0}_c_'.format (PROGRAM_NAME)
    commentPlaceholderRegEx = re.compile (r'{0}'.format (commentPlaceholder))

    # ============ Define string swapping tools

    keepStringRegEx = re.compile (r'.*{0}.*'.format (plainMarker))
        
    def getDecodedStringPlaceholderAndRegister (matchObject): 
        string = matchObject.group (0)
        if obfuscateStrings:
            if keepStringRegEx.search (string): # Rare, so no need for speed
                replacedStrings.append (string.replace (plainMarker, ''))
                return stringPlaceholder    # Store original string minus plainMarker, no need to unscramble
            else:
                replacedStrings.append (scramble (string))
                return 'unScramble{0} ({1})'.format (plainMarker, stringPlaceholder)    # Store unScramble (<scrambledString>)
        else:
            replacedStrings.append (string)
            return stringPlaceholder
        
    def getString (matchObject):  # @UnusedVariable
        global stringIndex
        stringIndex += 1
        return replacedStrings [stringIndex]

    stringRegEx = re.compile (r'([ru]|ru|ur|[rb]|rb|br)?(({0})|({1})|({2})|({3}))'.format (
        r"'''.*?(?<![^\\]\\)(?<![^\\]\')'''",
        r'""".*?(?<![^\\]\\)(?<![^\\]\")"""',
        r"'.*?(?<![^\\]\\)'",
        r'".*?(?<![^\\]\\)"'
    ), re.MULTILINE | re.DOTALL | re.VERBOSE) # @UndefinedVariable

    stringPlaceholder = '_{0}_s_'.format (PROGRAM_NAME)
    stringPlaceholderRegEx = re.compile (r'{0}'.format (stringPlaceholder))

    # ============ Define 'from future' moving tools

    def moveFromFuture (matchObject):
        fromFuture = matchObject.group (0)

        if fromFuture:
            global nrOfSpecialLines
            contentList [nrOfSpecialLines:nrOfSpecialLines] = [fromFuture]  # Move 'from __future__' line after other special lines
            nrOfSpecialLines += 1
        return ''
        
    fromFutureRegEx = re.compile ('from\s*__future__\s*import\s*\w+.*$', re.MULTILINE) # @UndefinedVariable

    # ============ Define identifier recognition tools

    identifierRegEx = re.compile (r'''
        \b          # Delimeted
        (?!{0})     # Not starting with commentPlaceholder
        (?!{1})     # Not starting with stringPlaceholder
        [^\d\W]     # De Morgan: Not (decimal or nonalphanumerical) = not decimal and alphanumerical
        \w*         # Alphanumerical
        (?<!__)     # Not ending with __
        (?<!{0})    # Not ending with commentPlaceholder
        (?<!{1})    # Not ending with stringPlaceHolder
        \b          # Delimited
    '''.format (commentPlaceholder, stringPlaceholder), re.VERBOSE) # De Morgan # @UndefinedVariable

    chrRegEx = re.compile (r'\bchr\b')

    # =========== Generate skip list
    
    skipWordSet = set (keyword.kwlist + ['__init__'] + extraPlainWordList)  # __init__ should be in, since __init__.py is special
    if not isPython2: skipWordSet.update( ['unicode', 'unichr' ] ) # not naturally kept in clear text when obfuscation is produced in Python 3

    rawPlainFilePathList = ['{0}/{1}'.format (sourceRootDirectory, plainFileRelPath.replace ('\\', '/')) for plainFileRelPath in plainFileRelPathList]
    
    # Prevent e.g. attempt to open opy_config.txt if it is in a different location but still listed under plain_files
    
    plainFilePathList = [plainFilePath for plainFilePath in rawPlainFilePathList if os.path.exists (plainFilePath)]
    
    for plainFilePath in plainFilePathList:
        plainFile = open (plainFilePath)
        content = plainFile.read ()
        plainFile.close ()
        
        # Throw away comment-like line tails
        
        content = commentRegEx.sub ('', content)
        
        # Throw away strings
        
        content = stringRegEx.sub ('', content)
        
        # Put identifiers in skip word set
        
        skipWordSet.update (re.findall (identifierRegEx, content))
        
    class ExternalModules:
        def __init__ (self):
            for externalModuleName in externalModuleNameList:
                attributeName = externalModuleName.replace ('.', plainMarker)   # Replace . in module name by placeholder to get attribute name
                
                try:
                    exec (
                        '''
import {0} as currentModule
                        '''.format (externalModuleName),
                        globals ()
                    )
                    setattr (self, attributeName, currentModule)    # @UndefinedVariable
                except Exception as exception:
                    print (exception)
                    setattr (self, attributeName, None) # So at least the attribute name will be available
                    print ('Warning: could not inspect external module {0}'.format (externalModuleName))
                
    externalModules = ExternalModules ()
    externalObjects = set ()
                
    def addExternalNames (anObject):
        if anObject in externalObjects:
            return
        else:
            externalObjects.update ([anObject])

        try:
            attributeNameList = list (anObject.__dict__)
        except:
            attributeNameList = []
        
        try:
            if isPython2:
                parameterNameList = list (anObject.func_code.co_varnames)
            else:
                parameterNameList = list (anObject.__code__.co_varnames)
        except:     
            parameterNameList = []
            
        attributeList = [getattr (anObject, attributeName) for attributeName in attributeNameList]
        attributeSkipWordList = (plainMarker.join (attributeNameList)) .split (plainMarker) # Split module name chunks that were joined by placeholder
        
        updateSet = set ([entry for entry in (parameterNameList + attributeSkipWordList) if not (entry.startswith ('__') and entry.endswith ('__'))])
        # Entries both starting and ending with __ are skipped anyhow by the identifier regex, not including them here saves time
        
        skipWordSet.update (updateSet)
        
        for attribute in attributeList: 
            try:
                addExternalNames (attribute)
            except:
                pass


    addExternalNames (__builtin__ if isPython2 else builtins) 
    addExternalNames (externalModules)

    skipWordList = list (skipWordSet)
    skipWordList.sort (key = lambda s: s.lower ())

    # ============ Generate obfuscated files

    obfuscatedFileDict = {}
    obfuscatedWordList = []
    obfuscatedWordDict = {}
    obfuscatedRegExList = []
    skippedPublicSet=set()

    for sourceFilePath in sourceFilePathList:
        if sourceFilePath == configFilePath:    # Don't copy the config file to the target directory
            continue

        sourceDirectory, sourceFileName = sourceFilePath.rsplit ('/', 1)
        sourceFilePreName, sourceFileNameExtension = (sourceFileName.rsplit ('.', 1) + ['']) [ : 2]
        targetRelSubDirectory = sourceFilePath [len (sourceRootDirectory) : ]
        clearRelPath = targetRelSubDirectory[1:] # remove leading /
                
        # Read plain source

        if sourceFileNameExtension in sourceFileNameExtensionList and not sourceFilePath in plainFilePathList:
            stringBase = random.randrange (64)
        
            sourceFile = codecs.open (sourceFilePath, encoding = DEFAULT_ENCODING)
            content = sourceFile.read () 
            sourceFile.close ()
            
            if skipPublicIdentifiers:
                skippedPublicSet.update( opy_parser.findPublicIdentifiers( content ) )
                skipWordSet.update( skippedPublicSet )   
            
            replacedComments = []
            contentList = content.split ('\n', 2)
                
            nrOfSpecialLines = 0
            insertCodingComment = True
            
            if len (contentList) > 0:
                if shebangCommentRegEx.search (contentList [0]):                                # If the original code starts with a shebang line
                    nrOfSpecialLines += 1                                                       #   Account for that
                    if len (contentList) > 1 and codingCommentRegEx.search (contentList [1]):   #   If after the shebang a coding comment follows
                        nrOfSpecialLines += 1                                                   #       Account for that
                        insertCodingComment = False                                             #       Don't insert, it's already there
                elif codingCommentRegEx.search (contentList [0]):                               # Else if the original code starts with a coding comment
                    nrOfSpecialLines += 1                                                       #   Account for that
                    insertCodingComment = False                                                 #   Don't insert, it's already there
                
            if obfuscateStrings and insertCodingComment:                                        # Obfuscated strings are always converted to unicode
                contentList [nrOfSpecialLines:nrOfSpecialLines] = ['# coding: ' + DEFAULT_ENCODING]           # Insert the coding line if it wasn't there
                nrOfSpecialLines += 1                                                           # And remember it's there
                                                                                                # Nothing has to happen with an eventual shebang line
            if obfuscateStrings:
                normalContent = '\n'.join ([getUnScrambler (stringBase)] + contentList [nrOfSpecialLines:])
            else:
                normalContent = '\n'.join (contentList [nrOfSpecialLines:])
                
            # At this point normalContent does not contain the special lines
            # They are in contentList
            
            normalContent = commentRegEx.sub (getCommentPlaceholderAndRegister, normalContent)
             
            # Replace strings by string place holders
            
            replacedStrings = []
            normalContent = stringRegEx.sub (getDecodedStringPlaceholderAndRegister, normalContent)
            
            # Take eventual out 'from __future__ import ... ' line and add it to content list
            # Content list is prepended to normalContent later
            
            normalContent = fromFutureRegEx.sub (moveFromFuture, normalContent)

            # Replace any imported modules per the old/new (key/value) pairs provided
            if len(replacementModulesDict) > 0 : 
                normalContent = opy_parser.replaceImports( normalContent, replacementModulesDict )
                                
            # Parse content to find imports and optionally provide aliases for those in clear text,
            # so that they will become "masked" upon obfuscation.
            if maskExternalModules : 
                normalContent = opy_parser.injectAliases( normalContent, externalModuleNameList )
            else:  
                opy_parser.analyzeImports( normalContent, externalModuleNameList )

            if not preppedOnly :
                # Obfuscate content without strings
                
                # All source words and module name
                sourceWordSet = set (re.findall (identifierRegEx, normalContent) + [sourceFilePreName])
                
                # Add source words that are not yet obfuscated and shouldn't be skipped to global list of obfuscated words, preserve order of what's already there
                strippedSourceWordSet = sourceWordSet.difference (obfuscatedWordList).difference (skipWordSet)  # Leave out what is already or shouldn't be obfuscated
                strippedSourceWordList = list (strippedSourceWordSet)
                strippedSourceRegExList = [re.compile (r'\b{0}\b'.format (sourceWord)) for sourceWord in strippedSourceWordList]    # Regex used to replace obfuscated words
                obfuscatedWordList += strippedSourceWordList            
                obfuscatedRegExList += strippedSourceRegExList
                
                # Replace words to be obfuscated by obfuscated ones
                for obfuscationIndex, obfuscatedRegEx in enumerate (obfuscatedRegExList):              
                    clrName = obfuscatedWordList[ obfuscationIndex ]     
                    obfName = getObfuscatedName( obfuscationIndex, clrName )
                    obfuscatedWordDict[clrName]=obfName
                    # Use regex to prevent replacing word parts
                    normalContent = obfuscatedRegEx.sub ( obfName, normalContent )   
                    
                    
            # Replace string place holders by strings
            
            stringIndex = -1
            normalContent = stringPlaceholderRegEx.sub (getString, normalContent)
        
            # Replace nonempty comment place holders by comments
            
            commentIndex = -1
            normalContent = commentPlaceholderRegEx.sub (getComment, normalContent)
            
            content = '\n'.join (contentList [:nrOfSpecialLines] + [normalContent])
            
            # Remove empty lines
            
            content = '\n'.join ([line for line in [line.rstrip () for line in content.split ('\n')] if line])
            
            if preppedOnly :
                targetFilePreName = sourceFilePreName 
                targetSubDirectory = '{0}{1}'.format (targetRootDirectory, targetRelSubDirectory) .rsplit ('/', 1) [0]
            else :                     
                # Obfuscate module name
                try:
                    targetFilePreName = getObfuscatedName (obfuscatedWordList.index (sourceFilePreName), sourceFilePreName)
                except: # Not in list, e.g. top level module name
                    targetFilePreName = sourceFilePreName
                
                # Obfuscate module subdir names, but only above the project root!
                targetChunks = targetRelSubDirectory.split ('/')
                for index in range (len (targetChunks)):
                    try:
                        targetChunks [index] = getObfuscatedName (obfuscatedWordList.index (targetChunks [index]), targetChunks [index])
                    except: # Not in list
                        pass
                targetRelSubDirectory = '/'.join (targetChunks)
                targetSubDirectory = '{0}{1}'.format (targetRootDirectory, targetRelSubDirectory) .rsplit ('/', 1) [0]

            # Create target path and track it against clear text relative source                       
            obfusPath = '{0}/{1}.{2}'.format (targetSubDirectory, targetFilePreName, sourceFileNameExtension)
            obfuscatedFileDict[clearRelPath] = obfusPath

            # Bail before the actual path / file creation on a dry run 
            if dryRun : continue

            # Create target path and write file                        
            targetFile = createFilePath (obfusPath, open = True)
            targetFile.write (content)
            targetFile.close ()
        elif (not dryRun) and (not sourceFileNameExtension in skipFileNameExtensionList):
            targetSubDirectory = '{0}{1}'.format (targetRootDirectory, targetRelSubDirectory) .rsplit ('/', 1) [0]
            
            # Create target path and copy file
            targetFilePath = '{0}/{1}'.format (targetSubDirectory, sourceFileName)
            createFilePath (targetFilePath)
            shutil.copyfile (sourceFilePath, targetFilePath)

    # POST PROCESS
    #-----------------------------------------------------------------------------------
     
    # for maskedIdentifiers, swap the clear text masks with the obfuscations  
    # for obfuscatedWordDict, remove the mask entries
    masks=[]
    for clr, obf in six.iteritems( obfuscatedWordDict ):
        for unMasked, masked in six.iteritems( opy_parser.maskedIdentifiers ):
            if masked==clr:
                masks.append( clr )
                opy_parser.maskedIdentifiers[ unMasked ] = obf                
                break    
    for m in masks: obfuscatedWordDict.pop( m, None )

    print ('>>> Obfuscation Summary:')                
    print ('Target Root Directory: {0}'.format ( targetRootDirectory ))
    print ('Obfuscated files: {0}'.format ( len(obfuscatedFileDict) ))
    print ('Obfuscated identifiers: {0}'.format (len(obfuscatedWordDict)))
    print ('Masked identifiers: {0}'.format (len(opy_parser.maskedIdentifiers)))
    print ('Clear text public identifiers: {0}'.format (len(skippedPublicSet)))
    print ('Obfuscated module references: {0}'.format (len(opy_parser.obfuscatedModImports)))                    
    print ('Clear text module references: {0}'.format (len(opy_parser.clearTextModImports)))
    print ('')
    print ('>>> Obfuscation Details:')            
    print ('Obfuscated files: {0}'.format ( obfuscatedFileDict ))
    print ('Obfuscated identifiers: {0}'.format ( obfuscatedWordDict ))
    print ('Masked identifiers: {0}'.format ( opy_parser.maskedIdentifiers ))
    print ('Clear text public identifiers: {0}'.format (skippedPublicSet))
    print ('Obfuscated module references: {0}'.format (opy_parser.obfuscatedModImports))                    
    print ('Clear text module references: {0}'.format (opy_parser.clearTextModImports))
    print ('')    
    
    results = OpyResults()    
    results.obfuscatedFiles = obfuscatedFileDict
    results.obfuscatedIds   = obfuscatedWordDict   
    results.obfuscatedMods  = opy_parser.obfuscatedModImports    
    results.maskedIds       = opy_parser.maskedIdentifiers
    results.clearTextMods   = opy_parser.clearTextModImports
    results.clearTextPublic = skippedPublicSet        
    results.clearTextIds    = skipWordList    
    return results

# Opyfying something twice can and is allowed to fail.
# The obfuscation for e.g. variable 1 in round 1 can be the same as the obfuscation for e.g. variable 2 in round 2.
# If in round 2 variable 2 is replaced first, the obfuscation from round 1 for variable 1 will be replaced by the same thing.
    
if __name__ == '__main__': __run()
