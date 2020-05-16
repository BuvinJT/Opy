import re
import ast
import six 
import os.path
import sys
import collections
import inspect    # @UnusedImport
from _ast import Or

DEBUG=True

NEWLINE      = '\n'
SPACE        = ' '    
TAB          = '\t'
CONTINUATION = "\\"

IDENTIFIER_REGEX     = r'\b{0}\b'
IDENTIFIER_DOT_REGEX = r'\b{0}\.\b'

MEMBER_DELIM = SUB_MOD_DELIM = '.'
MAGIC_PREFFIX = MAGIC_SUFFIX = PRIVATE_PREFIX = '__'
        
ALIAS_TEMPLATE     = "alias_%d"  
SET_ALIAS_TEMPLATE = "%s as %s"

CONTINUED_TEMPLATE = "%s%s%s"
LONG_LINE_TEMPLATE = "%s%s"

__AST_ERR_TMPT = "\nCannot parse file: %s\n"
                
__IMPORT_TMPLT       = "import %s"
__FROM_IMPORT_TMPLT  = "from %s import %s"
__IS_MOD_TMPLT       = "inspect.ismodule( %s )"
__GET_MOD_PATH_TMPLT = "inspect.getfile( %s )"

__DEFAULT_OBF_EXTS = ['py','pyx']

class __PositiveException( Exception ): pass

def __stdErr( msg ):
    sys.stderr.write( msg )
    sys.stderr.flush()

# -----------------------------------------------------------------------------
obfuscatedImports   = set()
clearTextModImports    = set()
clearTextMemberImports = set()
maskedIdentifiers      = {}

def _reset():
    global obfuscatedImports, clearTextModImports, clearTextMemberImports, \
        maskedIdentifiers    
    obfuscatedImports   = set()
    clearTextModImports    = set()
    clearTextMemberImports = set()
    maskedIdentifiers      = {}

# -----------------------------------------------------------------------------
__ANALIZE_MODE, __MASK_MODE, __REPLACE_MODE = tuple(range(3))

def analyzeImports( fileContent, fileName=None, clearTextMods=[], 
                    obfuscateExts=__DEFAULT_OBF_EXTS ):
    __parseImports( fileContent, __ANALIZE_MODE, fileName, clearTextMods,
                    obfuscateExts=obfuscateExts )

def injectAliases( fileContent, fileName=None, clearTextMods=[],
                   obfuscateExts=__DEFAULT_OBF_EXTS ):
    return __parseImports( fileContent, __MASK_MODE, fileName, clearTextMods,
                           obfuscateExts=obfuscateExts )

def replaceModNames( fileContent, fileName=None, replacements={},
                     obfuscateExts=__DEFAULT_OBF_EXTS ):
    return __parseImports( fileContent, __REPLACE_MODE, fileName, 
                           replacements=replacements,
                           obfuscateExts=obfuscateExts )

def __parseImports( fileContent, mode, fileName, 
                    clearTextNames=[], replacements={},
                    obfuscateExts=__DEFAULT_OBF_EXTS ):    

    __parseImports.Import = collections.namedtuple(
            "Import", [ "module", "name", "alias", "lineno",
                        "real_mod", "real_mbr", "real_path" ] ) 

    def main( fileContent, mode, fileName, 
              clearTextNames, replacements,
              obfuscateExts ):

        if DEBUG:
            print()
            print(">>> PARSING: ", fileName)
    
        # Eliminate line continuations right off the bat!
        # This helps ease all subsequent operations to some degree,
        # and is somewhat beneficial to obfuscation itself, in that it
        # makes the code more difficult to read if it runs off the screen 
        fileContent = NEWLINE.join( __toLines( 
            fileContent, combineContinued=True ) )       
    
        # perform the fundamental parsing process
        try: importDetails = __catalogImports( fileContent, clearTextNames,
                                               obfuscateExts )   
        except Exception as e:
            __stdErr( __AST_ERR_TMPT % (fileName,) )
            __stdErr( repr(e) )
            return None if mode == __ANALIZE_MODE else fileContent
        
        if DEBUG:
            print()
            print( fileContent )
            print()
            print( ">>> PARSING RESULTS" )
            print( importDetails )
            print()

        # don't manipulate the source        
        if mode == __ANALIZE_MODE : return None
        
        # start manipulating the source
        lines = __toLines( fileContent )       
        if mode==__MASK_MODE :
            __assignAliasesToImports( lines, importDetails ) 
            __replaceIdentifiers( lines, importDetails )
        elif mode == __REPLACE_MODE: 
            __replaceModNames( lines, importDetails, replacements )

        # return the revised source  
        revisedContent = NEWLINE.join( lines )
        if DEBUG:
            print()
            print(revisedContent)
            print()                                    
        return revisedContent 

    def __catalogImports( fileContent, clearTextNames,
                          obfuscateExts ):
        if DEBUG: print("\n>>> Cataloging imports...\n")
        global obfuscatedImports, clearTextModImports, clearTextMemberImports 
        # get the entire parsed results in single shot
        details = [ imp for imp in __yieldImport( fileContent ) ]                
        # catalog the results
        for d in details:           
            mod    = __detailToImportMod(  d )
            name   = __detailToImportName( d )
            srcExt = fileExtension( d.real_path )
            if( d.real_mod in clearTextNames or
                (srcExt is not None and 
                 srcExt not in obfuscateExts) ):
                clearTextModImports.add( d.real_mod )
                if len(name) > 0 and name != d.real_mod: 
                    clearTextMemberImports.add( name )                        
            else :                     
                if mod: obfuscatedImports.add( mod )
                if name: obfuscatedImports.add( name )                        
                
        return details
        
    # "GENERATOR" function, to be called in a loop
    # Returns a detailed accounting of parsed results
    # See: https://stackoverflow.com/a/9049549/3220983
    def __yieldImport( fileContent ):
        def isMod( modName ):
            try: 
                exec( __IMPORT_TMPLT % (modName,) ) 
                return eval( __IS_MOD_TMPLT % (modName,) )
            except: return False    

        def modPath( modName ):
            try: 
                exec( __IMPORT_TMPLT % (modName,) ) 
                return eval( __GET_MOD_PATH_TMPLT % (modName,) )
            except: return None     
                            
        def isChild( moduleName, childName ):
            try:
                exec( __FROM_IMPORT_TMPLT % (moduleName, childName) )
                return True
            except: return False
            
        root = ast.parse( fileContent )           
        for node in ast.walk( root ):
            #print(node)
            if   isinstance( node, ast.Import ): module = []
            elif isinstance( node, ast.ImportFrom ):  
                module = node.module.split( SUB_MOD_DELIM )
            else: continue        
            for n in node.names:                
                name = n.name.split( MEMBER_DELIM )
                real_path = None                
                real_mod = None
                real_mbr = None
                impParts = module + name
                for i in range(len( impParts )):
                    # start with the whole thing, then chop off more from 
                    # the end each time                                  
                    head = ( MEMBER_DELIM.join( impParts ) if i==0 else
                             MEMBER_DELIM.join( impParts[:-i] ) )
                    # start with nothing, then collect more from the end each time
                    tail = "" if i==0 else MEMBER_DELIM.join( impParts[-i:] )
                    if isMod( head ):
                        real_mod = head             
                        real_path = modPath( real_mod )
                        if isChild( real_mod, tail ): real_mbr = tail                        
                        break
                yield __parseImports.Import( 
                    module, name, n.asname, node.lineno,
                    real_mod, real_mbr, real_path )
                # Execution resumes here (with the locals preserved!) 
                # on the next call to this function per the magic of "yield"...               
                
    def __assignAliasesToImports( lines, importDetails, modFilter=set() ):
        """ modifies lines by reference
            conditionally modifies global maskedIdentifiers, 
            pass a modFilter to use this in "local mode"   
        """
        if DEBUG: print("\n>>> Assigning aliases to imports...\n")
        global maskedIdentifiers
        newAliases={}        
        useGlobal = len(modFilter)==0
        if useGlobal: modFilter = clearTextModImports
        for d in importDetails :          
            if d.alias : continue  
            mod = __detailToImportMod( d )
            if mod in modFilter : 
                imp      = MEMBER_DELIM.join( d.name ) 
                idx      = d.lineno-1        
                line     = lines[ idx ]                             
                try:    
                    if useGlobal: alias = maskedIdentifiers[imp]
                    else: raise __PositiveException()
                except: alias = ALIAS_TEMPLATE % (len(maskedIdentifiers),)
                setAlias = SET_ALIAS_TEMPLATE % ( imp, alias )
                regEx    = re.compile( IDENTIFIER_REGEX.format( imp ) )                                        
                revLine = regEx.sub( setAlias, line )
                if DEBUG:
                    print( "line %d: %s aliased as %s" % 
                           (d.lineno, imp, alias) )
                    print( "original line: ", line )
                    print( "revised line:  ", revLine)
                    print()
                lines[ idx ] = revLine
                newAliases[ imp ] = alias
                if useGlobal: maskedIdentifiers[ imp ] = alias
        return newAliases
                   
    def __replaceIdentifiers( lines, importDetails, replacements={}, 
                              includeImportLines=False ): 
        """ modifies lines by reference
            uses global maskedIdentifiers by default,
            else the "override" aliases parameter                 
        """
        if DEBUG: print("\n>>> Replacing identifiers...\n") 
        if len(replacements)==0: replacements=maskedIdentifiers
        nakedRegExs={}
        trailingDotRegExs={}        
        for oldName in replacements :
            nakedRegExs[oldName] = ( 
                re.compile( IDENTIFIER_REGEX.format( oldName ) ) ) 
            trailingDotRegExs[oldName] = ( 
                re.compile( IDENTIFIER_DOT_REGEX.format( oldName ) ) )            
        ignoreLineNos = ( [] if includeImportLines else 
                          [ d.lineno for d in importDetails ] )
        for idx, line in enumerate( lines ):
            lineno = idx+1            
            if lineno not in ignoreLineNos:
                for oldName, newName in six.iteritems( replacements ):
                    if DEBUG: original=line
                    line = nakedRegExs[oldName].sub( newName, line )
                    line = trailingDotRegExs[oldName].sub( newName + MEMBER_DELIM, line )
                    if DEBUG and original!=line:
                        print( "line %d: replaced %s with %s" %
                                (lineno, oldName, newName) )
                        print( "original line: ", original )
                        print( "revised line:  ", line )
                        print()
                    lines[idx] = line

    def __replaceModNames( lines, importDetails, replacements ):
        """ modifies lines by reference """
        if DEBUG: print("\n>>> Replacing module names...\n")
        validated={}
        for oldName, newName in six.iteritems( replacements ):         
            for d in importDetails :          
                mod = __detailToImportMod( d )
                if mod == oldName :
                    validated[oldName]=newName               
                    break      
        __replaceIdentifiers( lines, importDetails, 
            replacements=validated, includeImportLines=True )             

    def __detailToImportMod( d ):
        return MEMBER_DELIM.join( d.module ) if len(d.module) > 0 else "" 

    def __detailToImportName( d ):
        return MEMBER_DELIM.join( d.name ) if len(d.name) > 0 else "" 
     
    def __toLines( fileContent, combineContinued=False ):
        lines = fileContent.split( NEWLINE )
        if combineContinued :
            # this does not attempt to compress white space purposefully!
            revLines = []
            longLine = ""
            for l in lines:
                if l.rstrip().endswith( CONTINUATION ):
                    longLine = ( CONTINUED_TEMPLATE % 
                        (longLine, l.rstrip()[:-1], SPACE ) )
                else :            
                    longLine = LONG_LINE_TEMPLATE % (longLine, l)
                    revLines.append( longLine )
                    longLine = ""
            lines = revLines
        return lines 

    return main( fileContent, mode, fileName, 
                 clearTextNames, replacements, obfuscateExts )

# ----------------------------------------------------------------------------- 
def findPublicIdentifiers( fileContent ):

    def main():
        publicIds=set()
        root = ast.parse( fileContent )    
        publicIds.update( __findAstPublicNameAssigns( root ) )
        publicIds.update( __findAstPublicFuncsClassesAttribs( root ) )
        return publicIds

    # recursive
    def __findAstPublicFuncsClassesAttribs( node ):
        publicNodes = set()    
        for child in ast.iter_child_nodes( node ):       
            if( isinstance( child, ast.FunctionDef ) or 
                isinstance( child, ast.ClassDef ) ):            
                if __isPrivatePrefix( child.name ) : continue                        
                publicNodes.add( child.name ) 
                publicNodes.update( __findAstPublicAttribAssigns( child ) )            
                publicNodes.update( __findAstPublicFuncsClassesAttribs( child ) )
        return publicNodes
    
    def __findAstPublicAttribAssigns( node ):
        publicNodes = set()    
        for child in ast.iter_child_nodes( node ):
            if isinstance( child, ast.Assign ):
                for target in child.targets :
                    if isinstance( target, ast.Attribute ) :        
                        if not __isPrivatePrefix( target.attr ):    
                            publicNodes.add( target.attr )
        return publicNodes
    
    def __findAstPublicNameAssigns( node ):
        publicNodes = []    
        for child in ast.iter_child_nodes( node ):
            if isinstance( child, ast.Assign ):
                for target in child.targets :
                    if isinstance( target, ast.Name ) :
                        if not __isPrivatePrefix( target.id ):    
                            publicNodes.append( target.id )
        return publicNodes
    
    def __isPrivatePrefix( identifier ):
        return ( identifier.startswith( PRIVATE_PREFIX )
                 and not identifier.endswith( MAGIC_SUFFIX ) )

    return main()

# -----------------------------------------------------------------------------

def baseFileName( path ): return os.path.basename( path )

def rootFileName( path ): return os.path.splitext( baseFileName( path ) )[0]

def fileExtension( p ):     
    try: return os.path.splitext( p )[1][1:] # no leading .
    except: return None
  
def rootImportName( modName ): return modName.split( SUB_MOD_DELIM )[0]
   
def toPackageName( relPath ): 
    return relPath.replace( "/", SUB_MOD_DELIM ).replace( "\\" , SUB_MOD_DELIM)

def toProjectSubPackage( relPath ):    
    names = toPackageName( relPath ).split(SUB_MOD_DELIM)
    if len(names)==1: return None
    return names[0]

# Basic Unit Tests 
# -----------------------------------------------------------------------------
if __name__ == '__main__': 
    fileContent=(
"""
import ast 
from os import system, sep as PATH_DELIM, \
    remove as removeFile, \
    fdopen, getcwd, chdir, walk, environ, devnull
from os.path import exists
    
x = devnull
_y = exists    
__z = ast.Import

def public(): return x
def _protected(): return _y
def __private(): return __z
""")
    
    analyzeImports( fileContent, clearTextMods=['ast','os'] )
    print( "obfuscated", obfuscatedImports )
    print( "clearTextMod", clearTextModImports )
    print( "clearTextMbr", clearTextMemberImports )
    print( "masked", maskedIdentifiers )
    
    print( injectAliases( fileContent, clearTextMods=["ast","os","os.path"]  ) )
    print( "masked", maskedIdentifiers )
        
    print( replaceModNames( fileContent, replacements={
          "ast":"AST"
        #, "os.path":"OS.PATH"      
        , "os":"OS"      
        , "path":"this should not appear!"       
        , "system":"this should not appear!"      
        , "fake":"this should not appear!"
        , "PATH_DELIM":"this should not appear either!"    
    }) )
    
    print( "PublicIdentifiers",
           findPublicIdentifiers( fileContent ) )
        
