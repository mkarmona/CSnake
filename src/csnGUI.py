# Author: Maarten Nieber

import wx
import wx.html
from wx import xrc
import csnGUIHandler
import csnGUIOptions
import csnContext
import csnImportWizard
import csnContextConverter
import csnBuild
import csnCreate
import csnUtility
import os.path
import sys
import shutil
import time
import subprocess
import xrcbinder
from optparse import OptionParser
import csnProject
import traceback

csnakeFilesWildCard = "Context Files (*.csnakecontext;*.CSnakeGUI;)|*.csnakecontext;*.CSnakeGUI|All Files (*.*)|*.*"

class RedirectText:
    """
    Used to redirect messages to stdout to the text control in CSnakeGUIFrame.
    """
    def __init__(self,aWxTextCtrl):
        self.out=aWxTextCtrl

    def write(self,string):
        self.out.WriteText(string)
        self.out.Update()

def FormatFilename(x):
    if x == "":
        return x
    return csnUtility.NormalizePath(x)
    
def FormatFilenameList(filenameList):
    return [csnUtility.NormalizePath(x) for x in filenameList]
    
class SelectFolderCallback:
    """ 
    Lets the user choose a path, then calls 'callback' to set the path value in the domain layer, 
    and calls app.UpdateGUIAndSaveContextAndOptions.
    """
    def __init__(self, message, callback, app):
        self.message = message
        self.callback = callback
        self.app = app
        
    def __call__(self, event = None):
        dlg = wx.DirDialog(None, self.message)
        if dlg.ShowModal() == wx.ID_OK:
            self.callback(csnUtility.NormalizePath(dlg.GetPath()))
        self.app.UpdateGUIAndSaveContextAndOptions()
        
class CSnakeGUIApp(wx.App):
    def OnInit(self):
        self.thisFolder = "%s" % (os.path.dirname(sys.argv[0]))
        self.thisFolder = csnUtility.NormalizePath(self.thisFolder)
        if self.thisFolder == "":
            self.thisFolder = "."
        
        self.resourcesFolder = csnUtility.GetRootOfCSnake() + "/resources"
        
        self.destroyed = False
        self.listOfPossibleTargets = []
        self.projectCheckBoxes = dict()
        self.context = None
        self.options = csnGUIOptions.Options(guiInstance=self)
        self.optionsFilename = "%s/options" % self.thisFolder
        self.converter = csnContextConverter.Converter(self.optionsFilename)
        self.handler = csnGUIHandler.Handler(self.options)
        self.locked = False
        self.helpTextSelectProjects = None
        
        self.InitGUI()
        self.Initialize()
        return 1

    def InitGUI(self):
        wx.InitAllImageHandlers()
        xrcFile = "%s/csnGUI.xrc" % self.resourcesFolder
        self.res = xrc.XmlResource(xrcFile)
        self.InitFrame()
        self.InitFrameHelp()
        self.InitMenu()
        self.frame.Bind(wx.EVT_CLOSE, self.OnExit, self.frame)
        self.SetTopWindow(self.frame)
        self.frame.SetSize([800, 550])
        self.frame.Show()		
    
    def InitFrame(self):
        self.frame = self.res.LoadFrame(None, "frmCSnakeGUI")
        self.LoadIcon()
        self.binder = xrcbinder.Binder(self, self.frame)
        self.binder.SetBuddyClass("options", self.options)
        
        self.textLog = xrc.XRCCTRL(self.frame, "textLog")
        self.binder.AddTextControl("txtBuildFolder", buddyClass = "context", buddyField = "buildFolder")
        self.binder.AddTextControl("txtThirdPartyBuildFolder", buddyClass = "context", buddyField = "thirdPartyBuildFolder")
        self.binder.AddTextControl("txtInstallFolder", buddyClass = "context", buddyField = "installFolder")
        self.binder.AddTextControl("txtKDevelopProjectFolder", buddyClass = "context", buddyField = "kdevelopProjectFolder")
        self.binder.AddTextControl("txtThirdPartyRootFolder", buddyClass = "context", buddyField = "thirdPartyRootFolder")
        self.binder.AddTextControl("txtCMakePath", buddyClass = "options", buddyField = "cmakePath")
        self.binder.AddTextControl("txtPythonPath", buddyClass = "options", buddyField = "pythonPath")
        self.binder.AddTextControl("txtTextEditorPath", buddyClass = "options", buddyField = "textEditorPath")
        self.binder.AddTextControl("txtIDEPath", buddyClass = "options", buddyField = "idePath")
        self.binder.AddComboBox("cmbCSnakeFile", valueListFunctor = self.GetCSnakeFileComboBoxItems, buddyClass = "context", buddyField = "csnakeFile")
        self.binder.AddComboBox("cmbInstance", valueListFunctor = self.GetInstanceComboBoxItems, buddyClass = "context", buddyField = "instance")
        self.binder.AddComboBox("cmbCompiler", valueListFunctor = self.GetCompilerComboBoxItems, buddyClass = "context", buddyField = "compiler")
        self.binder.AddComboBox("cmbCMakeVersion", valueListFunctor = self.GetCMakeVersionComboBoxItems, buddyClass = "context", buddyField = "cmakeVersion")
        self.binder.AddComboBox("cmbBuildType", valueListFunctor = self.GetBuildTypeComboBoxItems, buddyClass = "context", buddyField = "configurationName")
        self.binder.AddListBox("lbRootFolders", buddyClass = "context", buddyField = "rootFolders")
        self.binder.AddCheckBox("chkAutomaticallyInstallFiles", buddyClass = "options", buddyField = "automaticallyInstallFiles")

        # set rules to format filenames
        filenameFields = [
            "txtBuildFolder", 
            "txtThirdPartyBuildFolder", 
            "txtInstallFolder", 
            "txtKDevelopProjectFolder", 
            "txtThirdPartyRootFolder", 
            "txtCMakePath", 
            "txtPythonPath", 
            "txtTextEditorPath", 
            "txtIDEPath", 
            "cmbCSnakeFile" 
        ]
        for filenameField in filenameFields:
            self.binder.SetValueTransform(filenameField, FormatFilename)
        self.binder.SetValueTransform("lbRootFolders", FormatFilenameList)

        # when the following fields change, update all the controls
        listForUpdatingGUI = [
            "cmbCompiler",
            "cmbCMakeVersion",
            "txtIDEPath",
            "txtPythonPath",
            "txtCMakePath", 
            "txtTextEditorPath", 
            "cmbCSnakeFile",
            "txtBuildFolder", 
            "txtThirdPartyRootFolder", 
            "txtThirdPartyBuildFolder", 
            "cmbInstance"
        ]
        for controlName in listForUpdatingGUI:
            self.binder.SetAfterUpdateBuddyHook(controlName, self.UpdateGUIAndSaveContextAndOptionsWithLock)
        
        self.kdevelopItems = list()
        self.kdevelopItems.append(xrc.XRCCTRL(self.frame, "labelKDevelopFolder"))
        self.kdevelopItems.append(xrc.XRCCTRL(self.frame, "txtKDevelopProjectFolder"))
        self.kdevelopItems.append(xrc.XRCCTRL(self.frame, "btnSelectKDevelopProjectFolder"))
        
        self.noteBook = xrc.XRCCTRL(self.frame, "noteBook")
        self.noteBook.SetSelection(0)
        
        self.panelSelectProjects = xrc.XRCCTRL(self.frame, "panelSelectProjects")
        self.statusBar = xrc.XRCCTRL(self.frame, "statusBar")

        self.frame.Bind(wx.EVT_BUTTON, SelectFolderCallback("Select Binary Folder", self.SetBuildFolder, self), id=xrc.XRCID("btnSelectBuildFolder"))
        self.frame.Bind(wx.EVT_BUTTON, SelectFolderCallback("Select Install Folder", self.SetInstallFolder, self), id=xrc.XRCID("btnSelectInstallFolder"))
        self.frame.Bind(wx.EVT_BUTTON, SelectFolderCallback("Select Third Party Root Folder", self.SetThirdPartyRootFolder, self), id=xrc.XRCID("btnSelectThirdPartyRootFolder"))
        self.frame.Bind(wx.EVT_BUTTON, SelectFolderCallback("Select Third Party Bin Folder", self.SetThirdPartyBuildFolder, self), id=xrc.XRCID("btnSelectThirdPartyBuildFolder"))
        self.frame.Bind(wx.EVT_BUTTON, SelectFolderCallback("Select folder for saving the KDevelop project file", self.SetKDevelopProjectFolder, self), id=xrc.XRCID("btnSelectKDevelopProjectFolder"))
        self.frame.Bind(wx.EVT_BUTTON, SelectFolderCallback("Add root folder", self.AddRootFolder, self), id=xrc.XRCID("btnAddRootFolder"))
        self.frame.Bind(wx.EVT_BUTTON, self.OnDetectRootFolders, id=xrc.XRCID("btnDetectRootFolders"))

        self.frame.Bind(wx.EVT_BUTTON, self.OnSetCMakePath, id=xrc.XRCID("btnSetCMakePath"))
        self.frame.Bind(wx.EVT_BUTTON, self.OnSelectCSnakeFile, id=xrc.XRCID("btnSelectCSnakeFile"))
        self.frame.Bind(wx.EVT_BUTTON, self.OnSetIDEPath, id=xrc.XRCID("btnSetIDEPath"))
        self.frame.Bind(wx.EVT_BUTTON, self.OnSetPythonPath, id=xrc.XRCID("btnSetPythonPath"))
        self.frame.Bind(wx.EVT_BUTTON, self.OnSetTextEditorPath, id=xrc.XRCID("btnSetTextEditorPath"))
        self.frame.Bind(wx.EVT_BUTTON, self.OnEditCSnakeFile, id=xrc.XRCID("btnEditCSnakeFile"))

        self.frame.Bind(wx.EVT_BUTTON, self.RefreshProjects, id=xrc.XRCID("btnForceRefreshProjects"))
        self.btnForceRefreshProjects = xrc.XRCCTRL(self.frame, "btnForceRefreshProjects")
        self.btnSetIDEPath = xrc.XRCCTRL(self.frame, "btnSetIDEPath")
        self.btnSetCMakePath = xrc.XRCCTRL(self.frame, "btnSetCMakePath")
        self.btnUpdateListOfTargets = xrc.XRCCTRL(self.frame, "btnUpdateListOfTargets")
        self.btnCreateCMakeFilesAndRunCMake = xrc.XRCCTRL(self.frame, "btnCreateCMakeFilesAndRunCMake")
        self.btnOnlyCreateCMakeFiles = xrc.XRCCTRL(self.frame, "btnOnlyCreateCMakeFiles")
        self.btnConfigureThirdPartyFolder = xrc.XRCCTRL(self.frame, "btnConfigureThirdPartyFolder")
        self.btnInstallFilesToBuildFolder = xrc.XRCCTRL(self.frame, "btnInstallFilesToBuildFolder")
        self.btnLaunchIDE = xrc.XRCCTRL(self.frame, "btnLaunchIDE")
        self.btnLaunchIDEThirdParty = xrc.XRCCTRL(self.frame, "btnLaunchIDEThirdParty")
        self.btnEditCSnakeFile = xrc.XRCCTRL(self.frame, "btnEditCSnakeFile")
        
        self.checkListProjects = xrc.XRCCTRL(self.frame, "checkListProjects")
        self.checkListProjects.Bind(wx.EVT_CHECKLISTBOX, self.OnCheckListProjectsEvent, self.checkListProjects)
        
        self.frame.Bind(wx.EVT_BUTTON, self.OnRemoveRootFolder, id=xrc.XRCID("btnRemoveRootFolder"))
        self.frame.Bind(wx.EVT_COMBOBOX, self.OnSelectRecentlyUsed, id=xrc.XRCID("cmbCSnakeFile"))
        self.frame.Bind(wx.EVT_BUTTON, self.OnUpdateListOfTargets, id=xrc.XRCID("btnUpdateListOfTargets"))
        self.frame.Bind(wx.EVT_BUTTON, self.OnCreateCMakeFilesAndRunCMake, id=xrc.XRCID("btnCreateCMakeFilesAndRunCMake"))
        self.frame.Bind(wx.EVT_BUTTON, self.OnOnlyCreateCMakeFiles, id=xrc.XRCID("btnOnlyCreateCMakeFiles"))
        self.frame.Bind(wx.EVT_BUTTON, self.OnConfigureThirdPartyFolder, id=xrc.XRCID("btnConfigureThirdPartyFolder"))
        self.frame.Bind(wx.EVT_BUTTON, self.OnInstallFilesToBuildFolder, id=xrc.XRCID("btnInstallFilesToBuildFolder"))
        self.frame.Bind(wx.EVT_BUTTON, self.OnLaunchIDE, id=xrc.XRCID("btnLaunchIDE"))
        self.frame.Bind(wx.EVT_BUTTON, self.OnLaunchIDEThirdParties, id=xrc.XRCID("btnLaunchIDEThirdParty"))
        self.frame.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED, self.OnNoteBookPageChanged, id=xrc.XRCID("noteBook"))
        
    def InitFrameHelp(self):
        self.frameHelp = self.res.LoadFrame(None, "frmHelp")
        self.htmlCSnakeManual = xrc.XRCCTRL(self.frameHelp, "htmlCSnakeManual")

    def OnCSnakeManual(self, event=None):
        url = csnUtility.GetRootOfCSnake() + "/doc/UserManual/CSnakeUserManual.html"
        self.htmlCSnakeManual.LoadPage(url)
        self.frameHelp.SetSize([800, 550])
        self.frameHelp.Show()		
        
    def OnNoteBookPageChanged(self, event):
        if self.noteBook.GetPageText(self.noteBook.GetSelection()) == "Select Projects":
            self.SelectProjects()
        
    def InitMenu(self):
        self.frame.Bind(wx.EVT_MENU, self.OnContextNew, id=xrc.XRCID("mnuContextNew"))
        self.frame.Bind(wx.EVT_MENU, self.OnContextOpen, id=xrc.XRCID("mnuContextOpen"))
        self.frame.Bind(wx.EVT_MENU, self.OnContextCreateACopy, id=xrc.XRCID("mnuContextCreateACopy"))
        self.frame.Bind(wx.EVT_MENU, self.OnContextRename, id=xrc.XRCID("mnuContextRename"))
        self.frame.Bind(wx.EVT_MENU, self.OnContextAbandonChanges, id=xrc.XRCID("mnuContextAbandonChanges"))
        self.frame.Bind(wx.EVT_MENU, self.OnExit, id=xrc.XRCID("mnuExit"))
        self.frame.Bind(wx.EVT_MENU, self.OnImportExistingSourceFolder, id=xrc.XRCID("mnuImportFolder"))
        self.frame.Bind(wx.EVT_MENU, self.OnCSnakeManual, id=xrc.XRCID("mnuCSnakeManual"))
        self.frame.Bind(wx.EVT_MENU, self.OnAbout, id=xrc.XRCID("mnuAbout"))
        
    def Initialize(self):
        """
        Initializes the application.
        """
        self.ParseCommandLine()
        if not self.commandLineOptions.console:
            self.RedirectStdOut()
        self.PrintWelcomeMessages()
        self.InitializeHandlerAndOptions()    
        self.UpdateGUIAndSaveContextAndOptions()
        
    def Warn(self, message):
        if message is None:
            return
        """ Shows a warning message to the user. ToDo: do some more fancy than print."""
        print message + "\n"
        
    def Error(self, message):
        """ Shows an error message to the user. ToDo: do some more fancy than print."""
        if message is None:
            return
        print message + "\n"

    def Report(self, message):
        if message is None:
            return
        print message + "\n"

    def BackupContextFile(self):
        """ Creates a backup of the current context, so that the user can later abandon all his changes. """
        self.contextBeforeEditingFilename = "%s/contextBeforeEditing" % self.thisFolder
        try:
            shutil.copy(self.options.contextFilename, self.contextBeforeEditingFilename)
        except:
            message = "Warning: could not copy %s to backup location %s" % (self.options.contextFilename, self.contextBeforeEditingFilename)
            self.Warn(message)

    def SetStatus(self, message):
        self.statusBar.SetFields([message])
        if message != "":
            wx.BeginBusyCursor()
        else:
            wx.EndBusyCursor()
    
    def LoadIcon(self):
        iconFile = csnUtility.GetRootOfCSnake() + "/resources/Laticauda_colubrina.ico"
        self.icon = wx.Icon(iconFile, wx.BITMAP_TYPE_ICO)
        self.frame.SetIcon(self.icon)
    
    def ParseCommandLine(self):
        parser = OptionParser()
        parser.add_option("-c", "--console", dest="console", default=False, help="print all messages to the console window")
        (self.commandLineOptions, self.commandLineArgs) = parser.parse_args()
    
    def RedirectStdOut(self):
        # redirect std out
        self.redir=RedirectText(self.textLog)
        sys.stdout=self.redir
        sys.stderr=self.redir

    def PrintWelcomeMessages(self):
        self.Report("CSnake version = %s\n" % csnBuild.version)

    def SaveOptions(self):
        self.options.Save(self.optionsFilename)
    
    def InitializeHandlerAndOptions(self):
        # convert existing options, or create a new options file
        if os.path.exists(self.optionsFilename):
            self.converter.ConvertOptions()
        else:
            self.SaveOptions()
        
        self.options.Load(self.optionsFilename)

        # determine context filename to be used
        if len(self.commandLineArgs) >= 1:
            self.options.contextFilename = self.commandLineArgs[0]
            
        # if context does not exist, create a default one
        if not os.path.isfile(self.options.contextFilename):
            self.options.contextFilename = "%s/default.csnakecontext" % self.thisFolder
            self.InitializeContext(self.options.contextFilename)

        if not os.path.isdir(self.options.lastUsedImportFolder):
            self.options.lastUsedImportFolder = csnUtility.NormalizePath("%s/../examples" % self.resourcesFolder)
        
        self.options.Save(self.optionsFilename)
        
        # load the context
        if self.LoadContext():
            self.BackupContextFile()

    def CopyGUIToContextAndOptions(self):
        """ Copy all GUI fields to the current context """
        self.binder.UpdateBuddies()
        
    def SaveContextAndOptions(self):
        """
        Copy context from the widget controls to self.context.
        If filename is not "", save current configuration context (source folder/build folder/etc) 
        to filename.
        """
        self.CopyGUIToContextAndOptions()
        self.context.pythonPath = self.options.GetPythonPath()
        
        try:
            self.context.Save(self.options.contextFilename)
            self.frame.SetTitle("CSnake GUI - %s" % self.options.contextFilename)
        except:
            self.Error("Sorry, CSnakeGUI could not save the context to %s.\nPlease check if another program is locking this file.\n" % self.options.contextFilename)
            
        try:
            self.options.Save(self.optionsFilename)
        except:
            self.Error("Sorry, CSnakeGUI could not save the options to %s\n. Please check if another program is locking this file.\n" % self.optionsFilename)
            
    def OnCreateCMakeFilesAndRunCMake(self, event):
        self.action = self.ActionCreateCMakeFilesAndRunCMake
        self.DoAction()
        
    def OnDetectRootFolders(self, event):
        (additionalRootFolders, thirdPartyRootFolder) = self.handler.FindAdditionalRootFolders()
        if thirdPartyRootFolder != "" and self.context.thirdPartyRootFolder != "":
            message = "Replace current third party root folder (%s) with %s?" % (self.context.thirdPartyRootFolder, thirdPartyRootFolder)
            dlg = wx.MessageDialog(self.frame, message, style = wx.YES_NO)
            if dlg.ShowModal() != wx.ID_YES:
                thirdPartyRootFolder = ""
        
        self.ExtendRootFolders(additionalRootFolders, thirdPartyRootFolder)
    
    def ExtendRootFolders(self, additionalRootFolders, thirdPartyRootFolder):
        self.context.rootFolders.extend(additionalRootFolders)
        if thirdPartyRootFolder != "":
            self.context.thirdPartyRootFolder = thirdPartyRootFolder
        self.UpdateGUIAndSaveContextAndOptions()
    
    def FindAdditionalRootFolders(self, onlyForNewInstance=False):
        if onlyForNewInstance and self.options.IsCSnakeFileInRecentlyUsed(self.context.csnakeFile):
            return
        
        (additionalRootFolders, thirdPartyRootFolder) = self.handler.FindAdditionalRootFolders()
        if len(additionalRootFolders) or thirdPartyRootFolder != "":
            
            noThirdPartyRootFolderYetButFoundOne = self.context.thirdPartyRootFolder == "" and thirdPartyRootFolder != ""
            if len(additionalRootFolders):
                message =  "CSnakeGUI found additional root folders which are likely to be necessary for csnake file %s.\n" % self.context.csnakeFile
                message += "Should CSnakeGUI add the following root folders?\n\n"
                for folder in additionalRootFolders:
                    message += folder + "\n"
                    
                message += "\n\nIf you choose No, you can later add the above root folders using the Detect button.\n"
                dlg = wx.MessageDialog(self.frame, message, style = wx.YES_NO)
                if dlg.ShowModal() == wx.ID_YES:
                    self.ExtendRootFolders(additionalRootFolders, "")

            if thirdPartyRootFolder != "":
                message =  "CSnakeGUI found a third party root folder that is likely to be necessary for csnake file %s.\n" % self.context.csnakeFile
                if self.context.thirdPartyRootFolder != "":
                    message += "Should CSnakeGUI replace the current third party root folder (%s) with %s?" % (self.context.thirdPartyRootFolder, thirdPartyRootFolder)
                else:
                    message += "Should CSnakeGUI add the following third party root folder?\n\n"
                    message += thirdPartyRootFolder + "\n"
            
                message += "\n\nIf you choose No, you can later add the above root folder using the Detect button.\n"
            
                dlg = wx.MessageDialog(self.frame, message, style = wx.YES_NO)
                if dlg.ShowModal() == wx.ID_YES:
                    self.ExtendRootFolders([], thirdPartyRootFolder)
            
    def ActionCreateCMakeFilesAndRunCMake(self):
        self.ActionCreateCMakeFiles(True)
        
    def OnOnlyCreateCMakeFiles(self, event):
        self.action = self.ActionOnlyCreateCMakeFiles
        self.DoAction()
        
    def ActionOnlyCreateCMakeFiles(self):
        self.ActionCreateCMakeFiles(False)
        
    def ActionCreateCMakeFiles(self, alsoRunCMake=True):
        self.FindAdditionalRootFolders(True)
        if self.handler.ConfigureProjectToBuildFolder(_alsoRunCMake=alsoRunCMake, _callback=self):
            self.UpdateRecentlyUsedCSnakeFiles()
            if self.options.automaticallyInstallFiles:
                self.handler.InstallFilesToBuildFolder(onlyNewerFiles=True)
            if self.context.instance.lower() == "gimias":
                self.ProposeToDeletePluginDlls(self.handler.GetListOfSpuriousPluginDlls(_reuseInstance = True))
                
    def OnConfigureThirdPartyFolder(self, event):
        self.action = self.ActionConfigureThirdPartyFolder
        self.DoAction()
        
    def ActionConfigureThirdPartyFolder(self):
        self.handler.ConfigureThirdPartyFolder()
        
    def OnInstallFilesToBuildFolder(self, event):
        self.action = self.ActionInstallFilesToBuildFolder
        self.DoAction()
        
    def ActionInstallFilesToBuildFolder(self):
        self.FindAdditionalRootFolders(True)
        if not self.handler.InstallFilesToBuildFolder():
            self.Error("Error while installing files.")

    def ClearTextLog(self):
        self.textLog.Clear()
        self.textLog.Refresh()
        self.textLog.Update()
        
    def DoAction(self):
        self.ClearTextLog()
        
        self.Report("--- Working, patience please... ---")
        self.SaveContextAndOptions()
        startTime = time.time()

        success = False
        self.SetStatus("Processing...")
        try:
            self.action()
            success = True
        except (AssertionError, Exception), e:
            traceback.print_exc()
            self.Error(str(e))
            
        self.SetStatus("")
        elapsedTime = time.time() - startTime
        self.Report("--- Done (%d seconds) ---" % elapsedTime)
        self.UpdateGUIAndSaveContextAndOptions()
        
        #self.Restart()
        
    def Restart(self):
        """ Restart the application """
        arglist = []
        if( os.path.splitext(os.path.basename(sys.executable))[0].lower() == "python" ):
            arglist = [sys.executable]
            arglist.extend(sys.argv)
        os.execv(sys.executable, arglist)
                
    def OnSelectCSnakeFile(self, event):
        """
        Select file containing the project that should be configured.
        """
        dlg = wx.FileDialog(None, "Select CSnake file", wildcard = "*.py")
        if dlg.ShowModal() == wx.ID_OK:
            self.context.csnakeFile = dlg.GetPath()
            self.UpdateGUIAndSaveContextAndOptions()

    def SetBuildFolder(self, folder):
        self.context.buildFolder = folder
        
    def SetInstallFolder(self, folder):
        self.context.installFolder = folder
        
    def SetThirdPartyRootFolder(self, folder):
        self.context.thirdPartyRootFolder = folder
        
    def SetThirdPartyBuildFolder(self, folder):
        self.context.thirdPartyBuildFolder = folder
        
    def SetKDevelopProjectFolder(self, folder):
        self.context.kdevelopProjectFolder = folder
            
    def AddRootFolder(self, folder):
        """
        Add folder where CSnake files must be searched to context.rootFolders.
        """
        self.context.rootFolders.append(folder)
        self.UpdateGUIAndSaveContextAndOptions()
        self.lbRootFolders.SetSelection(len(self.context.rootFolders) - 1)

    def OnRemoveRootFolder(self, event):
        """
        Remove folder where CSnake files must be searched from context.rootFolders.
        """
        selected = self.lbRootFolders.GetSelection()
        self.context.rootFolders.remove(self.lbRootFolders.GetStringSelection())
        self.UpdateGUIAndSaveContextAndOptions()
        self.lbRootFolders.SetSelection(min(selected, self.lbRootFolders.GetCount()-1))
            
    def OnContextNew(self, event):
        """
        Let the user load a context.
        """
        dateString = time.strftime("%a%d%B%Y")
        self.options.contextFilename = "%s/%s.csnakecontext" % (self.thisFolder, dateString)
        while os.path.exists(self.options.contextFilename):
            dateString = time.strftime("%a%d%B%Y_%H;%M;%S")
            self.options.contextFilename = "%s/%s.csnakecontext" % (self.thisFolder, dateString)
        self.SaveOptions()
        
        self.InitializeContext(self.options.contextFilename)
        loaded = self.LoadContext()
        assert loaded, "Logical error: could not load new context %s\n" % self.options.contextFilename
        self.BackupContextFile()
        self.options.ClearRecentlyUsed()
        self.UpdateGUIAndSaveContextAndOptions()
        
    def OnContextOpen(self, event):
        """
        Let the user load a context.
        """
        defaultDir = os.path.dirname(self.options.contextFilename)
        dlg = wx.FileDialog(None, "Select CSnake context file", wildcard=csnakeFilesWildCard, defaultDir=defaultDir)
        if dlg.ShowModal() == wx.ID_OK:
            self.options.contextFilename = dlg.GetPath()
            self.SaveOptions()
            if self.LoadContext():
                self.BackupContextFile()

    def OnContextCreateACopy(self, event):
        """
        Let the user save the context.
        """
        (base, ext) = os.path.splitext(self.options.contextFilename)
        self.options.contextFilename = base + "Copy" + ext
        self.SaveContextAndOptions()

    def OnContextRename(self, event):
        """
        Let the user save the context.
        """
        defaultDir = os.path.dirname(self.options.contextFilename)
        defaultFile = self.options.contextFilename
        dlg = wx.FileDialog(None, "Move CSnake context to...", defaultDir=defaultDir, defaultFile=defaultFile, wildcard=csnakeFilesWildCard, style=wx.FD_SAVE)
        if dlg.ShowModal() == wx.ID_OK:
            os.rename(self.options.contextFilename, dlg.GetPath())
            self.options.contextFilename = dlg.GetPath()
            self.SaveOptions()
            self.LoadContext()

    def GetCompilerComboBoxItems(self):
        result = []
        result.append("Visual Studio 7 .NET 2003")
        result.append("Visual Studio 8 2005")
        result.append("Visual Studio 8 2005 Win64")
        result.append("Visual Studio 9 2008")
        result.append("Visual Studio 9 2008 Win64")
        result.append("KDevelop3")
        result.append("Unix Makefiles")        
        return result

    def GetCMakeVersionComboBoxItems(self):
        result = []
        result.append("2.4")
        result.append("2.6")        
        return result
    
    def GetBuildTypeComboBoxItems(self):
        result = []
        result.append("DebugAndRelease")
        result.append("Release")
        result.append("Debug")
        return result
    
    def GetCSnakeFileComboBoxItems(self):
        result = list()
        count = 0
        for x in self.options.recentlyUsed:
            result.append("%s - In %s" % (x.instance, x.csnakeFile))
            count += 1
            if count >= 10:
                break
        return result
    
    def UpdateGUIAndSaveContextAndOptions(self):
        """ Refreshes the GUI based on the current context. Also saves the current context to the contextFilename """
        self.options.FindApplicationPaths()

        self.binder.UpdateControls()

        # some rootfolder must always be selected
        if self.lbRootFolders.GetSelection() == -1 and self.lbRootFolders.GetCount():
            self.lbRootFolders.SetSelection(0)
        
        self.btnSetIDEPath.SetLabel("Set path to %s" % self.options.GetIDEPrettyName())
        self.btnSetCMakePath.SetLabel("Set path to %s" % self.options.GetCMakePrettyName())
        for kdevelopItem in self.kdevelopItems:
            kdevelopItem.Show( self.context.compiler in ("KDevelop3", "Unix Makefiles") )
        
        hasIDE = os.path.isfile(self.options.idePath)
        hasPython = os.path.isfile(self.options.pythonPath)
        hasTextEditor = os.path.isfile(self.options.textEditorPath)
        hasCMake = os.path.isfile(self.options.cmakePath)
        hasCSnakeFile = os.path.isfile(self.context.csnakeFile)
        hasInstance = hasCSnakeFile and self.context.instance != ""
        
        self.btnUpdateListOfTargets.Enable(hasCSnakeFile)
        self.btnEditCSnakeFile.Enable(hasTextEditor)
        self.btnCreateCMakeFilesAndRunCMake.Enable(hasInstance and hasCMake and self.context.buildFolder != "")
        self.btnOnlyCreateCMakeFiles.Enable(hasInstance and self.context.buildFolder != "")
        self.btnConfigureThirdPartyFolder.Enable(hasCMake and self.context.thirdPartyBuildFolder != "" and os.path.isdir(self.context.thirdPartyRootFolder))
        self.btnInstallFilesToBuildFolder.Enable(hasInstance and self.context.buildFolder != "")
        self.btnLaunchIDE.Enable(hasIDE and self.context.buildFolder != "")
        self.btnLaunchIDEThirdParty.Enable(hasIDE and self.context.thirdPartyBuildFolder != "")
        
        self.SetTextColour(self.txtCMakePath, hasCMake)
        self.SetTextColour(self.txtTextEditorPath, hasTextEditor)
        self.SetTextColour(self.txtIDEPath, hasIDE)
        self.SetTextColour(self.txtPythonPath, hasPython)
        self.SetTextColour(self.cmbCSnakeFile, hasCSnakeFile)

        reportProblemMessage = ""
        if not hasCMake: 
            reportProblemMessage = "CMake not found. Please check the path to CMake in the options tab."
        elif not hasCSnakeFile:
            reportProblemMessage = "No valid CSnake file. Please check the CSnake File field in the Context tab."
        elif not hasInstance:
            reportProblemMessage = "Instance field not set. Please check the Instance field in the Context tab."
        elif self.context.buildFolder == "":
            reportProblemMessage = "Build Folder not set. Please check the Build Folder field in the Context tab."
        elif not hasIDE:
            reportProblemMessage = "IDE not found. Setting the IDE path is optional, and can be found in the Options tab."
        elif not hasPython:
            reportProblemMessage = "Python not found. Setting the Python path is optional, and can done in the Options tab."
        elif not hasTextEditor:
            reportProblemMessage = "Text editor not found. Setting the text editor path is optional, and can done in the Options tab."

        self.statusBar.SetFields([reportProblemMessage])
            
        self.SaveContextAndOptions()
        wx.CallAfter(self.frame.Update)

    def SetTextColour(self, control, isValid):
        if isValid:
            control.SetForegroundColour(wx.BLACK)
        else:
            control.SetForegroundColour(wx.RED)

    def UpdateGUIAndSaveContextAndOptionsWithLock(self):
        """ 
        This function calls UpdateGUIAndSaveContextAndOptions and prevents recursive loops (in which
        UpdateGUIAndSaveContextAndOptions calls itself).
        Normally, calling UpdateGUIAndSaveContextAndOptions should not yield such loops.
        To keep the application logic healthy, only use this function when you know there is going to be a loop.
        """
        if not self.locked:
            self.locked = True
            self.UpdateGUIAndSaveContextAndOptions()
            self.locked = False

    def LoadContext(self):
        """
        Load configuration context from contextFilename.
        """
        if not os.path.exists(self.options.contextFilename):
            self.Error("CSnakeGUI could not find context file %s" % self.options.contextFilename)
            return False
        
        try:
            if not self.converter.Convert(self.options.contextFilename):
                self.Error("CSnakeGUI tried to open %s, but this file is not a valid context file" % self.options.contextFilename)
                return False
            self.options.Load(self.optionsFilename)
        except:
            self.Error("CSnakeGUI tried to open %s, but this file is not a valid context file" % self.options.contextFilename)
            return False

        self.SetContext(self.handler.LoadContext(self.options.contextFilename))
        self.frame.SetTitle("CSnake GUI - %s" % self.options.contextFilename)
        self.UpdateGUIAndSaveContextAndOptions()
        
        return True

    def SetContext(self, context):
        self.context = context
        self.binder.SetBuddyClass("context", self.context)
        
    def OnUpdateListOfTargets(self, event):
        self.ClearTextLog()
        self.FindAdditionalRootFolders(True)

        try:
            self.SetStatus("Retrieving list of targets")
            self.listOfPossibleTargets = self.handler.GetListOfPossibleTargets()
        finally:
            self.SetStatus("")

        if len(self.listOfPossibleTargets) and not self.context.instance in self.listOfPossibleTargets:
            self.context.instance = self.listOfPossibleTargets[0]
        self.UpdateGUIAndSaveContextAndOptions()

    def GetInstanceComboBoxItems(self):
        return self.listOfPossibleTargets
            
    def ProposeToDeletePluginDlls(self, spuriousDlls):
        if len(spuriousDlls) == 0:
            return
            
        dllMessage = ""
        for x in spuriousDlls:
            dllMessage += ("%s\n" % x)
            
        message = "In the build results folder, CSnake found GIMIAS plugins that have not been configured.\nThe following plugin dlls may crash GIMIAS:\n\n%s\nDelete them?" % dllMessage
        dlg = wx.MessageDialog(self.frame, message, style = wx.YES_NO)
        if dlg.ShowModal() != wx.ID_YES:
            return
            
        for dll in spuriousDlls:
            os.remove(dll)

    def OnLaunchIDE(self, event = None):
        argList = [self.options.idePath, self.handler.GetTargetSolutionPath()]
        subprocess.Popen(argList)
    
    def OnLaunchIDEThirdParties(self, event = None):
        argList = [self.options.idePath, self.handler.GetThirdPartySolutionPath()]
        subprocess.Popen(argList)
    
    def OnExit(self, event = None):
        if not self.destroyed:
            self.destroyed = True
            self.CopyGUIToContextAndOptions()
            if os.path.exists(self.options.contextFilename):
                self.SaveContextAndOptions()
            self.frameHelp.Destroy()
            self.frame.Destroy()

    def OnSelectRecentlyUsed(self, event):
        item = self.cmbCSnakeFile.GetSelection()
        context = self.options.recentlyUsed[item]
        self.context.csnakeFile = context.csnakeFile
        self.context.instance = context.instance
        self.UpdateGUIAndSaveContextAndOptions()

    def OnContextAbandonChanges(self, event):
        try:
            shutil.copy(self.contextBeforeEditingFilename, self.options.contextFilename)
            self.LoadContext()
        except:
            self.Warn("Sorry, could not copy %s to %s. You can try copying the file manually" % (self.contextBeforeEditingFilename, self.options.contextFilename))

    def OnSetCMakePath(self, event):
        """
        Let the user select where CSnake is located.
        """
        dlg = wx.FileDialog(None, "Select path to CMake")
        if dlg.ShowModal() == wx.ID_OK:
            self.options.cmakePath = dlg.GetPath()
            self.UpdateGUIAndSaveContextAndOptions()

    def OnSetPythonPath(self, event):
        dlg = wx.FileDialog(None, "Select path to Python")
        if dlg.ShowModal() == wx.ID_OK:
            self.options.pythonPath = dlg.GetPath()
            self.UpdateGUIAndSaveContextAndOptions()

    def OnSetTextEditorPath(self, event):
        dlg = wx.FileDialog(None, "Select path to a text editor")
        if dlg.ShowModal() == wx.ID_OK:
            self.options.textEditorPath = dlg.GetPath()
            self.UpdateGUIAndSaveContextAndOptions()

    def OnEditCSnakeFile(self, event=None):
        if not os.path.isfile(self.options.textEditorPath):
            self.Warn("Please set a valid text editor path in the Options tab.")
            return
            
        argList = [self.options.textEditorPath, self.context.csnakeFile]
        subprocess.Popen(argList)
    
    def OnSetIDEPath(self, event):
        dlg = wx.FileDialog(None, "Select path to Python")
        if dlg.ShowModal() == wx.ID_OK:
            self.options.idePath = dlg.GetPath()
            self.UpdateGUIAndSaveContextAndOptions()

    def SelectProjects(self, forceRefresh = False):
        # get list of ALL the categories on which the user can filter
        previousFilter = self.context.filter 
        self.context.filter = list()
            
        if self.helpTextSelectProjects: 
            self.helpTextSelectProjects.Destroy()
        
        # create list of checkboxes for the categories
        self.checkListProjects.Clear()
        self.panelSelectProjects.GetSizer().Clear()
        self.panelSelectProjects.GetSizer().Add(self.checkListProjects, proportion=1, flag=wx.EXPAND | wx.ALL, border=5)
        self.panelSelectProjects.GetSizer().Add(self.btnForceRefreshProjects, flag=wx.ALL, border=5)

        success = False
        self.SetStatus("Retrieving projects from %s..." % self.context.csnakeFile)
        try:
            self.categories = self.handler.GetCategories(forceRefresh)
            success = True
        except:
            try:
                self.categories = self.handler.GetCategories(True)
                success = True
            except:
                pass

        self.SetStatus("")
        if not success:    
            message = "Could not load project dependencies for instance %s from file\n%s" % (self.context.instance, self.context.csnakeFile)
            message = message + "\nPlease check the fields 'CSnake File' and 'Instance', and the contents of the CSnake file."
            self.helpTextSelectProjects = wx.StaticText(self.panelSelectProjects, -1, message)
            self.panelSelectProjects.GetSizer().Insert(0, self.helpTextSelectProjects, border=5, flag=wx.ALL)
            self.panelSelectProjects.Layout()
            return
        
        self.context.filter = previousFilter
        self.catToIndex = dict()
        for category in sorted(self.categories):
            self.checkListProjects.Append(category)
            self.catToIndex[category] = self.checkListProjects.GetCount() - 1
            self.checkListProjects.Check(self.checkListProjects.GetCount() - 1, not category in self.context.filter )

        if len(self.categories) == 0:
            self.helpTextSelectProjects = wx.StaticText(self.panelSelectProjects, -1, "For instance %s there are no optional projects to select" % self.context.instance)
            self.panelSelectProjects.GetSizer().Insert(0, self.helpTextSelectProjects, border=5, flag=wx.ALL)
            
        # create list of checkboxes for the 'super categories' (which are groups of normal categories, such as Tests)
        self.superToIndex = dict()
        for super in self.context.subCategoriesOf.keys():
            value = True
            for sub in self.context.subCategoriesOf[super]:
                    value = value and (not sub in self.context.filter)
                    
            self.checkListProjects.Append(super)
            self.superToIndex[super] = self.checkListProjects.GetCount() - 1
            self.checkListProjects.Check(self.checkListProjects.GetCount() - 1, value )
            
        self.panelSelectProjects.Layout()
        
    def OnCheckListProjectsEvent(self, event):
        """ 
        Respond to checking a supercategory (such as Tests or Demos). Results in (un)checking all subcategories in that
        supercategory.
        """
        clickedSuperCategory = False
        for super in self.context.subCategoriesOf.keys():
            index = self.superToIndex[super]
            clickedSuperCategory = clickedSuperCategory or index == event.GetInt()
            value = self.checkListProjects.IsChecked(index)
                    
            if clickedSuperCategory:
                for category in sorted(self.categories):
                    if category in self.context.subCategoriesOf[super]:
                        self.checkListProjects.Check(self.catToIndex[category], value)
                    
        for category in sorted(self.categories):
            if category in self.context.filter:
                self.context.filter.remove(category)
            if not self.checkListProjects.IsChecked(self.catToIndex[category]):
                self.context.filter.append(category)

    def RefreshProjects(self, event):
        self.SelectProjects(forceRefresh=True)
    
    def UpdateRecentlyUsedCSnakeFiles(self):
        self.options.AddRecentlyUsed(self.context.instance, self.context.csnakeFile)

    def OnAbout(self, event=None):
        dlg = wx.AboutDialogInfo()
        dlg.AddDeveloper("Maarten Nieber")
        dlg.SetDescription("A GUI for CSnake: a configuration tool for C/C++ source code\nbuilt upon Python and CMake.")
        dlg.SetIcon(self.icon)
        dlg.SetName("CSnakeGUI")
        dlg.SetVersion(str(csnBuild.version))
        wx.AboutBox(dlg)
        
    def OnImportExistingSourceFolder(self, event=None):
        dlg = csnImportWizard.ImportWizard(self.res, defaultDir=self.options.lastUsedImportFolder)
        if dlg.ShowModal() == wx.ID_OK:
            path = dlg.GetPath()
            type = dlg.GetProjectType()
            self.options.lastUsedImportFolder = path
            importer = csnCreate.FolderImporter()
            importer.Import(path, type)
            self.context.csnakeFile = FormatFilename(importer.context.csnakeFile)
            self.context.instance = importer.context.instance
            self.SaveContextAndOptions()
            self.FindAdditionalRootFolders(True)
            self.UpdateRecentlyUsedCSnakeFiles()
            self.UpdateGUIAndSaveContextAndOptions()
        
    def InitializeContext(self, filename):
        self.options.FindApplicationPaths()
        csnContext.Context().Save(filename)
        context = csnContext.Load(filename)

        if self.options.cmake24Data.path != "":
            context.cmakeVersion = "2.4"
        elif self.options.cmake26Data.path != "":
            context.cmakeVersion = "2.6"

        if self.options.kdevelop3Data.path != "":
            context.compiler = "KDevelop3"
        elif self.options.visualStudio2003Data.path != "":
            context.compiler = "Visual Studio 7 .NET 2003"
        elif self.options.visualStudio2005Data.path != "":
            context.compiler = "Visual Studio 8 2005"
        elif self.options.visualStudio2008Data.path != "":
            context.compiler = "Visual Studio 9 2008"
        context.Save(filename)
    
if __name__ == "__main__":
    app = CSnakeGUIApp(0)
    app.MainLoop()
