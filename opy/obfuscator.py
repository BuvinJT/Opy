import re
import os
import sys
import errno
import keyword
import random
import codecs
import shutil
from six import PY2, iteritems

PROGRAM_NAME = 'opy'
DEFAULT_ENCODING = 'utf-8'
DEBUG_LEVEL = 1

from . _version import __version__  
from . inspector import Inspector
from . parser import Parser, \
    rootImportName, rootFileName, toProjectSubPackage

def _toCleanStrList(l):
    try:    
        ret = list(set(l))
        ret = [str(x).strip() for x in ret if x is not None]
        ret = [x for x in ret if len(x) != 0]
        return ret 
    except: return []

class OpyError(Exception): pass

class OpyResults:

    def __init__(self):
        self.obfuscatedFiles   = None
        self.obfuscatedIds     = None   
        self.clearTextIds      = None
        self.obfuscatedImports = None
        self.clearTextImports  = None                   
        self.maskedImports     = None
        self.obfuscatedMods    = None
        self.clearTextMods     = None                      
        self.toClearTextMods   = None
        self.toClearTextIds    = None
        self.clearTextPublic   = None
    
class Obfuscator():

    __runCount = 0
        
    def __init__( self ):                
        self.clearTextMods=[]
        self.clearTextIds=[] 
        self.obfuscateExts=[] 
        self.replacements={}
        
        self.__fetchStandardExclusions()
        self._parser = Parser( self )
                
    def _autoConfig( self, runOptions, isVerbose ):    
            
        isPreserving = runOptions.config.preserve_unresolved_imports
        isThrowing = runOptions.config.error_on_unresolved_imports
        
        # first analyze, then auto configure OR error out if a problem is detected
        analysis = self._analyze(runOptions, isVerbose=False)    
        obMods = analysis.obfuscatedMods    
        
        # handle unresolved imports
        if len(obMods) > 0:                                
            if isPreserving:
                if isVerbose: 
                    for m in obMods: 
                        print("WARNING unresolved module: %s" % (m,))
                    print("")
                try:    runOptions.config.external_modules.extend(obMods)
                except: runOptions.config.external_modules = obMods
            elif isThrowing:                    
                raise OpyError("Unresolved module(s): %s" % (",".join(obMods),)) 

        # extend the clear text mods list as directed by the analysis  
        clearMods = analysis.toClearTextMods   
        if len(clearMods) > 0: 
                if isVerbose: 
                    print("Imported modules found which must remain in clear text: %s" 
                          % (",".join(clearMods),))   
                try:    runOptions.config.external_modules.extend(clearMods)
                except: runOptions.config.external_modules = clearMods
    
        # extend the clear text id list as directed by the analysis  
        clearIds = analysis.toClearTextIds   
        if len(clearIds) > 0: 
                if isVerbose: 
                    print("Imports ids found which must remain in clear text: %s" 
                          % (",".join(clearIds),))   
                try:    runOptions.config.plain_names.extend(clearIds)
                except: runOptions.config.plain_names = clearIds
            
        print("")
    
    def _analyze( self, runOptions, isVerbose ):
        # allow for the same runOptions to work for both analyze and obfuscate                  
        savedDryRun = runOptions.config.dry_run    
        runOptions.config.dry_run = True
        results = self._run( runOptions, isVerbose )    
        runOptions.config.dry_run = savedDryRun
        return results
    
    def _run( self, runOptions, isVerbose=True):      
                     
        if Obfuscator.__runCount == 0:
            print ('{} (TM) Configurable Multi Module Python Obfuscator Version {}'.format (PROGRAM_NAME.capitalize (), __version__))
            print ('Copyright (C) Geatec Engineering. License: Apache 2.0 at  http://www.apache.org/licenses/LICENSE-2.0\n')
        Obfuscator.__runCount += 1
    
        if runOptions and (DEBUG_LEVEL > 0 or isVerbose):
            runOptions.config._clean()
            if runOptions.config.dry_run:
                print(">>> ANALYZING: ")
                print("source directory: %s" % (runOptions.sourceRootDirectory,))
                print("configuration: \n%s" % (runOptions.config,))                
            else :
                print(">>> OBFUSCATING: ")
                print("source directory: %s" % (runOptions.sourceRootDirectory,))
                print("target directory: %s" % (runOptions.targetRootDirectory,))
                print("config file path: %s" % (runOptions.configFilePath,))
                print("configuration: \n%s" % (runOptions.config,))    
    
        self._parser._reset()
    
        random.seed()
    
        charBase = 2048  # Choose high to prevent string recoding from generating special chars like ', " and \
        self.stringNr = charBase
        charModulus = 7
    
        # =========== Utilities   
    
        def createFilePath( filePath, open=False ):  # @ReservedAssignment
            try: os.makedirs( filePath.rsplit('/', 1)[0] )
            except OSError as exception:
                if exception.errno != errno.EEXIST: raise                    
            if open:
                return codecs.open( filePath, encoding=DEFAULT_ENCODING, 
                                    mode='w' )
    
        def addObfuscatedWords( sourceWordSet ):
            
            if isinstance( sourceWordSet, list ): sourceWordSet = set(sourceWordSet)
            
            # Add source words that are not yet obfuscated and shouldn't be skipped 
            # to global list of obfuscated words, preserve order of what's already 
            # there. Leave out what is already or shouldn't be obfuscated
            newWords = list( sourceWordSet.difference( 
                self.obfuscatedWordList ).difference( self.skipWordSet ) )
            if DEBUG_LEVEL > 1: print("Adding obfuscated words: ", newWords )
            initLen = len(self.obfuscatedWordList)                                  
            self.obfuscatedWordList += newWords
                        
            # Maintain self.obfuscatedWordDict for analysis
            for idx, name in enumerate( newWords ):              
                self.obfuscatedWordDict[ name ] = getObfuscatedName( initLen+idx, name )
    
            # Regex used to replace obfuscated words
            newRegExs = [ re.compile( r'\b{0}\b'.format( w ) ) for w in newWords ]
            self.obfuscatedRegExList += newRegExs        
                
        def getObfuscatedName (obfuscationIndex, name):
            return '{0}{1}{2}'.format (
                '__' if name.startswith ('__') else '_' if name.startswith ('_') else 'l',
                bin (obfuscationIndex) [2:] .replace ('0', 'l'),
                self.obfTail
            )
                        
        def scramble(stringLiteral):           
            if PY2:
                recodedStringLiteral = unicode().join( # @UndefinedVariable
                    [unichr(charBase + ord(char) + # @UndefinedVariable
                            (charIndex + self.stringNr) % charModulus)  
                     for charIndex, char in enumerate(stringLiteral)] )  
                stringKey = unichr(self.stringNr)  # @UndefinedVariable
            else:
                recodedStringLiteral = str().join(
                    [chr(charBase + ord(char) + 
                          (charIndex + self.stringNr) % charModulus) 
                     for charIndex, char in enumerate(stringLiteral)])
                stringKey = chr(self.stringNr)
                
            rotationDistance = self.stringNr % len(stringLiteral)
            rotatedStringLiteral =( recodedStringLiteral[:-rotationDistance] + 
                                    recodedStringLiteral[-rotationDistance:] )
            keyedStringLiteral = rotatedStringLiteral + stringKey
            
            self.stringNr += 1
            return 'u"' + keyedStringLiteral + '"'      
            
        def getUnScrambler(stringBase):  # @UnusedVariable
            return '''
from sys import version_info as __opyVerInfo

PY2{0} = __opyVerInfo[0] == 2
charBase{0} = {1}
charModulus{0} = {2}

def unScramble{0} (keyedStringLiteral):
    global stringNr{0}
    
    stringNr = ord (keyedStringLiteral [-1])
    rotatedStringLiteral = keyedStringLiteral [:-1]
    
    rotationDistance = stringNr % len (rotatedStringLiteral)
    recodedStringLiteral = rotatedStringLiteral [:rotationDistance] + rotatedStringLiteral [rotationDistance:]
        
    if PY2{0}:
        stringLiteral = unicode () .join ([unichr (ord (char) - charBase{0} - (charIndex + stringNr) % charModulus{0}) for charIndex, char in enumerate (recodedStringLiteral)])
    else:
        stringLiteral = str () .join ([chr (ord (char) - charBase{0} - (charIndex + stringNr) % charModulus{0}) for charIndex, char in enumerate (recodedStringLiteral)])
        
    return eval (stringLiteral)
    '''.format (self.plainMarker, charBase, charModulus) 
                
        def printHelpAndExit(errorLevel):
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
    
            '''.format(PROGRAM_NAME.capitalize(), PROGRAM_NAME, r'#', license))
            if errorLevel is not None: exit(errorLevel)
            
        # ============ Assign directories ============
    
        if runOptions:
            # Use library settings 
            if runOptions.printHelp: printHelpAndExit(None)                   
                        
            if runOptions.sourceRootDirectory is not None:                    
                sourceRootDirectory = runOptions.sourceRootDirectory.replace('\\', '/')
            else:
                sourceRootDirectory = os.getcwd ().replace('\\', '/')
    
            if runOptions.targetRootDirectory is not None:
                self.targetRootDirectory = runOptions.targetRootDirectory.replace('\\', '/')
            else:
                self.targetRootDirectory = '{0}/{1}_{2}'.format(* (sourceRootDirectory.rsplit ('/', 1) + [PROGRAM_NAME]))
    
            if runOptions.configFilePath == False :
                configFilePath = ""
            elif runOptions.configFilePath is not None:
                configFilePath = runOptions.configFilePath.replace('\\', '/')
            else:
                configFilePath = '{0}/{1}_config.txt'.format(sourceRootDirectory, PROGRAM_NAME)    
        else:
            # Use command line arguments
            if len(sys.argv) > 1:
                for switch in '?', '-h', '--help':
                    if switch in sys.argv[1]:
                        printHelpAndExit (0)
                sourceRootDirectory = sys.argv[1].replace('\\', '/')
            else:
                sourceRootDirectory = os.getcwd().replace('\\', '/')
    
            if len(sys.argv) > 2:
                self.targetRootDirectory = sys.argv[2].replace('\\', '/')
            else:
                self.targetRootDirectory = '{0}/{1}_{2}'.format(* (sourceRootDirectory.rsplit ('/', 1) + [PROGRAM_NAME]))
    
            if len(sys.argv) > 3:
                configFilePath = sys.argv[3].replace('\\', '/')
            else:
                configFilePath = '{0}/{1}_config.txt'.format(sourceRootDirectory, PROGRAM_NAME)
                
        # =========== Read config file
    
        global obfuscate_strings, ascii_strings, obfuscated_name_tail
        global plain_marker, pep8_comments, source_extensions, skip_extensions
        global skip_path_fragments, external_modules, mask_external_modules
        global skip_public, plain_files, plain_names, dry_run, prepped_only
        global subset_files
    
        if configFilePath == "":        
            configFile = runOptions.config.toVirtualFile()
        else :        
            try: configFile = open(configFilePath)
            except Exception as exception:
                print(exception)
                printHelpAndExit (1)
            
        exec (configFile.read (), globals())
        configFile.close()
        
        def getConfig(parameter, default):
            try:    return eval (parameter)
            except: return default
        
        self.obfuscateStrings = getConfig ('obfuscate_strings', False)
        self.asciiStrings = getConfig ('ascii_strings', False)
        self.obfTail = getConfig ('obfuscated_name_tail', '_{}_')
        self.plainMarker = getConfig ('plain_marker', '_{}_'.format (PROGRAM_NAME))
        self.pep8Comments = getConfig ('pep8_comments', True)
        self.sourceFileNameExtensionList = getConfig ('source_extensions.split ()', ['py', 'pyx'])
        self.skipFileNameExtensionList = getConfig ('skip_extensions.split ()', ['pyc'])
        self.skipPathFragmentList = getConfig ('skip_path_fragments.split ()', [])
        self.externalModuleNameList = getConfig ('external_modules.split ()', [])
        self.maskExternalModules = getConfig ('mask_external_modules', False)
        self.skipPublicIdentifiers = getConfig ('skip_public', False)
        self.plainFileRelPathList = getConfig ('plain_files.split ()', [])
        self.extraPlainWordList = getConfig ('plain_names.split ()', [])
        self.dryRun = getConfig ('dry_run', False)
        self.preppedOnly = getConfig ('prepped_only', False)
        self.subsetFilesList = getConfig ('subset_files.split ()', [])
    
        # TODO: Handle spaces between key/colon/value, e.g. 'key : value'     
        self.replacementModulesDict = {}
        replacementModulesPairList = getConfig ('replacement_modules.split ()', [])
        for pair in replacementModulesPairList:
            pairParts = pair.split(":") 
            try: self.replacementModulesDict[ pairParts[0].strip() ] = pairParts[1].strip()
            except: continue        
            
        # ============ Gather source file names
        self.rawSourceFilePathList=[]
        self.topLevelSubDirectories=[]
        for directory, subDirectories, fileNames in os.walk( sourceRootDirectory ):
            self.rawSourceFilePathList += [ 
                os.path.join( directory, fileName ) for fileName in fileNames ]
            try:
                if len(os.path.split(subDirectories[0])[0])==0: 
                    for sub in subDirectories: 
                        self.topLevelSubDirectories.append( sub )
            except: pass
        
        def hasSkipPathFragment(sourceFilePath):
            for skipPathFragment in self.skipPathFragmentList:
                if skipPathFragment in sourceFilePath:
                    return True
            return False
        
        self.sourceFilePathList = [
            sourceFilePath for sourceFilePath in self.rawSourceFilePathList 
            if not hasSkipPathFragment (sourceFilePath) ]
    
        if len(self.subsetFilesList) > 0 :        
            def inSubsetFilesList(sourceFilePath):
                if sourceFilePath in self.subsetFilesList : return True
                baseName = os.path.basename(sourceFilePath)
                if baseName in self.subsetFilesList : return True
                return False
            self.sourceFilePathList = [
                sourceFilePath for sourceFilePath in self.sourceFilePathList 
                if inSubsetFilesList(sourceFilePath)]
    
        # =========== Define comment swapping tools
                
        shebangCommentRegEx = re.compile(r'^{0}!'.format (r'#'))
        codingCommentRegEx = re.compile('coding[:=]\s*([-\w.]+)')
        keepCommentRegEx = re.compile('.*{0}.*'.format (self.plainMarker), re.DOTALL)  # @UndefinedVariable
            
        def getCommentPlaceholderAndRegister(matchObject):
            comment = matchObject.group(0)
            if keepCommentRegEx.search(comment):  # Rare, so no need for speed
                replacedComments.append(comment.replace (self.plainMarker, ''))
                return commentPlaceholder
            else:
                return ''
            
        def getComment (matchObject):  # @UnusedVariable
            self.commentIndex += 1
            return replacedComments[self.commentIndex]
            
        commentRegEx = (
                re.compile (r'{0}{1}{2}.*?$'.format (
                    r"(?<!')",
                    r'(?<!")',
                    r'  # '  # According to PEP8 an inline comment should start like this.
                ), re.MULTILINE)  # @UndefinedVariable
            if self.pep8Comments else  
                re.compile (r'{0}{1}{2}.*?$'.format (
                    r"(?<!')",
                    r'(?<!")',
                    r'#'
                ), re.MULTILINE)  # @UndefinedVariable
        )
        commentPlaceholder = '_{0}_c_'.format(PROGRAM_NAME)
        commentPlaceholderRegEx = re.compile(r'{0}'.format (commentPlaceholder))
    
        # ============ Define string swapping tools
    
        keepStringRegEx = re.compile (r'.*{0}.*'.format(self.plainMarker))
            
        def getDecodedStringPlaceholderAndRegister(matchObject): 
            string = matchObject.group(0)
            if self.obfuscateStrings:
                if keepStringRegEx.search(string):  # Rare, so no need for speed
                    replacedStrings.append(string.replace(self.plainMarker, ''))
                    return stringPlaceholder  # Store original string minus self.plainMarker, no need to unscramble
                else:
                    replacedStrings.append(scramble(string))
                    return 'unScramble{0} ({1})'.format(self.plainMarker, stringPlaceholder)  # Store unScramble (<scrambledString>)
            else:
                replacedStrings.append(string)
                return stringPlaceholder
            
        def getString(matchObject):  # @UnusedVariable
            self.stringIndex += 1
            return replacedStrings [self.stringIndex]
    
        stringRegEx = re.compile (r'([ru]|ru|ur|[rb]|rb|br)?(({0})|({1})|({2})|({3}))'.format(
            r"'''.*?(?<![^\\]\\)(?<![^\\]\')'''",
            r'""".*?(?<![^\\]\\)(?<![^\\]\")"""',
            r"'.*?(?<![^\\]\\)'",
            r'".*?(?<![^\\]\\)"'
        ), re.MULTILINE | re.DOTALL | re.VERBOSE)  # @UndefinedVariable
    
        stringPlaceholder = '_{0}_s_'.format (PROGRAM_NAME)
        stringPlaceholderRegEx = re.compile (r'{0}'.format (stringPlaceholder))
    
        # ============ Define 'from future' moving tools
    
        def moveFromFuture (matchObject):
            fromFuture = matchObject.group (0)
    
            if fromFuture:
                contentList[self.nrOfSpecialLines:self.nrOfSpecialLines] = [fromFuture]  # Move 'from __future__' line after other special lines
                self.nrOfSpecialLines += 1
            return ''
            
        fromFutureRegEx = re.compile ('from\s*__future__\s*import\s*\w+.*$', re.MULTILINE)  # @UndefinedVariable
    
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
        '''.format (commentPlaceholder, stringPlaceholder), re.VERBOSE)  # De Morgan # @UndefinedVariable
    
        chrRegEx = re.compile (r'\bchr\b')
    
        # =========== Generate skip list
        
        # __init__ should be in, since __init__.py is special
        self.skipWordSet = set( keyword.kwlist + ['__init__'] + self.extraPlainWordList )
        # these are not naturally kept in clear text when obfuscation is produced in Python 3  
        if not PY2: self.skipWordSet.update(['unicode', 'unichr' ])  
    
        self.rawPlainFilePathList = [
            '{0}/{1}'.format(sourceRootDirectory, plainFileRelPath.replace ('\\', '/')) 
            for plainFileRelPath in self.plainFileRelPathList ]
        
        # Prevent e.g. attempt to open opy_config.txt if it is in a different location but still listed under plain_files
        
        self.plainFilePathList = [plainFilePath for plainFilePath 
                                  in self.rawPlainFilePathList 
                                  if os.path.exists (plainFilePath)]
        
        for plainFilePath in self.plainFilePathList:
            plainFile = open (plainFilePath)
            content = plainFile.read ()
            plainFile.close ()        
            # Throw away comment-like line tails        
            content = commentRegEx.sub ('', content)        
            # Throw away strings        
            content = stringRegEx.sub ('', content)        
            # Put identifiers in skip word set        
            self.skipWordSet.update (re.findall (identifierRegEx, content))
            
            
        self.inspector = Inspector( self.externalModuleNameList, 
                                    self.plainMarker, isVerbose )
        #print(self.inspector.publicIds)           
        self.skipWordSet.update( self.inspector.publicIds )                 
        self.skipWordList = list( self.skipWordSet )
        self.skipWordList.sort( key=lambda s: s.lower () )
    
        # ============ Generate obfuscated files
        
        self.obfuscatedFileDict = {}
        self.obfuscatedWordDict = {}
        self.obfuscatedWordList = []    
        self.obfuscatedRegExList = []
        self.skippedPublicSet = set()
    
        # TODO: FIRST step through all files, looking for words to skip...
    
        # get obfuscated names for all files / sub directories to be created 
        for path in self.sourceFilePathList:
            if path == configFilePath: continue
            if path in self.plainFilePathList: continue
            head, ext = os.path.splitext(path)        
            try :             
                if ext[1:] not in self.sourceFileNameExtensionList: continue
            except: continue
            relPath = os.path.relpath( head, sourceRootDirectory )
            pathParts = relPath.split( '/' )
            pathParts = [p for p in pathParts if len(p) > 0]
            pathParts = [p for p in pathParts if p not in self.skipWordList]
            addObfuscatedWords( pathParts )
    
        for sourceFilePath in self.sourceFilePathList:
            # Don't copy the config file to the target directory
            if sourceFilePath == configFilePath: continue
    
            sourceDirectory, sourceFileName = sourceFilePath.rsplit('/', 1)
            sourceFilePreName, sourceFileNameExtension = (
                sourceFileName.rsplit('.', 1) + [''])[ : 2]
            targetRelSubDirectory = sourceFilePath [len (sourceRootDirectory) : ]
            clearRelPath = targetRelSubDirectory[1:]  # remove leading /
                    
            # Read plain source
    
            if( sourceFileNameExtension in self.sourceFileNameExtensionList and 
                not sourceFilePath in self.plainFilePathList ):
                stringBase = random.randrange (64)
            
                sourceFile = codecs.open (sourceFilePath, encoding=DEFAULT_ENCODING)
                content = sourceFile.read () 
                sourceFile.close ()
                
                # temporary setup for using the parser....
                self.clearTextMods=self.externalModuleNameList
                self.clearTextIds=list(self.skipWordSet)
                self.obfuscateExts=self.sourceFileNameExtensionList 
                self.replacements=self.replacementModulesDict
                
                if self.skipPublicIdentifiers:
                    self.skippedPublicSet.update(self._parser.findPublicIdentifiers(content))
                    self.skipWordSet.update(self.skippedPublicSet)   
                
                # Replace any imported modules per the old/new (key/value) pairs provided
                if len(self.replacementModulesDict) > 0 : 
                    content = self._parser.replaceModNames( content, sourceFilePath )
                                    
                # Parse content to find imports and optionally provide aliases for those in clear text,
                # so that they will become "masked" upon obfuscation.
                if self.maskExternalModules : 
                    # injectAliases implicitly analyzes
                    content = self._parser.injectAliases( content, sourceFilePath )
                else:  
                    self._parser.analyzeImports( content, sourceFilePath )
                
                replacedComments = []
                contentList = content.split( '\n', 2 )
                    
                self.nrOfSpecialLines = 0
                insertCodingComment = True
                
                if len(contentList) > 0:
                    if shebangCommentRegEx.search( contentList[0] ):  # If the original code starts with a shebang line
                        self.nrOfSpecialLines += 1  #   Account for that
                
                    # NOTE: While the original code preserved coding lines, we now replace them 
                            
                    #    if len(contentList) > 1 and codingCommentRegEx.search( contentList[1] ):  #   If after the shebang a coding comment follows
                    #        self.nrOfSpecialLines += 1  #       Account for that
                    #        insertCodingComment = False  #       Don't insert, it's already there
                    #elif codingCommentRegEx.search( contentList[0] ):  # Else if the original code starts with a coding comment
                    #    self.nrOfSpecialLines += 1  #   Account for that
                    #    insertCodingComment = False  #   Don't insert, it's already there
                    
                #if self.obfuscateStrings and insertCodingComment:  # Obfuscated strings are always converted to unicode
                if insertCodingComment:  
                    contentList [self.nrOfSpecialLines:self.nrOfSpecialLines] = [
                        '# coding: ' + DEFAULT_ENCODING ]  # Insert the coding line if it wasn't there
                    self.nrOfSpecialLines += 1  # And remember it's there
                                            # Nothing has to happen with an eventual shebang line
                if self.obfuscateStrings:
                    normalContent = '\n'.join(
                        [getUnScrambler(stringBase)] + contentList[self.nrOfSpecialLines:] )
                else:
                    normalContent = '\n'.join( contentList[self.nrOfSpecialLines:] )
                    
                # At this point normalContent does not contain the special lines
                # They are in contentList                
                normalContent = commentRegEx.sub( getCommentPlaceholderAndRegister, 
                                                  normalContent )                 
                # Replace strings by string place holders                
                replacedStrings = []
                normalContent = stringRegEx.sub( getDecodedStringPlaceholderAndRegister, 
                                                 normalContent )                
                # Take eventual out 'from __future__ import ... ' line and add it to content list
                # Content list is prepended to normalContent later                
                normalContent = fromFutureRegEx.sub( moveFromFuture, normalContent )
                                                                                        
                #topLevelSubDirectories
    
                #-------------------
    
                if not self.preppedOnly :
                    # Obfuscate content without strings
                    
                    # Collect all words in the source, plus the module name
                    sourceWordSet = set( re.findall( 
                        identifierRegEx, normalContent ) + [sourceFilePreName] )                
                    addObfuscatedWords( sourceWordSet )
    
                    # Replace words to be obfuscated 
                    # Use regex to prevent replacing word parts
                    for idx, regEx in enumerate( self.obfuscatedRegExList ):              
                        obf = getObfuscatedName( idx, self.obfuscatedWordList[ idx ] )                                    
                        normalContent = regEx.sub( obf, normalContent )   
                        
                # Replace string place holders by strings                
                self.stringIndex = -1
                normalContent = stringPlaceholderRegEx.sub( getString, normalContent )
            
                # Replace nonempty comment place holders by comments                
                self.commentIndex = -1
                normalContent = commentPlaceholderRegEx.sub( getComment, normalContent )

                def fixCrossLineStrings( content ):
                    import ast                                        
                    priorLineno=None 
                    unscramble = self.obfuscatedWordDict.get(
                        "unScramble{0}".format(self.plainMarker) )              
                    while True: 
                        try: 
                            ast.parse( content )  
                            return content                            
                        except SyntaxError as e:
                            if e.lineno==priorLineno : break 
                            priorLineno = e.lineno 
                            idx = e.lineno-1        
                            lines = content.split('\n') 
                            line = lines[idx]                    
                            if line.strip().startswith( unscramble ):
                                lines[idx-1] += ' \\' 
                                lines[idx] = line.replace( unscramble, 
                                                           "+ " + unscramble, 1 )
                            content = '\n'.join( lines )
                        except Exception as e:
                            print(e)
                            break         
                    return content                                                 
                normalContent = fixCrossLineStrings( normalContent )
                
                content = '\n'.join( contentList[:self.nrOfSpecialLines] + [normalContent] )
                
                # Remove empty lines                
                content = '\n'.join(
                    [line for line in 
                        [line.rstrip () for line in content.split('\n')] if line] )
                
                if self.preppedOnly :
                    targetFilePreName = sourceFilePreName 
                    targetSubDirectory = '{0}{1}'.format(
                        self.targetRootDirectory, targetRelSubDirectory ).rsplit('/', 1)[0]
                else :                     
                    # Obfuscate module name
                    try:
                        targetFilePreName = getObfuscatedName(
                            self.obfuscatedWordList.index( sourceFilePreName ), 
                            sourceFilePreName )
                    except:  # Not in list, e.g. top level module name
                        targetFilePreName = sourceFilePreName
                    if DEBUG_LEVEL > 2:
                        print("original file name %s changed to %s" % 
                               (sourceFilePreName, targetFilePreName))    
                    
                    # Obfuscate module subdir names, but only above the project root!
                    orginalSubDirectory = targetRelSubDirectory
                    targetChunks = targetRelSubDirectory.split('/')
                    for index in range (len (targetChunks)):
                        try:
                            if DEBUG_LEVEL > 2:
                                print("original dir part %s" % (targetChunks[index],))                            
                            targetChunks[index] = getObfuscatedName(
                                self.obfuscatedWordList.index( targetChunks [index] ), 
                                targetChunks[index] )
                            if DEBUG_LEVEL > 2:
                                print("changed to %s" % (targetChunks[index],))                            
                        except:  # Not in list
                            if DEBUG_LEVEL > 2:
                                print("kept as %s" % (targetChunks[index],))
                            pass
                    targetRelSubDirectory = '/'.join( targetChunks )
                    targetSubDirectory = '{0}{1}'.format(
                        self.targetRootDirectory, targetRelSubDirectory ).rsplit('/', 1)[0]
                    if DEBUG_LEVEL > 2:
                        print("original directory %s changed to %s" % 
                               (orginalSubDirectory, targetRelSubDirectory))    
    
                # Create target path and track it against clear text relative source                       
                obfusPath = '{0}/{1}.{2}'.format(
                    targetSubDirectory, targetFilePreName, sourceFileNameExtension )
                self.obfuscatedFileDict[clearRelPath] = obfusPath
                if DEBUG_LEVEL > 2:
                    print("original relative path %s mapped to target %s" % 
                           (clearRelPath, obfusPath))    
    
                # Bail before the actual path / file creation on a dry run 
                if self.dryRun : continue
    
                # Create target path and write file                        
                targetFile = createFilePath (obfusPath, open=True)
                targetFile.write (content)
                targetFile.close ()
            elif( not self.dryRun and 
                  not sourceFileNameExtension in self.skipFileNameExtensionList ):
                targetSubDirectory = '{0}{1}'.format(
                    self.targetRootDirectory, targetRelSubDirectory ).rsplit('/', 1)[0]                
                # Create target path and copy file
                targetFilePath = '{0}/{1}'.format (targetSubDirectory, sourceFileName)
                createFilePath (targetFilePath)
                shutil.copyfile (sourceFilePath, targetFilePath)
                
        return self.__results( runOptions, isVerbose )

    def __results( self, runOptions, isVerbose=True ):               
    
        # for maskedIdentifiers, swap the clear text masks with the obfuscations  
        # for self.obfuscatedWordDict, remove the mask entries
        masks = []
        for clr, obf in iteritems(self.obfuscatedWordDict):
            for unMasked, masked in iteritems(self._parser.maskedImports):
                if masked == clr:
                    masks.append(clr)
                    self._parser.maskedImports[ unMasked ] = obf                
                    break    
        for m in masks: self.obfuscatedWordDict.pop(m, None)        
            
        isStandardExc = runOptions.config.apply_standard_exclusions
        plainFiles = runOptions.config.plain_files
        plainNames = runOptions.config.plain_names
                    
        # filter out obfuscated mods which are included in the project     
        if len(self._parser.obfuscatedMods) > 0:
            obFiles = self.obfuscatedFileDict                
            projPkgs = ([toProjectSubPackage(f) for f in plainFiles] + 
                         [toProjectSubPackage(f) for f in obFiles])                                             
            projMods = ([rootFileName(f) for f in plainFiles] + 
                         [rootFileName(f) for f in obFiles])     
            if projPkgs   is None: projPkgs = []
            if projMods   is None: projMods = []
            if plainNames is None: plainNames = []
            self._parser.obfuscatedMods = [m for m in self._parser.obfuscatedMods
                        if rootImportName(m) not in projPkgs]                                
            self._parser.obfuscatedMods = [m for m in self._parser.obfuscatedMods
                if m not in projMods and m not in plainNames]
                         
        # apply standard exclusions
        if len(self._parser.obfuscatedMods) > 0 and isStandardExc:                         
            stdEx = [m for m in self._parser.obfuscatedMods
                      if m in self.standardExclusions
                      or rootImportName(m) in self.standardExclusions] 
            self._parser.obfuscatedMods = [m for m in self._parser.obfuscatedMods 
                                           if m not in stdEx]
            if len(stdEx) > 0: 
                if isVerbose or DEBUG_LEVEL > 0: 
                    print("Standard exclusions encountered: %s" % (",".join(stdEx),))   
                try:    runOptions.config.external_modules.extend(stdEx)
                except: runOptions.config.external_modules = stdEx
    
        results = OpyResults()
        results.obfuscatedFiles   = self.obfuscatedFileDict
        results.obfuscatedIds     = self.obfuscatedWordDict   
        results.clearTextIds      = self.skipWordSet
        results.obfuscatedImports = _toCleanStrList(
            self._parser.obfuscatedImports )
        results.clearTextImports  = _toCleanStrList(
             self._parser.clearTextImports )
        results.maskedImports     = self._parser.maskedImports
        results.clearTextPublic   = self.skippedPublicSet        
        results.obfuscatedMods    = _toCleanStrList(
            self._parser.obfuscatedMods )
        results.clearTextMods    = _toCleanStrList(
            self._parser.clearTextMods )    
        results.toClearTextMods   = _toCleanStrList(
            self._parser.toClearTextMods )
        results.toClearTextIds    = _toCleanStrList(
            self._parser.toClearTextIds )
        
        if DEBUG_LEVEL > 0 or isVerbose: 
            print ('>>> Obfuscation Summary:')                
            print ('Target Root Directory: {0}'.format(self.targetRootDirectory))
            print ('Obfuscated files: {0}'.format(len(results.obfuscatedFiles)))
            print ('Obfuscated identifiers: {0}'.format(len(self.obfuscatedWordDict)))
            #print ('Clear text identifiers: {0}'.format(len(self.skipWordSet)))
            print ('Obfuscated imports: {0}'.format(len(results.obfuscatedImports)))     
            print ('Clear text imports: {0}'.format(len(results.clearTextImports)))
            print ('Masked Imports: {0}'.format(len(results.maskedImports)))
            print ('Obfuscated module imports: {0}'.format(len(results.obfuscatedMods)))        
            print ('Clear text module imports: {0}'.format(len(results.clearTextMods)))
            print ('Clear text public identifiers: {0}'.format(len(self.skippedPublicSet)))
            print ('To clear text mods: {0}'.format(len(results.toClearTextMods)))
            print ('To clear text ids: {0}'.format(len(results.toClearTextIds)))        
            print ('')
            print ('>>> Obfuscation Details:')            
            print ('Obfuscated files: {0}'.format(results.obfuscatedFiles))
            print ('Obfuscated identifiers: {0}'.format(self.obfuscatedWordDict))
            #print ('Clear text identifiers: {0}'.format(self.skipWordSet))
            print ('Obfuscated imports: {0}'.format(results.obfuscatedImports))     
            print ('Clear text imports: {0}'.format(results.clearTextImports))
            print ('Masked Imports: {0}'.format(results.maskedImports))
            print ('Obfuscated module imports: {0}'.format(results.obfuscatedMods))
            print ('Clear text module imports: {0}'.format(results.clearTextMods))        
            print ('Clear text public identifiers: {0}'.format(self.skippedPublicSet))
            print ('To clear text mods: {0}'.format(results.toClearTextMods))
            print ('To clear text ids: {0}'.format(results.toClearTextIds))        
            print ('')    
            
        return results
    
    def __fetchStandardExclusions( self ):
        filePath = os.path.join(os.path.dirname(__file__),
                                 'standard_exclusions.txt')
        with codecs.open(filePath, 'r', 'utf-8') as f:
            lines = f.read().split('\n')
        cleanLines = [ l.strip() for l in lines if len(l.strip()) > 0 ]    
        self.standardExclusions = _toCleanStrList(cleanLines)
