	.. figure:: http://www.qquick.org/opy.jpg
		:alt: Image of Phaistos Disc
		
		**The famous Phaistos Disc from Crete, obfuscation unbroken after thousands of years.**

Opy will obfuscate your extensive, real world, multi module Python source code for free!
And YOU choose per project what to obfuscate and what not, by editing the config file:

- You can recursively exclude all identifiers of certain modules from obfuscation.
- You can exclude human readable configuration files containing Python code.
- You can use getattr, setattr, exec and eval by excluding the identifiers they use.
- You can even obfuscate module file names and string literals.
- You can run your obfuscated code from any platform.

-------------------------------------------------------

Bugs fixed:

- utf-8 forced for setup (issue 25)
- pep8_comments config setting now defaults to True, making it possible for opy to obfuscate itself as a test
- erroneous copying of directories above project root fixed
- name of __init__.py files now left unaltered by default
- module directories renamed appropriately
- .pyc files not copied to target directory tree any more. N.B. Delete them from your existing target trees since they break obfuscation!
- from __future__ import now handled correctly

**Bug reports and feature requests are most welcome and will be taken under serious consideration on a non-committal basis**

-------------------------------------------------------

What's new:

- implementation of Opy as an import / library provided
- replacement_modules *BETA* feature added 
- mask_external_modules *BETA* feature added
- skip_public *BETA* feature added
- added dry_run and prepped_only options
- added analyze() function to library to assist with the identification
  of obfuscated files, words, imports etc.
- added class OpyFile for applying "quick patches" to obfuscated files
  (applicable when using Opy as a library)
- line continuations combined into single lines

- possibility to specify input dir, output dir and config file documented
- skip_path_fragments implemented
- explanatory comments in config file made more clear
- reasonable defaults provided for all configuration settings
- -h an --help added in addition to ?
- pep8_comments option added
- support for obfuscation of names starting with __ added
- license changed from QQuickLicense to Apache 2.0
- empty lines are removed

-------------------------------------------------------

Raw/Primitive Installation:

- Download and unzip Opy into an arbitrary directory of your computer.
- You only need the files opy.py and opy_config.txt. They are in the opy subdirectory of your unzipped Opy version.
- Put opy.py or a script to launch it in the path of your OS, or simply copy opy.py to the top directory of your project.

Use:

- For safety, backup your source code and valuable data to an off-line medium.
- Put a copy of opy_config.txt in the top directory of your project.
- Adapt it to your needs according to the remarks in opy_config.txt.
- This file only contains plain Python and is exec'ed, so you can do anything clever in it.
- Open a command window, go to the top directory of your project and run opy.py from there.
- If the top directory of your project is e.g. ../work/project1 then the obfuscation result wil be in ../work/project1_opy.
- Further adapt opy_config.txt until you're satisfied with the result.
- Type 'opy ?' or 'python opy.py ?' (without the quotes) on the command line to display a help text and a reference to the licence.

-------------------------------------------------------

Library Installation:

- Download and unzip Opy into an arbitrary directory of your computer.
- Open a command window, go to the directory where you placed the download and execute: 

	pip install .	
	(Don't miss the period at the end!)
	
	Or if you don't have pip installed:
	
	python setup.py install
	
Use:

- Create a python script to obfuscate your project OR to provide a more robust packaging process, with the obfuscation acting as one "stage" within that.
- Import the obfuscate function from the opy module and then call it as shown below:

from opy import obfuscate
obfuscate( sourceRootDirectory = scrDir
		 , targetRootDirectory = trgDir
	     , configFilePath      = cfgFile )

Note that each of the arguments are optional. If omitting them, the utility runs in the default manner using relative / default paths. 
		 
-------------------------------------------------------
		 
Important remark:

- Obfuscate your Python code only when strictly needed. Freedom is one of the main benefits of the Python community. In line with this the source of Opy is not obfuscated.

Example of obfuscated code: ::

	import Tkinter as l1111lll1
	import tkFileDialog
	import os

	from util import *

	from l1l111l import *
	from l1llll1 import *

	l1l1lll1l1l1 = 35
	l1l11l1ll1 = 16

	class l111l1l111l (l1111lll1.Frame, l1lll11ll1):
		def __init__ (self, parent):	
			l1111lll1.Frame.__init__ (self, parent)
			l1lll11ll1.__init__ (self)
			
			self.l1l1ll11llll = []
			
			self.l1l1ll11llll.append (l1111lll1.Frame (self, width = l1l1llll1111, height = l1l11l111l))
			self.l1l1ll11llll [-1] .pack (side = l1llll (u'ࡶࡲࡴࠬ'))
			
			self.l1l1ll1ll11l = l1111lll1.LabelFrame (self, text = l1llll (u'ࡒࡦࡵࡤࡱࡵࡲࡩ࡯ࡩ࠸'), padx = 5)
			self.l1l1ll1ll11l.pack (side = l1llll (u'ࡺ࡯ࡱࠢ'), fill = l1llll (u'ࡦࡴࡺࡨࠧ'), expand = True)
		
-------------------------------------------------------
		
Known limitations:

- A comment after a string literal should be preceded by white space.
- A ' or " inside a string literal should be escaped with \\ rather then doubled.
- If the pep8_comments option is False (the default), a # in a string literal can only be used at the start, so use 'p''#''r' rather than 'p#r'.
- If the pep8_comments option is set to True, however, only a <blank><blank>#<blank> cannot be used in the middle or at the end of a string literal
- Obfuscation of string literals is unsuitable for sensitive information since it can be trivially broken
- No renaming back door support for methods starting with __ (non-overridable methods, also known as private methods)

- Some keyword arguments may have issues??? (further details tbd...)

* "Skip Public" (beta feature) has some weaknesses.
	As with other features, this can encounter "name collisions". In this case,
	it can end up leaving some identifiers in clear text that you wanted to be 
	obfuscated.  Such should NOT cause operational errors at least.  

* "Masking" (beta feature) fails under a few conditions. 
	A) It is not yet respectful of scoping details.
	B) It is not yet able to parse imports statements which are not on
	   their own lines (e.g. one-line conditional imports, semicolon 
	   delimited multi-statement import lines... ).  
 	C) It can cause name collisions, as it is not yet "context aware".
 	D) There is a problem in the handling of masking module members with 
 	   names that are otherwise set to be preserved in clear text. See
 	   examples. 
    The solution to all such problems is to assign YOUR OWN ALIASES for those use 
    cases which the utility is not yet able to resolve. See the "bugs" directory
    for examples of known problems (which will all hopefully be resolved!). 

	Masking name collision example 1:
	
	    from os.path import join
	    someString = ','.join( someList )
	
	    Becomes:
	
	    from os.path import join as alias_0
	    someString = ','.alias_0( someList )
	
	    (that's a problem because join is a string function too!)
	
	Pre-Obfuscated solution:
	
	    from os.path import join as joinPath
	    someString = ','.join( someList )
	
	    This will work because os.path.join now
        has a manually assigned alias, so the auto alias
        mechanism simply will not be employed for it. 
		Obfuscation of "joinPath" will work without issue.
	
	Masking name collision example 2:
	
	    from datetime import datetime 
	    def processObj( obj ):
	       if isinstance( obj, datetime ): print "Date/Time!"
	       
	    Becomes:
	
	    from datetime import datetime as alias_0
	    def processObj( obj ):
	        if isinstance( obj, datetime ): print "Date/Time!"
	
	    This is the opposite problem as example 1. Note the 
	    type evaluation line did not apply the alias! Why?
	    Because "datetime" is a module name being preserved 
	    in clear text, and thus ignored by the current alias 
	    applying algorithm.
	
	Pre-Obfuscated solution:
	
	    from datetime import datetime as dt
	    def processObj( obj ):
	        if isinstance( obj, dt ): print "Date/Time!"
        
        This will work because datetime.datetime now
        has a manually assigned alias, so the auto alias
        mechanism simply will not be employed for it. 
		Obfuscation of "dt" will work without issue.
            
-------------------------------------------------------

			
That's it, enjoy!

Jacques de Hooge

jacques.de.hooge@qquick.org

Other packages you might like:

- Lean and mean Python to JavaScript transpiler featuring multiple inheritance https://pypi.python.org/pypi/Transcrypt
- Python PLC simulator with Arduino code generation https://pypi.python.org/pypi/SimPyLC
- Event driven evaluation nodes https://pypi.python.org/pypi/Eden
- A lightweight Python course taking beginners seriously (under construction): https://pypi.python.org/pypi/LightOn
