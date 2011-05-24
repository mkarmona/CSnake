# Author: Maarten Nieber

import ConfigParser
import csnContext
import csnUtility
import os

latestFileFormatVersion = 3.0

class ApplicationData:
    def __init__(self, path = "", prettyName = "", searchPaths = None):
        self.path = path
        self.prettyName = prettyName
        if searchPaths is None:
            searchPaths = list()
        self.searchPaths = searchPaths
        
class Options(object):
    def __init__(self, guiInstance=None):
        self.guiInstance = guiInstance
        if not self.guiInstance is None:
            assert hasattr(self.guiInstance, "context"), "Could not obtain field context from guiInstance"
        self.contextFilename = ""
        self.recentlyUsed = list()
        self.automaticallyInstallFiles = False
        self.lastUsedImportFolder = ""

        self.kdevelop3Data = ApplicationData("", "KDevelop 3", ["kdevelop3"])
        self.visualStudio2003Data = ApplicationData("", "Visual Studio 2003", ["Microsoft Visual Studio .NET 2003/Common7/IDE/devenv.exe"])
        self.visualStudio2005Data = ApplicationData("", "Visual Studio 2005", ["Microsoft Visual Studio 8/Common7/IDE/devenv.exe"])
        self.visualStudio2008Data = ApplicationData("", "Visual Studio 2008")
        self.cmake24Data = ApplicationData("", "CMake 2.4", ["CMake 2.4/bin/cmake.exe"])
        self.cmake26Data = ApplicationData("", "CMake 2.6", ["CMake 2.6/bin/cmake.exe"])
        self.pythonData = ApplicationData("", "Python", ["python", "Python24/python.exe", "Python25/python.exe", "Python26/python.exe"])
        self.textEditorData = ApplicationData("", "Text Editor", ["gedit", "Notepad++/notepad++.exe", "UltraEdit-32/uedit32.exe", "NoteTab Light/NoteTab.exe", "PSPad editor/PSPad.exe", "windows/system32/notepad.exe"])

        self.dataFor = dict()
        self.dataFor["kdevelop3"] = self.kdevelop3Data
        self.dataFor["visualstudio2003"] = self.visualStudio2003Data
        self.dataFor["visualstudio2005"] = self.visualStudio2005Data
        self.dataFor["visualstudio2008"] = self.visualStudio2008Data
        self.dataFor["cmake2.4"] = self.cmake24Data
        self.dataFor["cmake2.6"] = self.cmake26Data
        self.dataFor["python"] = self.pythonData
        self.dataFor["texteditor"] = self.textEditorData
        
        self.ideFor = dict()
        self.ideFor["KDevelop3"] = self.kdevelop3Data
        self.ideFor["Visual Studio 7 .NET 2003"] = self.visualStudio2003Data
        self.ideFor["Visual Studio 8 2005"] = self.visualStudio2005Data
        self.ideFor["Visual Studio 8 2005 Win64"] = self.visualStudio2005Data
        self.ideFor["Visual Studio 9 2008"] = self.visualStudio2008Data
        self.ideFor["Visual Studio 9 2008 Win64"] = self.visualStudio2008Data

        self.cmakeDataForVersion = dict()
        self.cmakeDataForVersion["2.4"] = self.cmake24Data
        self.cmakeDataForVersion["2.6"] = self.cmake26Data

        self.windowsRootPaths = list()
        for i in range(ord('C'), ord('Z')+1):
            drive = chr(i)
            if not os.path.exists(drive +":\\"):
                break
        
            self.windowsRootPaths.append("%s:/" % drive)
            for path in ("%s:/Program Files" % drive, "%s:/Program Files (x86)" % drive):
                if os.path.exists(path):
                    self.windowsRootPaths.append(path)
                    
        self.linuxRootPaths = [
            "/usr/bin", 
            "/home/mnieber/Software"
        ]        
        self.applicationRootPaths = self.linuxRootPaths
        if csnUtility.IsRunningOnWindows():
            self.applicationRootPaths = self.windowsRootPaths
            
    def FindApplicationPaths(self):
        for applicationData in self.dataFor.values():
            if applicationData.path == "":
                applicationData.path = csnUtility.LocateApplication(self.applicationRootPaths, applicationData.searchPaths)[1]

    def GetIDEData(self):
        return self.ideFor[self.guiInstance.context.compiler]
        
    def GetCMakeData(self):
        return self.cmakeDataForVersion[self.guiInstance.context.cmakeVersion]
        
    def Load(self, filename):
        parser = ConfigParser.ConfigParser()
        parser.read([filename])
        section = "CSnake"
        self.contextFilename = parser.get(section, "contextFilename")
        self.automaticallyInstallFiles = parser.getboolean(section, "automaticallyInstallFiles")
        self.lastUsedImportFolder = parser.get(section, "lastUsedImportFolder")
        self.__LoadApplicationPaths(parser)
        parserContext = ConfigParser.ConfigParser()
        parserContext.read([self.contextFilename])
        self.__LoadRecentlyUsedCSnakeFiles(parserContext)
        
    def Save(self, filename):
        parser = ConfigParser.ConfigParser()
        section = "CSnake"
        parser.add_section(section)
        parser.set(section, "contextFilename", self.contextFilename)
        parser.set(section, "automaticallyInstallFiles", str(self.automaticallyInstallFiles))
        parser.set(section, "lastUsedImportFolder", self.lastUsedImportFolder)
        parser.set(section, "version", str(latestFileFormatVersion))
        self.__SaveApplicationPaths(parser)
        f = open(filename, 'w')
        parser.write(f)
        f.close()

        if self.contextFilename != "":
            parserContext = ConfigParser.ConfigParser()
            parserContext.read([self.contextFilename])
            self.__SaveRecentlyUsedCSnakeFiles(parserContext)
            f = open(self.contextFilename, 'w')
            csnContext.WriteHeaderComments(f)
            parserContext.write(f)
            f.close()
        
    def GetIDEPath(self):
        return self.GetIDEData().path
        
    def SetIDEPath(self, path):
        self.GetIDEData().path = path
        
    def GetIDEPrettyName(self):
        return self.GetIDEData().prettyName
        
    def GetCMakePath(self):
        result = self.GetCMakeData().path
        return result
        
    def SetCMakePath(self, path):
        self.GetCMakeData().path = path
        
    def GetPythonPath(self):
        return self.pythonData.path
        
    def SetPythonPath(self, path):
        self.pythonData.path = path
        
    def GetTextEditorPath(self):
        return self.textEditorData.path
        
    def SetTextEditorPath(self, path):
        self.textEditorData.path = path
        
    def GetCMakePrettyName(self):
        return self.GetCMakeData().prettyName
        
    def __LoadRecentlyUsedCSnakeFiles(self, parser):
        self.recentlyUsed = []
        count = 0
        section = "RecentlyUsedCSnakeFiles"
        while parser.has_option(section, "instance%s" % count):
            self.AddRecentlyUsed(
                parser.get(section, "instance%s" % count),
                parser.get(section, "csnakeFile%s" % count)
            )
            count += 1
    
    def __SaveRecentlyUsedCSnakeFiles(self, parser):
        section = "RecentlyUsedCSnakeFiles"
        if not parser.has_section(section):
            parser.add_section(section)
        for index in range(len(self.recentlyUsed)):
            parser.set(section, "instance%s" % index, self.recentlyUsed[index].instance) 
            parser.set(section, "csnakeFile%s" % index, self.recentlyUsed[index].csnakeFile) 

    def AddRecentlyUsed(self, _instance, _csnakeFile):
        for item in range( len(self.recentlyUsed) ):
            x = self.recentlyUsed[item]
            if (x.instance == _instance and x.csnakeFile == _csnakeFile):
                self.recentlyUsed.remove(x)
                self.recentlyUsed.insert(0, x)
                return
        
        x = csnContext.Context()
        (x.instance, x.csnakeFile) = (_instance, _csnakeFile)
        self.recentlyUsed.insert(0, x)
    
    def ClearRecentlyUsed(self):
        self.recentlyUsed = list()
    
    def IsCSnakeFileInRecentlyUsed(self, csnakeFile):
        """ Returns True if self.csnakeFile is in the list of recently used csnake files """
        result = False
        for item in range( len(self.recentlyUsed) ):
            x = self.recentlyUsed[item]
            if (x.csnakeFile == csnakeFile):
                result = True
        return result

    def __LoadApplicationPaths(self, parser):
        for name in self.dataFor:
            if parser.has_option("ApplicationPaths", name):
                self.dataFor[name].path = parser.get("ApplicationPaths", name)

    def __SaveApplicationPaths(self, parser):
        section = "ApplicationPaths"
        if not parser.has_section(section):
            parser.add_section(section)
            
        for name in self.dataFor:
            parser.set("ApplicationPaths", name, self.dataFor[name].path)
            
    idePath = property(GetIDEPath, SetIDEPath)    
    cmakePath = property(GetCMakePath, SetCMakePath)
    pythonPath = property(GetPythonPath, SetPythonPath)
    textEditorPath = property(GetTextEditorPath, SetTextEditorPath)
