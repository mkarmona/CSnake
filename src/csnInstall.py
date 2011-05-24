# Author: Maarten Nieber

import csnUtility
import os
import glob
import shutil
import GlobDirectoryWalker
from csnUtility import CheckIsList, CheckIsListOrNone

class Manager:
    def __init__(self, _project):
        self.project = _project
        self.filesToInstall = dict()
        self.filesToInstall["Debug"] = dict()
        self.filesToInstall["Release"] = dict()

    def AddFilesToInstall(self, _list, _location = None, _debugOnly = 0, _releaseOnly = 0, _WIN32 = 0, _NOT_WIN32 = 0):
        CheckIsList(_list)
        if not self.project.context.IsForPlatform(_WIN32, _NOT_WIN32):
            return
        
        if self.project.type == "third party":
            theList = list(_list)
        else:
            theList = self.project.Glob(_list)
        
        if _location is None:
            _location = '.'
            
        for file in theList:
            if not _debugOnly:
                if not self.filesToInstall["Release"].has_key(_location):
                    self.filesToInstall["Release"][_location] = []
                if not file in self.filesToInstall["Release"][_location]:
                    self.filesToInstall["Release"][_location].append( file )
            if not _releaseOnly:
                if not self.filesToInstall["Debug"].has_key(_location):
                    self.filesToInstall["Debug"][_location] = []
                if not file in self.filesToInstall["Debug"][_location]:
                    self.filesToInstall["Debug"][_location].append( file )
    
    def ResolvePathsOfFilesToInstall(self, _skipCVS = 1):
        """ 
        This function replaces relative paths and wildcards in self.filesToInstall with absolute paths without wildcards.
        Any folder is replaced by a complete list of the files in that folder.
        _skipCVS - If true, folders called CVS and .svn are automatically skipped. 
        """
        excludedFolderList = ("CVS", ".svn")
        for mode in ("Debug", "Release"):
            for project in self.project.GetProjects(_recursive = 1, _includeSelf = True):
                filesToInstall = dict()
                for location in project.installManager.filesToInstall[mode].keys():
                    for dllPattern in project.installManager.filesToInstall[mode][location]:
                        path = csnUtility.NormalizePath(dllPattern)
                        if not os.path.isabs(path):
                            path = "%s/%s" % (self.project.context.thirdPartyBuildFolder, path)
                        for file in glob.glob(path):
                            if (os.path.basename(file) in excludedFolderList) and _skipCVS and os.path.isdir(file):
                                continue
                            if os.path.isdir(file):
                                for folderFile in GlobDirectoryWalker.Walker(file, ["*"], excludedFolderList):
                                    if not os.path.isdir(folderFile):
                                        normalizedLocation = location + "/" + csnUtility.RemovePrefixFromPath(os.path.dirname(folderFile), file)
                                        normalizedLocation = csnUtility.NormalizePath(normalizedLocation)
                                        if not filesToInstall.has_key(normalizedLocation):
                                            filesToInstall[normalizedLocation] = []
                                        filesToInstall[normalizedLocation].append(csnUtility.NormalizePath(folderFile))
                            else:
                                normalizedLocation = csnUtility.NormalizePath(location)
                                if not filesToInstall.has_key(normalizedLocation):
                                    filesToInstall[normalizedLocation] = []
                                filesToInstall[normalizedLocation].append(csnUtility.NormalizePath(file))
                    
                project.installManager.filesToInstall[mode] = filesToInstall
 
    def InstallFilesToBuildFolder(self, onlyNewerFiles=False):
        """ 
        This function copies all third party dlls to the build folder, so that you can run the executables in the
        build folder without having to build the INSTALL target.
        """
        result = True
        self.ResolvePathsOfFilesToInstall()

        for mode in ("Debug", "Release"):
            buildResultsFolder = self.project.context.GetBuildResultsFolder(mode)
            os.path.exists(buildResultsFolder) or os.makedirs(buildResultsFolder)
            for project in self.project.GetProjects(_recursive = 1, _includeSelf = True):
                for location in project.installManager.filesToInstall[mode].keys():
                    for file in project.installManager.filesToInstall[mode][location]:
                        absLocation = "%s/%s" % (buildResultsFolder, location)
                        assert not os.path.isdir(file), "\n\nError: InstallFilesToBuildFolder cannot install a folder (%s)" % file
                        os.path.exists(absLocation) or os.makedirs(absLocation)
                        assert os.path.exists(absLocation), "Could not create %s\n" % absLocation
                        if onlyNewerFiles:
                            targetFile = "%s/%s" % (absLocation, os.path.basename(file))
                            if os.path.exists(targetFile) and os.stat(file).st_mtime <= os.stat(targetFile).st_mtime:
                                continue
                            
                        print "Install: copying %s to %s\n" % (file, absLocation)
                        fileResult = (0 != shutil.copy(file, absLocation))
                        result = fileResult and result
                        if not fileResult:
                            print "Failed to copy %s to %s\n" % (file, absLocation)
        return result
