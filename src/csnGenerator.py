# Author: Maarten Nieber

import csnUtility
import csnCMake
import os.path
import warnings
import sys
import types
import OrderedSet
import re
import shutil

# General documentation
#
# This block contains an introduction to the CSnake code. It's main purpose is to introduce some common terminology and concepts.
#  It is assumed that the reader has already read the CSnake user manual.
#
# Config and use file:
# CMake uses config and use files to let packages use other packages. The config file assigns a number of variables
# such as SAMPLE_APP_INCLUDE_DIRECTORIES and SAMPLE_APP_LIBRARY_DIRECTORIES. The use file uses these values to add
# include directories and library directories to the current CMake target. The standard way to use these files is to a)
# make sure that SAMPLE_APP_DIR points to the location of SAMPLE_APPConfig.cmake and UseSAMPLE_APP.cmake, b) 
# call FIND_PACKAGE(SAMPLE_APP) and c) call INCLUDE(${SAMPLE_APP_USE_FILE}. In step b) the config file of SAMPLE_APP is included and
# in step c) the necessary include directories, library directories etc are added to the current target.
# To adhere to normal CMake procedures, csnBuild also uses the use file and config file. However, FIND_PACKAGE is not needed,
# because the Generator class will directly include the config and use file for any dependency project.
# IMPORTANT: CSnake contains a workaround for a problem in Visual Studio: when you create a dependency, making a project A depend on a B, then Visual Studio will automatically
# link A with the binaries of B. This is a problem, because config file (BConfig.cmake) already tells A to link with the binaries of B, and linking twice with the same binaries may give linker errors.
# To work around this problem, CSnake generates two config files for B: BConfig.cmake and BConfig.cmake.private. The second one does not contain the CMake commands to link with the binaries
# of B, and this config file is included in the CMakeLists.txt of A.
#
# Compilers
#
# In this version of CSnake, you are required to specify the compiler that you will use to build your project. Examples of compiler instances are csnKDevelop.Compiler and csnVisualStudio2003.Compiler.
# I chose this design because it allowed me to simplify the code a lot. For example, when adding a compiler definition for linux, a check is performed to see if the project uses a linux compiler; it not,
# the definition is simply ignored.
# The default compiler is stored in csnProject.globalSettings.compilerType. If you create a Project without specifying a compiler, then this compiler will be assigned to the project instance.
#

# ToDo:
# - ImportWizard leaves a window behind when it closes
# - In windows, Debug build type does not work
# - Replace arguments such as _ONLY_WIN32 with flags: AddSources(sources, flags = [onlyWin32, onlyRelease]). From csnFlags import *.
# - It seems that the preprocessor definitions are not properly generated when AddDefinitions? is called for multiple definitions. 
# - Check that created filenames are not too long (especially with XYZApplications_BLABLA)
# - Why are definitions used directly in the use file, instead of via a CMake variable?
# - Automatically add -D for definitions in windows
# - It seems adding definition "/Zm200" does not work. It is treated as a preprocessor define and not as a compiler option
# - Improve documentation and usability of AddFilesToInstall
# - If you choose GeoAPIApplications in GIMIAS without any plugin, you do not see the GeoAPI apps in the solution
# - Get rid of prebuiltBinariesFolder?
# - Fix module reloading. Check out super_reload
# - Bad smell: Relative paths in _list are assumed to be relative to the third party binary folder. Disallow relative paths? Document in AddFilesToInstall and ResolvePathsOfFilesToInstall
# - Replace string labels with class types
# - Get rid of underscore in arguments
# - How to handle the fact that installing files overwrites existing files?

# New features
# - Create csn file automatically: support tests and libraries
# - Create csn file automatically: wizard asks for project type, proposes python modules to import, and dependency projects within those modes
# - Create csn file automatically: support cilab module project and GIMIAS plugin
# - option create-context in csnConsole
# - Support doxygen
# - Support for cxxtest should be more built-in (now it works because cxxtest is part of the toolkit third parties)
# - In case of an exception. show the stack trace in a nice way. Double clicking in the stack trace opens offending line in a text editor
# - Have more control over which tests are run
# - Have seperate checkListBox for super categories
# - Build all stuff in DebugAndRelease, Debug or Release. Support DebugAndRelease in Linux by building to both Debug and Release
# - Support clean syntax in which each project is a function (csnProject.RegisterProject(itk))
# - Add recently used context files (wx.FileHistory)
# - Edit button should be a butcon which allows to edit any csnake file in the solution.
# - When automatically installing files, also have a cached list of files that must be checked every 10 seconds
# - Only configure third parties that are needed for the target
# - Install to build folder using symbolic links
# - Scan source files and detect which supporting projects are needed
# - Upgrade existing csn file by creating one automatically and merging parts of it into the existing csn file
# - Add button to clean the build folder
# - Better GUI: do more checks, give nice error messages, show progress bar (call cmake asynchronous, poll file system) with cancel button. Try catching cmake output using Pexpect
# - Have public and private related projects (hide the include paths from its clients)
# - If ITK doesn't implement the DONT_INHERIT keyword, then use environment variables to work around the cmake propagation behaviour

# ToDo examples:
# In the first example, use the import project wizard to create a csn file for GreetMe, configure and build
# In the second example, use the import project wizard to create a csn file for HelloWorldLib. Add MyLibrary to MyCommandLine, configure and build
# In the third example, add a csnuse the import project wizard to create a csn file for MyApplication. Add MyLibrary to MyExecutable, configure and build

# End: ToDo.

# add root of csnake to the system path
sys.path.append(csnUtility.GetRootOfCSnake())
version = 2.21

# set default location of python. Note that this path may be overwritten in csnGUIHandler

class SyntaxError(StandardError):
    """ Used when there is a syntax error, for example in a folder name. """
    pass

def ToProject(project):
    """
    Helper function that tests if its argument (project) is a function. If so, it returns the result of the function. 
    If not, it returns its argument (project). It is used to treat Project instances and functions returning a Project instance
    in the same way.
    """
    result = project
    if type(project) == types.FunctionType:
        result = project()
    return result
    
class Generator:
    """
    Generates the CMakeLists.txt for a csnBuild.Project and all its dependency projects.
    """

    def __init__(self):
        pass
        
    def Generate(self, _targetProject, _generatedList = None):
        """
        Generates the CMakeLists.txt for _targetProject (a csnBuild.Project) in the build folder.
        _generatedList -- List of projects for which Generate was already called (internal to the function).
        """

        _targetProject.dependenciesManager.isTopLevel = _generatedList is None
        if _targetProject.dependenciesManager.isTopLevel:
            _targetProject.installManager.ResolvePathsOfFilesToInstall()
            _generatedList = []

        # assert that this project is not filtered
        assert not _targetProject.MatchesFilter(), "\n\nLogical error: the project %s should have been filtered instead of generated." % _targetProject.name
        
        # Trying to Generate a project twice indicates a logical error in the code        
        assert not _targetProject in _generatedList, "\n\nError: Trying to Generate a project twice. Target project name = %s" % (_targetProject.name)

        for generatedProject in _generatedList:
            if generatedProject.name == _targetProject.name:
                raise NameError, "Each project must have a unique name. Conflicting projects are %s (in folder %s) and %s (in folder %s)\n" % (_targetProject.name, _targetProject.GetSourceRootFolder(), generatedProject.name, generatedProject.GetSourceRootFolder())
        _generatedList.append(_targetProject)
        
        # check for backward slashes
        if csnUtility.HasBackSlash(_targetProject.context.buildFolder):
            raise SyntaxError, "Error, backslash found in build folder %s" % _targetProject.context.buildFolder
        
        # check  trying to build a third party library
        if _targetProject.type == "third party":
            warnings.warn( "CSnake warning: you are trying to generate CMake scripts for a third party module (nothing generated)\n" )
            return
         
        # create build folder
        os.path.exists(_targetProject.GetBuildFolder()) or os.makedirs(_targetProject.GetBuildFolder())
    
        # create Win32Header
        if _targetProject.type != "executable" and _targetProject.compileManager.generateWin32Header:
            _targetProject.compileManager.GenerateWin32Header()
            # add search path to the generated win32 header
            if not _targetProject.GetBuildFolder() in _targetProject.compileManager.public.includeFolders:
                _targetProject.compileManager.public.includeFolders.append(_targetProject.GetBuildFolder())
        
        _targetProject.RunCustomCommands()

        # Find projects that must be generated. A separate list is used to ease debugging.
        projectsToGenerate = OrderedSet.OrderedSet()
        requiredProjects = _targetProject.GetProjects(_recursive = 1, _onlyRequiredProjects = 1)        
        for projectToGenerate in requiredProjects:
            # determine if we must Generate the project. If a required project will generate it, 
            # then leave it to the required project. This will prevent multiple generation of the same project.
            # If a non-required project will generate it, then still generate the project 
            # (the non-required project may depend on target project to generate project, creating a race condition).
            generateProject = not projectToGenerate in _generatedList and projectToGenerate.type in ("dll", "executable", "library")
            if generateProject:
                for requiredProject in _targetProject.GetProjects(_recursive = 0, _onlyRequiredProjects = 1):
                    if requiredProject.dependenciesManager.DependsOn(projectToGenerate):
                        generateProject = 0
            if generateProject:
                projectsToGenerate.add(projectToGenerate)
        
        # add non-required projects that have not yet been generated to projectsToGenerate
        for project in _targetProject.GetProjects(_onlyNonRequiredProjects = True):
            if not project in _generatedList:
                projectsToGenerate.add(project)

        # generate projects, and add a line with ADD_SUBDIRECTORY
        generatedProjects = OrderedSet.OrderedSet()
        for project in projectsToGenerate:
            # check again if a previous iteration of this loop didn't add project to the generated list
            if not project in _generatedList:
                self.Generate(project, _generatedList)
                generatedProjects.append(project)
           
        # write cmake files
        writer = csnCMake.Writer(_targetProject)
        writer.GenerateConfigFile( _public = 0)
        writer.GenerateConfigFile( _public = 1)
        writer.GenerateUseFile()
        writeInstallCommands = _targetProject.dependenciesManager.isTopLevel
        #writeInstallCommands = False # hack
        writer.GenerateCMakeLists(generatedProjects, requiredProjects, _writeInstallCommands=writeInstallCommands)

    def InstallFilesToBuildFolder(self, _targetProject):
        """ 
        This function copies all third party dlls to the build folder, so that you can run the executables in the
        build folder without having to build the INSTALL target.
        """
        return _targetProject.installManager.InstallFilesToBuildFolder()
                        
    def PostProcess(self, _targetProject):
        """
        Apply post-processing after the CMake generation for _targetProject and all its child projects.
        """
        for project in _targetProject.GetProjects(_recursive = 1, _includeSelf = True):
            _targetProject.context.postProcessor.Do(project)
