import io
import six

class OpyConfig :
    """
    See opy_config.txt for details on these settings.
    """    
    def __init__( self ) :    
        self.obfuscate_strings = True        
        self.obfuscated_name_tail = '_opy_'  
        self.plain_marker = '_opy_'          
        self.pep8_comments = False
        self.source_extensions = [ 'py', 'pyx' ]          
        self.skip_extensions = [ 
             'pyc'
            ,'txt'
            ,'project'      # Eclipse/PyDev IDE files/folders
            ,'pydevproject'
            ,'settings' 
        ] 
        self.skip_path_fragments = [ 
             'opy_config.txt'
            ,'opy_config.py'
            ,'standard_exclusions.txt' 
        ]
        self.apply_standard_exclusions = True
        self.external_modules = []
        self.replacement_modules = {}
        self.plain_files = []
        self.plain_names = []
        self.mask_external_modules = True
        self.skip_public = False
        self.subset_files = []
        self.dry_run = False
        self.prepped_only = False        

    def __str__( self ):
        # TODO : rewrite this in a more clean/clever manner... 
        text = ( 
              "obfuscate_strings = %s\n" % str(self.obfuscate_strings)         
            + "obfuscated_name_tail = '%s'\n" % self.obfuscated_name_tail
            + "plain_marker = '%s'\n" % self.plain_marker
            + "pep8_comments = %s\n" % str(self.pep8_comments)
            + "mask_external_modules = %s\n" % str(self.mask_external_modules)
            + "apply_standard_exclusions = %s\n" % str(self.apply_standard_exclusions)
            + "skip_public = %s\n" % str(self.skip_public)
            + "dry_run = %s\n" % str(self.dry_run)
            + "prepped_only = %s\n" % str(self.prepped_only)            
        )
        text += "source_extensions ='''\n"
        for item in self.source_extensions : text += "%s\n" % item
        text += "'''\n"
        text += "skip_extensions ='''\n"
        for item in self.skip_extensions : text += "%s\n" % item
        text += "'''\n"
        text += "skip_path_fragments ='''\n"
        for item in self.skip_path_fragments : text += "%s\n" % item
        text += "'''\n"
        text += "external_modules ='''\n"
        for item in self.external_modules : text += "%s\n" % item
        text += "'''\n"
        text += "replacement_modules ='''\n"
        for k,v in six.iteritems( self.replacement_modules ) : 
            text += "%s:%s\n" % (k,v)
        text += "'''\n"
        text += "plain_files ='''\n"
        for item in self.plain_files : text += "%s\n" % item
        text += "'''\n"
        text += "plain_names ='''\n"
        for item in self.plain_names : text += "%s\n" % item
        text += "'''\n"        
        text += "subset_files ='''\n"
        for item in self.subset_files : text += "%s\n" % item
        text += "'''\n"
        return text

    def toVirtualFile( self ):         
        return io.StringIO( 
            str(self).decode('utf-8') if six.PY2 else str(self) )         
