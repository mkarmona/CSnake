import os
import shutil
import csnUtility
import csnCompiler

class Compiler(csnCompiler.Compiler):
    def __init__(self):
        csnCompiler.Compiler.__init__(self)

    def IsForPlatform(self, _WIN32, _NOT_WIN32):
        return _NOT_WIN32 or (not _WIN32 and not _NOT_WIN32)

    def GetOutputFolder(self, _configuration = "${CMAKE_CFG_INTDIR}"):
        """
        Returns the folder where the compiler places binaries for _configuration.
        The default value for _configuration returns the output folder for the current configuration.
        for storing binaries.
        """
        return "%s/bin/%s" % (self.GetBuildFolder(), _configuration)
        
class PostProcessor:
    def Do(self, _project, _binaryFolder, _kdevelopProjectFolder):

        if not os.path.exists(_kdevelopProjectFolder):
            # if _kdevelopProjectFolder does not exist, then it MUST equal "".
            # otherwise, the user specified an invalid path for _kdevelopProjectFolder.  
            assert _kdevelopProjectFolder == "", "Cannot create kdevelop files in %s. Folder does not exist." % _kdevelopProjectFolder 
            return
            
        kdevelopProjectFolder = csnUtility.NormalizePath(_kdevelopProjectFolder)
        kdevProjectFilename = "%s/%s.kdevelop" % (_project.GetBuildFolder(), _project.name)
        kdevProjectFileListFilename = "%s.filelist" % kdevProjectFilename

        if not os.path.exists(kdevProjectFilename):
            return
            
        f = open(kdevProjectFileListFilename, 'w')
        for project in _project.ProjectsToUse():
            for source in project.sources:
                fileListItem = csnUtility.RemovePrefixFromPath(source, kdevelopProjectFolder)
                fileListItem = csnUtility.NormalizePath(fileListItem)
                f.write(fileListItem + "\n")
        f.close()
        result = (0 != shutil.copy(kdevProjectFileListFilename, _kdevelopProjectFolder))
        assert result, "Could not copy from %s to %s\n" % (kdevProjectFileListFilename, _kdevelopProjectFolder)
        
        kdevelopFileInTargetFolder = "%s/%s.kdevelop" % (kdevelopProjectFolder, _project.name) 
        f = open(kdevProjectFilename, 'r')
        kdevelopProjectText = f.read()
        f.close()
        f = open(kdevelopFileInTargetFolder, 'w')
        searchText = "<projectdirectory>%s" % _project.GetBuildFolder()
        replaceText = "<projectdirectory>%s" % kdevelopProjectFolder
        kdevelopProjectText = kdevelopProjectText.replace(searchText, replaceText)
        searchText = "<filelistdirectory>%s" % _project.GetBuildFolder()
        replaceText = "<filelistdirectory>%s" % kdevelopProjectFolder
        kdevelopProjectText = kdevelopProjectText.replace(searchText, replaceText)
        f.write(kdevelopProjectText)
        f.close()