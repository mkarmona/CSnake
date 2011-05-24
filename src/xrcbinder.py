# Author: Maarten Nieber

import wx
from wx import xrc

def DefaultValueTransform(value):
    return value

def DefaultAfterUpdateBuddyHook():
    pass
    
class BoundControl:
    """
    Base class for a control that is bound to a buddy field in a buddy class.
    This class is used by a binder (see ControlBinder class).
    When the buddy value changes, calling binder.UpdateControls will update the control.
    When the control value changes, the binder will transform the control value, update the buddy field (see SetBuddyValue)
    and call self.afterUpdateBuddyHook (to do any other actions after updating the buddy).
    """
    def __init__(self, binder, control, buddyClass = None, buddyField = None):
        self.control = control
        self.buddyClass = buddyClass
        self.buddyField = buddyField
        self.binder = binder
        self.valueTransform = DefaultValueTransform
        self.afterUpdateBuddyHook = DefaultAfterUpdateBuddyHook
        
    def GetBuddyClass(self):
        return self.binder.GetBuddyClass(self)
        
    def HasBuddyValue(self):
        return hasattr(self.GetBuddyClass(), self.buddyField)
        
    def SetBuddyValue(self, value):
        """ Sets the buddy field with the result of calling self.valueTransform on the control value. """
        if self.HasBuddyValue():
            setattr(self.GetBuddyClass(), self.buddyField, self.valueTransform(value))
        
    def GetBuddyValue(self):
        return getattr(self.GetBuddyClass(), self.buddyField)
        
    def UpdateBuddy(self):
        self.UpdateBuddyImpl()
        self.afterUpdateBuddyHook()
        
    def UpdateControl(self):
        self.UpdateControlImpl()
        
    def OnKillFocus(self, event):
        """ User moved from one field to the other, copy latest values to the context """
        self.UpdateBuddy()
        self.UpdateControl()
        event.Skip()
        
class ControlWithField(BoundControl):
    def GetControlValue(self):
        controlValue = self.control.GetValue()
        return controlValue

class TextControl(ControlWithField):
    def __init__(self, binder, control, buddyClass = None, buddyField = None):
        ControlWithField.__init__(self, binder, control, buddyClass, buddyField)
        control.Bind(wx.EVT_KILL_FOCUS, self.OnKillFocus, control)
    
    def UpdateBuddyImpl(self):
        self.SetBuddyValue(self.GetControlValue())

    def UpdateControlImpl(self):
        if self.HasBuddyValue():
            buddyValue = self.GetBuddyValue()
            if self.control.GetValue() != buddyValue:
                self.control.SetValue(buddyValue)
    
class ComboBoxControl(ControlWithField):
    def __init__(self, binder, control, valueListFunctor, buddyClass = None, buddyField = None):
        ControlWithField.__init__(self, binder, control, buddyClass, buddyField)
        self.valueListFunctor = valueListFunctor
        control.Bind(wx.EVT_KILL_FOCUS, self.OnKillFocus, control)
        control.Bind(wx.EVT_COMBOBOX, self.OnSelectItem, control)
    
    def UpdateBuddyImpl(self):
        controlValue = self.GetControlValue()
        if self.control.GetValue() != controlValue:
            self.control.SetValue(controlValue)
        self.SetBuddyValue(controlValue)

    def UpdateControlImpl(self):
        newItems = self.valueListFunctor()
        if self.control.GetItems() != newItems:
            self.control.Clear()
            self.control.SetItems(newItems)
            
        buddyValue = self.GetBuddyValue()
        if self.control.GetValue() != buddyValue:
            self.control.SetValue(buddyValue)
            wx.CallAfter(self.control.SetValue, self.GetBuddyValue())
        
    def OnSelectItem(self, event):
        """ User moved from one field to the other, copy latest values to the context """
        self.UpdateBuddy()
        event.Skip()
        
class ListBoxControl(BoundControl):
    def __init__(self, binder, control, buddyClass = None, buddyField = None):
        BoundControl.__init__(self, binder, control, buddyClass, buddyField)
        
    def UpdateBuddyImpl(self):
        result = list()
        for i in range( self.control.GetCount() ):
            controlValue = self.control.GetString(i)
            result.append( controlValue )
        self.SetBuddyValue(result)

    def UpdateControlImpl(self):
        buddyValue = self.GetBuddyValue()
        if self.control.GetItems() != buddyValue:
            selected = self.control.GetSelection()
            self.control.Clear()
            for x in buddyValue:
                self.control.Append(x)
            if selected < self.control.GetCount():
                self.control.SetSelection(selected)
        
class CheckBoxControl(BoundControl):
    def __init__(self, binder, control, buddyClass = None, buddyField = None):
        BoundControl.__init__(self, binder, control, buddyClass, buddyField)
        control.Bind(wx.EVT_CHECKBOX, self.OnKillFocus, control)
        
    def UpdateBuddyImpl(self):
        self.SetBuddyValue(self.control.GetValue())

    def UpdateControlImpl(self):
        buddyValue = self.GetBuddyValue()
        if self.control.GetValue() != buddyValue:
            self.control.SetValue(buddyValue)
         
class ControlBinder:
    def __init__(self):
        self.controls = dict()
        self.buddyClassWithName = dict()

    def SetBuddyClass(self, buddyClassName, buddyClass):
        self.buddyClassWithName[buddyClassName] = buddyClass
    
    def AddTextControl(self, control, buddyClass = None, buddyField = None):
        self.controls[control] = (TextControl(self, control, buddyClass, buddyField))

    def AddComboBox(self, control, valueListFunctor, buddyClass = None, buddyField = None):
        self.controls[control] = (ComboBoxControl(self, control, valueListFunctor, buddyClass, buddyField))

    def AddListBox(self, control, buddyClass = None, buddyField = None):
        self.controls[control] = (ListBoxControl(self, control, buddyClass, buddyField))

    def AddCheckBox(self, control, buddyClass = None, buddyField = None):
        self.controls[control] = (CheckBoxControl(self, control, buddyClass, buddyField))

    def GetBuddyClass(self, boundControl):
        return self.buddyClassWithName[boundControl.buddyClass]
    
    def UpdateBuddies(self):
        for boundControl in self.controls.values():
            #print "!!Updating buddy (%s/%s)\n" % (boundControl.buddyClass, boundControl.buddyField)
            boundControl.UpdateBuddy()
            #print "!!Finished\n"

    def UpdateControls(self):
        for boundControl in self.controls.values():
            #print "!!Updating control (%s/%s)\n" % (boundControl.buddyClass, boundControl.buddyField)
            boundControl.UpdateControl()
            #print "!!Finished\n"
         
    def SetValueTransform(self, control, transform):
        self.controls[control].valueTransform = transform
        
    def SetAfterUpdateBuddyHook(self, control, hook):
        self.controls[control].afterUpdateBuddyHook = hook
        
class Binder(ControlBinder):
    def __init__(self, target, defaultContainer = None):
        ControlBinder.__init__(self)
        self.target = target
        self.defaultContainer = defaultContainer
        self.controlWithName = dict()

    def AddTextControl(self, controlName, container = None, buddyClass = None, buddyField = None):
        if container is None:
            container = self.defaultContainer
        setattr(self.target, controlName, xrc.XRCCTRL(container, controlName))
        self.controlWithName[controlName] = getattr(self.target, controlName)
        ControlBinder.AddTextControl(self, self.controlWithName[controlName], buddyClass, buddyField)

    def AddComboBox(self, controlName, valueListFunctor, container = None, buddyClass = None, buddyField = None):
        if container is None:
            container = self.defaultContainer
        setattr(self.target, controlName, xrc.XRCCTRL(container, controlName))
        self.controlWithName[controlName] = getattr(self.target, controlName)
        ControlBinder.AddComboBox(self, self.controlWithName[controlName], valueListFunctor, buddyClass, buddyField)

    def AddListBox(self, controlName, container = None, buddyClass = None, buddyField = None):
        if container is None:
            container = self.defaultContainer
        setattr(self.target, controlName, xrc.XRCCTRL(container, controlName))
        self.controlWithName[controlName] = getattr(self.target, controlName)
        ControlBinder.AddListBox(self, self.controlWithName[controlName], buddyClass, buddyField)

    def AddCheckBox(self, controlName, container = None, buddyClass = None, buddyField = None):
        if container is None:
            container = self.defaultContainer
        setattr(self.target, controlName, xrc.XRCCTRL(container, controlName))
        self.controlWithName[controlName] = getattr(self.target, controlName)
        ControlBinder.AddCheckBox(self, self.controlWithName[controlName], buddyClass, buddyField)

    def SetValueTransform(self, controlName, transform):
        ControlBinder.SetValueTransform(self, self.controlWithName[controlName], transform)

    def SetAfterUpdateBuddyHook(self, controlName, hook):
        ControlBinder.SetAfterUpdateBuddyHook(self, self.controlWithName[controlName], hook)
