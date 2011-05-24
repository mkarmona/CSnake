# Author: Maarten Nieber

import ConfigParser
import csnContext
import csnGUIOptions

class Converter:
    def __init__(self, optionsFilename):
        self.section = "CSnake"
        self.optionsFilename = optionsFilename
        
    def ConvertOptions(self):
        parserOptions = ConfigParser.ConfigParser()
        parserOptions.read([self.optionsFilename])
        
        inputVersionOptions = 0.0
        if parserOptions.has_option(self.section, "version"):
            inputVersionOptions = parserOptions.getfloat(self.section, "version")
            
        if inputVersionOptions < csnGUIOptions.latestFileFormatVersion:
        
            if not parserOptions.has_section("ApplicationPaths"):
                    parserOptions.add_section("ApplicationPaths")
                    
            self.MoveOption(parserOptions, self.section, "currentguisettingsfilename", toOption = "contextfilename")
            self.RemoveOption(parserOptions, self.section, "askToLaunchVisualStudio")
            self.MoveOption(parserOptions, self.section, "visualstudiopath", toSection = "ApplicationPaths", toOption = "visualstudio2003", overwriteExisting = False)
            self.MoveOption(parserOptions, self.section, "pythonpath", toSection = "ApplicationPaths", toOption = "python", overwriteExisting = False)
            self.MoveOption(parserOptions, self.section, "cmakepath", toSection = "cmake2.4", overwriteExisting = False)

            if not parserOptions.has_option(self.section, "automaticallyInstallFiles"):
                parserOptions.set(self.section, "automaticallyInstallFiles", "False")
                
            if not parserOptions.has_option(self.section, "lastUsedImportFolder"):
                parserOptions.set(self.section, "lastUsedImportFolder", "")
        
            parserOptions.set(self.section, "version", str(csnGUIOptions.latestFileFormatVersion))
            f = open(self.optionsFilename, 'w')
            parserOptions.write(f)
            f.close() 
            
    def Convert(self, contextFilename):
        parserOptions = ConfigParser.ConfigParser()
        parserOptions.read([self.optionsFilename])
        
        parserContext = ConfigParser.ConfigParser()
        parserContext.read([contextFilename])
        
        inputVersion = 0.0
        validFile = False
        if parserContext.has_option(self.section, "version"):
            inputVersion = parserContext.getfloat(self.section, "version")
            validFile = True
        else:
            validFile = parserContext.has_section(self.section)

        if not validFile:
            return False

        if inputVersion < csnContext.latestFileFormatVersion:
            self.MoveOption(parserOptions, self.section, "compiler",  toParser = parserContext, toSection = self.section)
            self.MoveOption(parserOptions, self.section, "cmakebuildtype", toParser = parserContext, toOption = "configurationname")
            self.MoveOption(parserContext, self.section, "binfolder",  toOption = "buildfolder")
            self.MoveOption(parserOptions, self.section, "idepath", toParser = parserOptions, toSection = "ApplicationPaths", toOption = "visualstudio2003", overwriteExisting = False)
            self.MoveOption(parserOptions, self.section, "cmakepath", toParser = parserOptions, toSection = "ApplicationPaths", toOption = "cmake2.4", overwriteExisting = False)
            self.MoveOption(parserOptions, self.section, "pythonpath", toParser = parserOptions, toSection = "ApplicationPaths", toOption = "python", overwriteExisting = False)

            if not parserContext.has_option(self.section, "cmakeversion"):
                parserContext.set(self.section, "cmakeversion", "2.4")
                
            if not parserContext.has_option(self.section, "testrunnertemplate"):
                parserContext.set(self.section, "testrunnertemplate", "normalRunner.tpl")
            
            if not parserContext.has_option(self.section, "filter"):
                parserContext.set(self.section, "filter", "")
                
            index = 0
            while parserContext.has_section("RecentlyUsedCSnakeFile%s" % index):
                self.MoveOption(
                    parserContext, 
                    "RecentlyUsedCSnakeFile%s" % index,
                    "instance",
                    toSection = "RecentlyUsedCSnakeFiles",
                    toOption = "instance%s" % index
                )
                self.MoveOption(
                    parserContext, 
                    "RecentlyUsedCSnakeFile%s" % index,
                    "csnakeFile",
                    toSection = "RecentlyUsedCSnakeFiles",
                    toOption = "csnakeFile%s" % index
                )
                index += 1

            self.MoveOption(parserContext, self.section, "thirdpartybinfolder",  toOption = "thirdpartybuildfolder")
            self.MoveOption(parserContext, self.section, "idepath", toParser = parserOptions, toOption = "visualstudio2003", toSection = "ApplicationPaths", overwriteExisting = False)
            self.MoveOption(parserContext, self.section, "cmakepath", toParser = parserOptions, toOption = "cmake2.4", toSection = "ApplicationPaths", overwriteExisting = False)
            self.CopyOption(parserContext, self.section, "pythonpath", toParser = parserOptions, toOption = "python", toSection = "ApplicationPaths", overwriteExisting = False)
                
            parserContext.set(self.section, "version", str(csnContext.latestFileFormatVersion))
            f = open(contextFilename, 'w')
            parserContext.write(f)
            f.close() 
            
            parserOptions.set(self.section, "version", str(csnGUIOptions.latestFileFormatVersion))
            f = open(self.optionsFilename, 'w')
            parserOptions.write(f)
            f.close() 
        
        return True

    def MoveOption(self, fromParser, fromSection, fromOption, toParser = None, toSection = None, toOption = None, overwriteExisting = True):
        self.CopyOption(fromParser, fromSection, fromOption, toParser, toSection, toOption, overwriteExisting)
        self.RemoveOption(fromParser, fromSection, fromOption)
            
    def CopyOption(self, fromParser, fromSection, fromOption, toParser = None, toSection = None, toOption = None, overwriteExisting = True):
        if toParser is None:
            toParser = fromParser
        if toSection is None:
            toSection = fromSection
        if toOption is None:
            toOption = fromOption

        if (not overwriteExisting) and toParser.has_section(toSection) and toParser.has_option(toSection, toOption):
            return
            return
        
        if not (fromParser.has_section(fromSection) and fromParser.has_option(fromSection, fromOption)):
            return False
            
        if not toParser.has_section(toSection):
            toParser.add_section(toSection)

        if False:
            print "Copying option %s from section %s to option %s from section %s\n" % (fromOption, fromSection, toOption, toSection)
        toParser.set(toSection, toOption, fromParser.get(fromSection, fromOption))
        return True

    def RemoveOption(self, fromParser, fromSection, option):
        if fromParser.has_option(fromSection, option):
            fromParser.remove_option(fromSection, option)
 
