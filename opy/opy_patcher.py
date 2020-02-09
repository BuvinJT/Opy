import six

DEFAULT_ENCODING = "utf-8"

_PLACEHOLDER_PREFIX = "OBF__"
_PLACEHOLDER_SUFFIX = "__OBF"
_NEWLINE="\n"

class OpyFile:
    def __init__( self, path, opyResults, encoding=DEFAULT_ENCODING ):
        self.__path = path
        self.__results = opyResults 
        self.__encoding = encoding        
        f = ( open( self.__path, 'r' ) if six.PY2 else 
              open( self.__path, 'r', encoding=self.__encoding ) )
        self.__lines = f.readlines()
        f.close() 
            
    def lines( self, isNumbered=False ):
        if isNumbered: 
            return [ ((i+1), ln) for i, ln in enumerate( self.__lines ) ]
        return self.__lines

    def line( self, lineNo ): return self.__lines[ lineNo-1 ]
    
    def setLine( self, lineNo, line ): 
        self.__lines[ lineNo-1 ] = self.__ensureLineEnding( 
            self.__resolvePlaceholders( line ) )
    
    def replaceInLine( self, lineNo, old, new ):        
        self.setLine( lineNo, self.line( lineNo ).replace( 
                self.__resolvePlaceholders( old ), 
                self.__resolvePlaceholders( new ) ) ) 

    def update( self ):
        f = ( open( self.__path, 'w' ) if six.PY2 else 
              open( self.__path, 'w', encoding=self.__encoding ) )
        f.writelines( self.__lines )
        f.close() 
            
    def __ensureLineEnding( self, line ):
        return line if line.endswith(_NEWLINE) else "%s%s" % (line,_NEWLINE)
        
    def __resolvePlaceholders( self, inText ):
        outText = inText
        if _PLACEHOLDER_PREFIX in inText: 
            for clr, obf in six.iteritems( self.__results.obfuscatedIds ):
                outText = outText.replace( obfuscatedId( clr ), obf )
            for clr, obf in six.iteritems( self.__results.maskedIds ):
                outText = outText.replace( obfuscatedId( clr ), obf )                
        return outText
        
# -----------------------------------------------------------------------------
# High-level / Convenience functions 

def patch( path, opyResults, patches=[] ):
    f = OpyFile( path, opyResults )
    for p in patches :
        if len(p)==2:
            lineNo, line = p
            f.setLine( lineNo, line ) 
        elif len(p)==3:
            lineNo, old, new = p
            f.replaceInLine( lineNo, old, new )     
    f.update()

def setLine( path, opyResults, lineNo, line ):
    f = OpyFile( path, opyResults )
    f.setLine( lineNo, line ) 
    f.update()

def replaceInLine( path, opyResults, lineNo, old, new ):
    f = OpyFile( path, opyResults )
    f.replaceInLine( lineNo, old, new  ) 
    f.update()
    
def obfuscatedId( clearIdentifier ): 
    return "%s%s%s" % (
        _PLACEHOLDER_PREFIX, clearIdentifier, _PLACEHOLDER_SUFFIX )
                