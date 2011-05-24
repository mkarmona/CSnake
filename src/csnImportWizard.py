# Author: Maarten Nieber

import wx
from wx import xrc
import os
        
class ImportWizard(object):
    def __init__(self, res, defaultDir=None):
        self.destroyed = False
        self.locked = False
        self.importFolder = ""
        self.dlg = res.LoadDialog(None, "dialogImportSourceFolder")
        self.dlg.txtImportFolder = xrc.XRCCTRL(self.dlg, "txtImportFolder")

        self.dlg.dirControlImportFolder = xrc.XRCCTRL(self.dlg, "dirControlImportFolder")
        self.dlg.dirControlImportFolder.GetTreeCtrl().Bind(wx.EVT_TREE_SEL_CHANGED, self.OnImportFolderSelectionChanged, self.dlg.dirControlImportFolder.GetTreeCtrl())
        self.dlg.dirControlImportFolder.SetPath(defaultDir)

        self.dlg.btnImport = xrc.XRCCTRL(self.dlg, "btnImport")
        self.dlg.radioBoxProjectType = xrc.XRCCTRL(self.dlg, "radioBoxProjectType")

        self.dlg.txtImportFolder.Bind(wx.EVT_KILL_FOCUS, self.OnTextImportFolderChanged, self.dlg.txtImportFolder)
        self.dlg.txtImportFolder.Bind(wx.EVT_TEXT_ENTER, self.OnTextImportFolderChanged, self.dlg.txtImportFolder)

        self.dlg.btnCancelImport = xrc.XRCCTRL(self.dlg, "btnCancelImport")
        self.dlg.btnImport.SetId(wx.ID_OK)
        self.dlg.btnCancelImport.SetId(wx.ID_CANCEL)
        self.dlg.SetSize([800, 550])
        self.dlg.Bind(wx.EVT_CLOSE, self.OnExit, self.dlg)

    def OnExit(self, event = None):
        if not self.destroyed:
            self.destroyed = True
            self.dlg.Destroy()

    def ShowModal(self):
        return self.dlg.ShowModal()

    def GetPath(self):
        return self.dlg.dirControlImportFolder.GetPath()

    def GetProjectType(self):
        values = dict()
        values["Executable"] = "executable"
        values["Static library"] = "library"
        values["Dynamic library"] = "dll"
        return values[self.dlg.radioBoxProjectType.GetStringSelection()]

    def OnTextImportFolderChanged(self, event=None):
        path = self.dlg.txtImportFolder.GetValue()
        if os.path.isfile(path):
            path = os.path.dirname(path)
        if os.path.exists(path):
            self.importFolder = path
            self.UpdateGUI()

    def OnImportFolderSelectionChanged(self, event=None):
        self.importFolder = self.dlg.dirControlImportFolder.GetPath()
        self.UpdateGUI()

    def UpdateGUI(self):
        if not self.locked:
            self.locked = True
            self.dlg.txtImportFolder.SetValue(self.importFolder)
            self.dlg.dirControlImportFolder.SetPath(self.importFolder)
            self.locked = False
