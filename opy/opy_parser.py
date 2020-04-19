import re
import ast
import six 
import os
import collections

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

class __PositiveException( Exception ): pass

# -----------------------------------------------------------------------------
obfuscatedModImports = set()
clearTextModImports  = set()
maskedIdentifiers    = {}

def _reset():
    global obfuscatedModImports, clearTextModImports, maskedIdentifiers    
    global _modAliases, _mbrAliases, _modReplace
    obfuscatedModImports = set()
    clearTextModImports  = set()
    maskedIdentifiers    = {}

# -----------------------------------------------------------------------------
__ANALIZE_MODE, __MASK_MODE, __REPLACE_MODE = tuple(range(3))

def analyzeImports( fileContent, clearTextMods=[] ):
    __parseImports( fileContent, __ANALIZE_MODE, clearTextMods )

def injectAliases( fileContent, clearTextMods=[] ):
    return __parseImports( fileContent, __MASK_MODE, clearTextMods )

def replaceModNames( fileContent, replacements={} ):
    return __parseImports( fileContent, __REPLACE_MODE, replacements=replacements )

def __parseImports( fileContent, mode, 
                    clearTextNames=[], replacements={} ):    

    __parseImports.Import = collections.namedtuple(
            "Import", [ "module", "name", "alias", "lineno" ] ) 

    def main( fileContent, mode, clearTextNames, replacements ):
    
        importDetails = __catalogImports( fileContent, clearTextNames )
        #print( importDetails )
        if mode == __ANALIZE_MODE : return None
        
        lines = __toLines( fileContent, combineContinued=True )       
        if mode==__MASK_MODE :
            __assignAliasesToImports( lines, importDetails ) 
            __replaceIdentifiers( lines, importDetails )
        elif mode == __REPLACE_MODE: 
            __replaceModNames( lines, importDetails, replacements )
        return NEWLINE.join( lines )

    def __catalogImports( fileContent, clearTextNames ):
        global obfuscatedModImports, clearTextModImports
        details = [ imp for imp in __yieldImport( fileContent ) ]                
        # update (simple) global mod name sets 
        mods = [ __detailToMod( d ) for d in details ]
        for m in mods: 
            if m in clearTextNames: clearTextModImports.add(  m )
            else :                  obfuscatedModImports.add( m )        
        return details
        
    # "GENERATOR" function, to be called in a loop
    # Returns a detailed accounting of parsed results
    # See: https://stackoverflow.com/a/9049549/3220983
    def __yieldImport( fileContent ):
        root = ast.parse( fileContent )           
        for node in ast.walk( root ):
            #print(node)
            if   isinstance( node, ast.Import ): module = []
            elif isinstance( node, ast.ImportFrom ):  
                module = node.module.split( SUB_MOD_DELIM )
            else: continue        
            for n in node.names:                
                yield __parseImports.Import( 
                    module, n.name.split( MEMBER_DELIM ), n.asname, 
                    node.lineno )
                # Execution resumes here (with the locals preserved!) 
                # on the next call to this function per the magic of "yeild"...
                
    def __assignAliasesToImports( lines, importDetails, modFilter=set() ):
        """ modifies lines by referrence
            conditionally modifies global maskedIdentifiers, 
            pass a modFilter to use this in "local mode"   
        """
        global maskedIdentifiers
        newAliases={}        
        useGlobal = len(modFilter)==0
        if useGlobal: modFilter = clearTextModImports
        for d in importDetails :          
            if d.alias : continue  
            mod = __detailToMod( d )
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
                lines[ idx ] = regEx.sub( setAlias, line )  
                newAliases[ imp ] = alias
                if useGlobal: maskedIdentifiers[ imp ] = alias
        return newAliases
                   
    def __replaceIdentifiers( lines, importDetails, replacements={}, 
                              includeImportLines=False ): 
        """ modifies lines by referrence
            uses global maskedIdentifiers by default,
            else the "override" aliases parameter                 
        """
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
                    line = nakedRegExs[oldName].sub( newName, line )
                    line = trailingDotRegExs[oldName].sub( newName + MEMBER_DELIM, line )
                    lines[idx] = line

    def __replaceModNames( lines, importDetails, replacements ):
        """ modifies lines by referrence """
        validated={}
        for oldName, newName in six.iteritems( replacements ):         
            for d in importDetails :          
                mod = __detailToMod( d )
                if mod == oldName :
                    validated[oldName]=newName               
                    break      
        __replaceIdentifiers( lines, importDetails, 
            replacements=validated, includeImportLines=True )             

    def __detailToMod( d ):
        return MEMBER_DELIM.join( d.module if len(d.module) > 0 else d.name ) 
         
    def __toLines( fileContent, combineContinued=False ):
        lines = fileContent.split( NEWLINE )
        if combineContinued :
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

    return main( fileContent, mode, clearTextNames, replacements )

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

    fileContent=(
"""    
from sys import stdout
# cross environment Tkinter import    
try:    from tkinter import Tk 
except: from Tkinter import Tk
try:    from tkinter.ttk import Button 
except: from ttk import Button

def onClick(): 
    stdout.write( "Hello!\\n" )
    stdout.flush()

mainWindow = Tk()
Button( mainWindow, text="Hello TKinkter", command=onClick ).grid()
mainWindow.mainloop()
""")    
    
    analyzeImports( fileContent, clearTextMods=[] )
    print( "obfuscated", obfuscatedModImports )
    print( "clearText", clearTextModImports )
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
        
