#! /usr/bin/python
license = (# @ReservedAssignment
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
import copy
from . config import OpyConfig 
from . obfuscator import Obfuscator 
DEFAULT_ENCODING = 'utf-8'
       
class _RunOptions:

    def __init__(self) :
        self.printHelp = False
        self.sourceRootDirectory = None
        self.targetRootDirectory = None
        self.configFilePath = None  # None == default, False == use configSettings
        self.configSettings = None

#-------------------------------------------------------

def obfuscate( sourceRootDirectory=None
             , targetRootDirectory=None
             , configFilePath=None
             , configSettings=None
             , isVerbose=True      
             ):    
    runOptions = _RunOptions()
    runOptions.printHelp = False
    runOptions.sourceRootDirectory = sourceRootDirectory
    runOptions.targetRootDirectory = targetRootDirectory
    runOptions.config = copy.copy(configSettings)    
    runOptions.configFilePath = (
        configFilePath if configSettings is None else False)
    ob = Obfuscator()   
    ob._autoConfig(runOptions, True)    
    return ob._run(runOptions, isVerbose)
    
def analyze( sourceRootDirectory=None
           , configSettings=OpyConfig()
           , fileList=[]
           , isVerbose=True             
           ):    
    runOptions = _RunOptions()
    runOptions.printHelp = False
    runOptions.sourceRootDirectory = sourceRootDirectory
    runOptions.targetRootDirectory = None
    runOptions.configFilePath = False    
    runOptions.config = copy.copy(configSettings)    
    if fileList and len(fileList) > 0:
        runOptions.config.subset_files = fileList
    ob = Obfuscator()        
    ob._autoConfig(runOptions, isVerbose)        
    return ob._analyze(runOptions, isVerbose)

def printHelp():    
    runOptions = _RunOptions()
    runOptions.printHelp = True
    ob = Obfuscator()  
    ob._run(runOptions)   
    
if __name__ == '__main__': printHelp()
