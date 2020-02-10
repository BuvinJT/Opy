	.. figure:: http://www.qquick.org/opy.jpg
		:alt: Image of Phaistos Disc
		
		**The famous Phaistos Disc from Crete, obfuscation unbroken after thousands of years.**

Opy will obfuscate your extensive, real world, multi module Python source code for free!
You can use Opy on Python 2 or 3!
And YOU choose per project what to obfuscate and what not, by defining unique configuration:

- You can recursively exclude all identifiers of certain modules from obfuscation.
- You can exclude human readable configuration files containing Python code.
- You can use getattr, setattr, exec and eval by excluding the identifiers they use.
- You can even obfuscate module file names and string literals.
- You can run your obfuscated code from any platform.

What's new in the "Distribution Builder FORK":

- implementation of Opy as an import / library provided!!
- replacement_modules *BETA* feature added 
- mask_external_modules *BETA* feature added
- skip_public *BETA* feature added
- added dry_run and prepped_only options
- added analyze() function to library to assist with the identification
  of obfuscated files, words, imports etc.
- added class OpyFile for applying "quick patches" to obfuscated files 
- line continuations combined into single lines  

Recent bugs fixed:

- utf-8 forced for setup (issue 25)
- pep8_comments config setting now defaults to True, making it possible for opy to obfuscate itself as a test
- erroneous copying of directories above project root fixed
- name of __init__.py files now left unaltered by default
- module directories renamed appropriately
- .pyc files not copied to target directory tree any more. N.B. Delete them from your existing target trees since they break obfuscation!
- from __future__ import now handled correctly

**Bug reports and feature requests are most welcome and will be taken under serious consideration on a non-committal basis**

"Raw" Installation / Traditional Use:

- Download and unzip (or git clone) Opy into an arbitrary local directory.
- For safety, backup your source code and valuable data to an off-line medium.
- Place a COPY of the supplied opy_config.txt in the top directory of your project.
- Adapt it to your needs according to the remarks within it.
- This file only contains plain Python and is exec'ed, so you can do anything clever in it.
- Open a command window, go to the top directory of your project, and run opy.py from there. ::
	
	python [path to]/opy.py [source directory] [target directory] [config file path]
	
Note that each of the arguments are optional. If omitting them, the utility uses default values:
source directory = current work directory
target directory = directory adjacent to the source named "Opy"
config file path = <source directory>/opy_config.txt

- Further adapt opy_config.txt until you're satisfied with the result.
- Type 'opy ?' or 'python opy.py ?' (without the quotes) on the command line to display a help text and a reference to the licence.

"Bundled" Installation with "Distribution Builder":

This library comes bundled within a larger project called "`Distribution Builder <https://pypi.org/project/distbuilder/>`_".  
That provides additional features for creating and working with obfuscations (among other powerful tools).  You 
may wish to install that instead, thereby acquiring this simultaneously.  

- Assuming `pip` is installed, and on your system path, simply open a command window and execute: ::
 
	pip install distbuilder
			
- For more information you refer the `Distribution Builder Documentation <https://distribution-builder.readthedocs.io/en/latest/>`_.

Simple Pip Installation:

- Assuming *pip* is installed, and on your system path, simply open a command window and execute: :: 

	pip install opy-distbuilder

Manual Pip Installation:

- Download and unzip Opy into an arbitrary local directory.
- Open a command window, go to the directory where you placed the download and execute:  ::

	pip install .	
	
(Don't miss the period at the end!)
	
Or, if you don't have pip installed: ::
	
	python setup.py install
	
- You may then delete the original copy.  	
		
Library Use:

- Create a python script to obfuscate your project.
- Import the obfuscate function from the opy module and then call it as shown below: ::

    from opy import obfuscate, OpyConfig
    results = obfuscate( sourceRootDirectory = None
                       , targetRootDirectory = None
                       , configFilePath      = None
                       , configSettings      = None )    

Note that each of the arguments are optional. If omitting them, the utility works as described 
in "Traditional Use". In addition the traditional use, however, the library style implementation
allows you to pass an *OpyConfig* object (as the "configSettings" argument).  This object contains
attributes which are named identically to those found in the opy_config.txt file.  The only difference 
when defining them is that iterable attributes are set directly rather than indirectly via the line 
delimited lists in the external file. 

**Refer to the opy_config.txt file to find detailed descriptions for all of the configuration options.** 
Those are the key to controlling how this process is customized.

- The library may alternatively be used to "analyze" the project without actually generating any files.

This can prove useful as part of an automated script which helps to drive the obfuscation in more 
dynamic ways (the Distribution Builder library uses this function for such purposes). ::  
 
    from opy import analyze, OpyConfig
    results = analyze( sourceRootDirectory = None
                     , fileList            = []  
                     , configSettings      = OpyConfig() )    
 
- The obfuscate and analyze functions both return an "OpyResults" object, with the following attributes: ::

    results.obfuscatedFileDict
    results.obfuscatedWordList
    results.obfuscatedModImports
    results.maskedIdentifiers      
    results.skippedPublicSet       
        	 
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
		
Currently Known Bugs / Issues:

We are hoping to eliminate some of the major and/or "simple" bugs soon... 

Sorry about the formating / loose nature of this part of the documentation. These only have been quickly jotted down to provide instant help and to keep a running list of todos for the developers.
Some of these bugs are directly related to one another, but are mentioned separately to bring explicit attention to each dimension of the issue. 

- (MAJOR) Weakness: Obfuscation of string literals is unsuitable for sensitive information since it can be trivially broken. Consider adding (your own) *encryption* mechanisms for data requiring serious protection...  	

- (MAJOR) Bug: Function calls cannot use keyword arguments.  The argument keys/names become obfuscated by the caller, yet there is no resolution in the function definition.

Workaround:
A) Use positional arguments
B) Append the argument keywords to the plain_names list. 

- (MAJOR) Bug: String obfuscation of dictionary keys may break using calling functions in external modules and for external resources where such must be defined in clear text. 

Workaround:
Define the dictionaries and/or key constants in a dedicated module (for import where needed), which is then added to the plain_files list.

- Bug: The parser is not finding imports on multi-part lines, such as the below example: ::    	

	try:    from tkinter import Tk 
	except: from Tkinter import Tk
	try:    from tkinter.ttk import Button 
	except: from ttk import Button

Workaround:
	Simply break the lines apart! ::    	

	try:    
		from tkinter import Tk 
	except: 
		from Tkinter import Tk
	try:    
		from tkinter.ttk import Button 
	except: 
		from ttk import Button

- Bug: When string obfuscation is enabled, multi-line string literals which are implicitly continued without the use of an explicit '+' operator between cannot be used. 

Example, the following string would result in an error. ::

	s = (
		"This is some text and it needs to \n"
		"wrap to the next line"
	)

Known workaround: 
Explicitly add the '+' character as needed. 

- (UNRESOLVABLE?) Bug: Dynamically created object attributes cannot be referenced directly.

Example: The popular argparse module creates attributes "magically" e.g. shoen below with "foo". ::

	import argparse
	parser = argparse.ArgumentParser()
	parser.add_argument('--foo', help='foo help')
	args = parser.parse_args()
	print( args.foo )

Opy will obfuscate the '--foo' string and the .foo attribute without binding them. 

Workaround: 
A) Convert args to a dictionary ::

	args = vars(parser.parse_args())
	
or ::

	args = parser.parse_args().__dict__

Then, access the value via the the key: ::

	print( args["foo"] )
	print( args.get("foo") )

B) Access the "magic" attribute via getattr :: 

	print( getattr(args,"foo") )

- Bug: A comment after a string literal should be preceded by white space.

- Bug: If the pep8_comments option is set to True, however, only a <blank><blank>#<blank> cannot be used in the middle or at the end of a string literal

- Bug: If the pep8_comments option is False (the default), a # in a string literal can only be used at the start, so use 'p''#''r' rather than 'p#r'.

- Bug: '#' characters used in the middle of string literals cause the string to be truncated at the index of the # character.

Example: ::
 
	print("ERROR #%d: %s" % ( errno, strerr ))

Workaround: Use dynamic string substitution and resolve the # via its ascii code.  
Example: ::

	HASH = chr(35)
	print("ERROR %c%d: %s" % ( HASH, errno, strerr ))

- Bug: A ' or " inside a string literal should be escaped with \\ rather then doubled.

- Bug: No renaming back door support for methods starting with __ (non-overridable methods, also known as private methods)

- Weakness: "Skip Public" (beta feature) can produce extra deobfuscation.

As with other features, this can encounter "name collisions". In this case,
it can end up leaving some identifiers in clear text that you wanted to be 
obfuscated.  **Such should NOT cause operational errors at least.**  

- Weakness: "Masking" (beta feature) fails under a few conditions. 

A) It is not yet respectful of scoping details.
B) It is not yet able to parse imports statements which are not on their own lines (e.g. one-line conditional imports, semicolon delimited multi-statement import lines... ).  
C) It can cause name collisions, as it is not yet "context aware".
D) There is a problem in the handling of masking module members with names that are otherwise set to be preserved in clear text. See examples. 

The solution to all such problems is to assign YOUR OWN ALIASES for those use 
cases which the utility is not yet able to resolve. See the "bugs" directory
for examples of known problems (which will all hopefully be resolved!). 

**Masking name collision example 1**: ::

    from os.path import join
    someString = ','.join( someList )

Becomes: ::

    from os.path import join as alias_0
    someString = ','.alias_0( someList )

(that's a problem because join is a string function too!)

Pre-Obfuscated solution: ::

    from os.path import join as joinPath
    someString = ','.join( someList )

This will work because os.path.join now
has a manually assigned alias, so the auto alias
mechanism simply will not be employed for it. 
Obfuscation of "joinPath" will work without issue.

**Masking name collision example 2**: ::

    from datetime import datetime 
    def processObj( obj ):
       if isinstance( obj, datetime ): print "Date/Time!"
       
Becomes: ::

    from datetime import datetime as alias_0
    def processObj( obj ):
        if isinstance( obj, datetime ): print "Date/Time!"

This is the opposite problem as example 1. Note the 
type evaluation line did not apply the alias! Why?
Because "datetime" is a module name being preserved 
in clear text, and thus ignored by the current alias 
applying algorithm.

Pre-Obfuscated solution: ::

    from datetime import datetime as dt
    def processObj( obj ):
        if isinstance( obj, dt ): print "Date/Time!"
    
This will work because datetime.datetime now
has a manually assigned alias, so the auto alias
mechanism simply will not be employed for it. 
Obfuscation of "dt" will work without issue.
            

			
