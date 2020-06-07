from six import PY2
if PY2 : import __builtin__  # @UnresolvedImport
else   : import builtins   

# File objects are built-in, but aren't found as in the builtins import
# so the file method names e.g. write(), flush(), etc. aren't known that way
# Explicitly including the standard io module will collect those missing names.    
_OTHER_BUILTIN_MODS = [ 'io' ]   

class Inspector: 
    
    def __init__( self, mods, plainMarker, isVerbose=False ):
        self.isVerbose   = isVerbose
        self.plainMarker = plainMarker    
        self.publicIds   = set()
        
        self.__modObjs = set()
        self._extractIds( __builtin__ if PY2 else builtins )
        try:    mods.extend( _OTHER_BUILTIN_MODS )
        except: mods = _OTHER_BUILTIN_MODS     
        self._extractIds( _ModAttribCollector( mods, plainMarker, isVerbose ) )
                 
    def _extractIds( self, obj ):
        if obj in self.__modObjs: return
        else: self.__modObjs.update( [obj] )
    
        try   : attribs = list( obj.__dict__ )
        except: attribs = []
        
        try:
            funcParmIds = list( obj.func_code.co_varnames if PY2 else 
                                obj.__code__.co_varnames )
        except: funcParmIds = []
        
        # Split module name chunks that were joined by placeholder    
        attribIds = (self.plainMarker.join( attribs )).split(self.plainMarker)  
        
        # Entries both starting and ending with __ are skipped 
        # anyhow by the identifier regex, not including them here saves time
        newIds = set([ entry for entry in (funcParmIds + attribIds) 
            if not( entry.startswith('__') and entry.endswith('__') ) ])
        
        self.publicIds.update( newIds )
        
        subAttribs = [ getattr( obj, attrib ) for attrib in attribs ]
        for subAttrib in subAttribs: 
            try   : self._extractIds( subAttrib )
            except: pass

class _ModAttribCollector:

    def __init__( self, mods, plainMarker, isVerbose=False ):
        for mod in mods:
            # Replace . in module name by placeholder to get attribute name
            attrib = mod.replace( '.', plainMarker )              
            try:
                exec (
                    '''
import {0} as modObj
                    '''.format( mod ),
                    globals ()
                )
                setattr( self, attrib, modObj )  # @UndefinedVariable
            except Exception as e:
                if isVerbose: print( e )
                # So at least the attribute name will be available
                setattr( self, attrib, None )  
                if isVerbose: 
                    print( "Warning: could not inspect module %s" % (mod,) )

# Basic Unit Tests 
# -----------------------------------------------------------------------------
if __name__ == '__main__':   
    print( Inspector( ['os','sys','re','io'], '__opy__', True ).publicIds )
