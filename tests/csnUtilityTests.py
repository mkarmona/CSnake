## @package csnUtilityTests
# Definition of the csnUtilityTests class.
# \ingroup tests
import unittest
import csnUtility
import os
import commands

class csnUtilityTests(unittest.TestCase):
    """ Unit tests for the csnUtility methods. """
    
    def testNormalizePath(self):
        """ csnUtilityTests: test NormalizePath function. """
        refString = "c:/hallo"

        self.assertEqual( csnUtility.NormalizePath(""), "." )
        self.assertEqual( csnUtility.NormalizePath("."), "." )
        testString1 = "c:/hallo"
        self.assertEqual( csnUtility.NormalizePath(testString1), refString )
        testString2 = "c:\\hallo"
        self.assertEqual( csnUtility.NormalizePath(testString2), refString )

    def testRemovePrefixFromPath(self):
        """ csnUtilityTests: test RemovePrefixFromPath function. """
        path = "c:/one/two/three"
        prefix = "c:"
        subString = "/one/two/three"
        self.assertEqual( subString, csnUtility.RemovePrefixFromPath(path, prefix) )

    def testHasBackSlash(self):
        """ csnUtilityTests: test HasBackSlash function. """
        self.assertTrue( csnUtility.HasBackSlash("c:\\hallo") )
        self.assertFalse( csnUtility.HasBackSlash("c://hallo") )
        
    def testCorrectPath(self):
        """ csnUtilityTests: test CorrectPath function. """
        root = "data/my src/"
        refPathRoot = root + "DummyLib"
        refPath = os.path.normpath( refPathRoot + "/libmodules" )
        
        self.assertEqual( csnUtility.CorrectPath(""), "" )
        self.assertEqual( csnUtility.CorrectPath("."), "." )
        testPath1 = root + "DummyLib/libmodules"
        self.assertEqual( csnUtility.CorrectPath(testPath1), refPath )
        testPath2 = root + "DummyLib/liBmoDules"
        self.assertEqual( csnUtility.CorrectPath(testPath2), refPath )      
        testPath3 = root + "DuMMyLib/libmodules"
        self.assertEqual( csnUtility.CorrectPath(testPath3), refPath )      
        refPath4 = os.path.normpath( root + "DummyLib/doEsnoTexist" )
        testPath4 = root + "DuMMyLib/doEsnoTexist"
        self.assertEqual( csnUtility.CorrectPath(testPath4), refPath4 )        
        refPath5 = os.path.normpath( "doEs/nOt/eXist" )
        testPath5 = "doEs/nOt/eXist"
        self.assertEqual( csnUtility.CorrectPath(testPath5), refPath5 )  
        
    def testSearchProgramPath(self):
        if csnUtility.IsWindowsPlatform():
            # Hoping there is a cmake on the test machine
            # Default path for cmake
            refPath1 = r"C:\Program Files (x86)\CMake 2.8\bin\cmake.exe"
            path_end1 = r"\bin\cmake.exe"
            # typical windows XP key names for cmake
            key_names1 = []
            for i in range(0,9):
                key_names1.append(r"SOFTWARE\Wow6432Node\Kitware\CMake 2.8.%s" % i)
            value_names1 = [r""]
            resPath1 = csnUtility.SearchWindowsProgramPath(key_names1, value_names1, path_end1)
            self.assertEqual( resPath1, refPath1 )
            
            # Wrong key name: should throw an exception
            key_names2 = [r"SOFTWARE\Wow6432Node\Kitware\CMake 8.7"]
            raisedError = False
            try:
                csnUtility.SearchWindowsProgramPath(key_names2, value_names1, path_end1)
            except OSError:
                raisedError = True
            self.assertTrue(raisedError)
            
            # Wrong path
            value_names2 = [r"foo"]
            raisedError = False
            try:
                csnUtility.SearchWindowsProgramPath( key_names1, value_names2, path_end1)
            except OSError:
                raisedError = True
            self.assertTrue(raisedError)
            
        else:  
            # Search for "echo" command (is installed on almost every machine and it's easy to check, if it works)
            echoPath = csnUtility.SearchUnixProgramPath("echo")
            
            # check, if it works
            self.assertTrue(os.path.exists(echoPath))
            testString = "kjag3hjZaheiVRuhvi6ueahEvehr2avhjaeGjhgfj6aecuy3ge1uyAagfi"
            (status, echoOutput) = commands.getstatusoutput('%s "%s"' % (echoPath, testString))
            self.assertEqual(status, 0)
            self.assertEqual(echoOutput, testString)
            
            # Wrong path
            raisedError = False
            try:
                csnUtility.SearchUnixProgramPath("somethingthatweforsuredontfind")
            except OSError:
                raisedError = True
            self.assertTrue(raisedError)

if __name__ == "__main__":
    unittest.main() 
