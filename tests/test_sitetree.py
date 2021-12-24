
import os
import shutil
import sys
import time
import unittest

from sitetree import *


class TestCopyFuncs(unittest.TestCase):

    def setUp(self):
        unittest.TestCase.setUp(self)
        os.makedirs('testdata/test_sitetree/src/nested')
        with open('testdata/test_sitetree/src/nested/fileA.txt', "w") as f:
            f.write("fileA")
        with open('testdata/test_sitetree/src/nested/fileB.txt', "w") as f:
            f.write("fileB")
        with open('testdata/test_sitetree/src/fileC.txt', "w") as f:
            f.write("fileC")

    def tearDown(self):
        unittest.TestCase.tearDown(self)
        shutil.rmtree('testdata/test_sitetree')

    def test_is_newer(self):
        time.sleep(0.1)
        with open('testdata/test_sitetree/fileC.txt', "w") as f:
            f.write("fileC")
        self.assertTrue(is_newer('testdata/test_sitetree/fileC.txt',
                                 'testdata/test_sitetree/src/fileC.txt'))
        self.assertFalse(is_newer('testdata/test_sitetree/src/fileC.txt',
                                  'testdata/test_sitetree/fileC.txt'))
        os.rename('testdata/test_sitetree/fileC.txt',
                  'testdata/test_sitetree/fileD.txt')
        self.assertRaises(ValueError, is_newer,
                          'testdata/test_sitetree/fileD.txt',
                          'testdata/test_sitetree/src/fileC.txt')
        os.remove('testdata/test_sitetree/fileD.txt')
        self.assertTrue(is_newer('testdata/test_sitetree/src/fileC.txt',
                                 'testdata/test_sitetree/fileC.txt'))

    def test_copy_on_condition(self):
        time.sleep(0.1)
        ALT_TEXT = "fileC alternative version"
        with open('testdata/test_sitetree/fileC.txt', "w") as f:
            f.write(ALT_TEXT)
        copy_on_condition('testdata/test_sitetree/fileC.txt',
                          'testdata/test_sitetree/src/fileC.txt', is_newer)
        with open('testdata/test_sitetree/src/fileC.txt', "r") as f:
            content = f.read()
        self.assertEqual(content, ALT_TEXT)
        time.sleep(1)
        with open('testdata/test_sitetree/src/fileC.txt', "w") as f:
            f.write("fileC")
        copy_on_condition('testdata/test_sitetree/fileC.txt',
                          'testdata/test_sitetree/src/fileC.txt', is_newer)
        with open('testdata/test_sitetree/src/fileC.txt', "r") as f:
            content = f.read()
        self.assertNotEqual(content, ALT_TEXT)
        os.remove('testdata/test_sitetree/fileC.txt')


# if __name__ == "__main__":
#     sys.path.append(
#         os.path.split(os.path.dirname(os.path.abspath(sys.argv[0])))[0])
#     from sitetree import *
#     unittest.main()
