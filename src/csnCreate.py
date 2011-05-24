# Author: Maarten Nieber

import csnProject
import csnContext
import os
import csnUtility
from GlobDirectoryWalker import Walker
from OrderedSet import OrderedSet

class FolderImporter(object):
    def __init__(self):
        self.folder = ""
        self.verbose = True
        self.file = None
    
    def Import(self, folder, type):
        self.folder = folder
        self.context = csnContext.Context()
        self.projectName = os.path.split(csnUtility.NormalizePath(self.folder))[1]
        self.context.csnakeFile = "%s/csn%s.py" % (self.folder, self.projectName)
        self.context.instance = self.projectName
        chars = list(self.projectName)
        chars[0] = chars[0].lower()
        self.context.instance = "".join(chars)
        chars[0] = chars[0].upper()
        self.projectName = "".join(chars)
        self.CreateInitPy()
        self.CreateContext(type)
        
    def CreateInitPy(self):
        initFile = "%s/__init__.py" % (self.folder)
        if not os.path.exists(initFile):
            f = open(initFile, 'w')
            f.write( "# Do not remove. Used to find python packages.\n" )
            f.close()

    def __CreateFileLists(self):
        excludedFolderList = ("CVS", ".svn")
        self.sourceFoldersList = OrderedSet()
        self.testSourceFoldersList = OrderedSet()
        self.includeFoldersList = OrderedSet()
        for file in Walker(self.folder, ["*"], excludedFolderList):
            extension = os.path.splitext(file)[1].lower()
            folder = csnUtility.RemovePrefixFromPath(os.path.dirname(file), self.folder)
            folder = csnUtility.NormalizePath(folder)
            while folder[0] == '/':
                folder = folder[1:]
            if extension in csnUtility.GetSourceFileExtensions(includeDot=True):
                pattern = "%s/*%s" % (folder, extension)
                if "tests" in csnUtility.PathToList(folder):
                    self.testSourceFoldersList.add(pattern)
                else:
                    self.sourceFoldersList.add(pattern)
                self.includeFoldersList.add(folder)
            if extension in csnUtility.GetIncludeFileExtensions(includeDot=True):
                pattern = "%s/*%s" % (folder, extension)
                if "tests" in csnUtility.PathToList(folder):
                    self.testSourceFoldersList.add(pattern)
                else:
                    self.sourceFoldersList.add(pattern)
                self.includeFoldersList.add(folder)

    def CreateContext(self, type):
        if False and os.path.exists(self.context.csnakeFile):
            raise IOError, "Project file %s already exists\n" % (self.context.csnakeFile)
    
        self.file = open(self.context.csnakeFile, 'w')

        self.__CreateHeaderSection()
        self.__CreateFileLists()

        self.Comment("# this section imports other CSnake python modules.")
        self.Comment("")

        self.Comment("# this section creates a Project instance for storing all %s ingredients." % self.projectName)
        self.Write("%s = csnProject.%s(\"%s\")" % (self.context.instance, type.title(), self.projectName))
        self.Write("")

        self.Comment("# The AddSources command adds a list of source files (wildcards are allowed).")
        self.Write("%s.AddSources(%s)" % (self.context.instance, str(self.sourceFoldersList)))
        self.Write("")

        self.Comment("# The AddIncludeFolders command adds a list of folders (wildcards are allowed) where include files are found.")
        self.Write("%s.AddIncludeFolders(%s)" % (self.context.instance, str(self.includeFoldersList)))
        self.Write("")

        if len(self.testSourceFoldersList):
            self.Comment("# The AddTests command adds a list of source tests (wildcards are allowed).")
            self.Write("if locals().get(\"cxxTest\"):")
            self.Write("    %s.AddTests(%s, cxxTest)" % (self.context.instance, str(self.testSourceFoldersList)))
            self.Write("")

        self.Write("# The AddProjects command adds a list of dependency projects.")
        self.Write("%s.AddProjects([])" % self.context.instance)
        self.Write("")

        self.file.close()

    def Write(self, text):
        self.file.write(text)
        self.file.write("\n")
    
    def Comment(self, text):
        if self.verbose:
            self.Write(text)
    
    def __CreateHeaderSection(self):
        self.Write("# this line imports the python modules needed for CSnake")
        self.Write("import csnProject")
        self.Write("")
