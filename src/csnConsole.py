# Author: Maarten Nieber

import csnGUIHandler
import csnGUIOptions
import csnGenerator
import csnContext
import sys
from optparse import OptionParser

class Console:
    def __init__(self):
        self.parser = OptionParser(usage="%prog optionsFile contextFile [--install --thirdParty]")
        self.parser.add_option("-i", "--install", dest="install", action="store_true", default=False, help="install files to build folder")
        self.parser.add_option("-t", "--thirdParty", dest="thirdParty", action="store_true", default=False, help="configure third party projects")

        self.context = None
        self.options = csnGUIOptions.Options(self)
        self.handler = csnGUIHandler.Handler(self.options)
        
    def Run(self):
        """ Starts the console application """
        (commandLineOptions, commandLineArgs) = self.parser.parse_args()
        if len(commandLineArgs) != 2:
            self.parser.print_usage()
            sys.exit(1)
            
        self.options.Load(commandLineArgs[0])
        self.context = self.handler.LoadContext(commandLineArgs[1])

        if commandLineOptions.thirdParty:
            taskMsg = "ConfigureThirdPartyFolder from %s to %s..." % (self.context.thirdPartyRootFolder, self.context.thirdPartyBuildFolder) 
            print "Starting task: " + taskMsg  
            result = self.handler.ConfigureThirdPartyFolder()
            assert result, "\n\nTask failed: ConfigureThirdPartyFolder" 
            print "Finished " + taskMsg + "\nPlease build the 3rd party sources then press enter...\n"
            raw_input()

        if commandLineOptions.install:
            taskMsg = "InstallFilesToBuildFolder to %s..." % (self.context.buildFolder)
            print "Starting task: " + taskMsg 
            result = self.handler.InstallFilesToBuildFolder()
            assert result, "\n\nTask failed: InstallFilesToBuildFolder" 
            print "Finished task: " + taskMsg

        taskMsg = "ConfigureProjectToBuildFolder to %s..." % (self.context.buildFolder)
        print "Starting task: " + taskMsg 
        result = self.handler.ConfigureProjectToBuildFolder(_alsoRunCMake = True)
        assert result, "\n\nTask failed: ConfigureProjectToBuildFolder" 
        print "Finished task: " + taskMsg + "\nPlease build the sources in %s.\n" % self.handler.GetTargetSolutionPath()
if __name__ == "__main__":
    console = Console()
    console.Run()
