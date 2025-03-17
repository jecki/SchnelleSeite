#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""test_upload.py - Unit tests for upload.py

Copyright 2015  by Eckhart Arnold

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import copy
import os
import shutil
import tempfile
import time
import unittest
import uuid

import upload


#############################################################################
#
# utility functions
#
#############################################################################

def create_tree(path, tree):
    """creates a directory tree from nested dictionaries."""
    if not os.path.exists(path):
        os.mkdir(path)
    for key in tree:
        fullpath = os.path.join(path, key)
        if isinstance(tree[key], dict):
            create_tree(fullpath, tree[key])
        else:
            with open(fullpath, "w", encoding="utf-8") as f:
                f.write(tree[key])


def read_tree(path):
    """reads a directory tree into a nested dictionary structure."""
    tree = {}
    directory = os.listdir(path)
    for entry in directory:
        fullpath = os.path.join(path, entry)
        if os.path.isdir(fullpath):
            tree[entry] = read_tree(fullpath)
        else:
            with open(fullpath, "r", encoding="utf-8") as f:
                tree[entry] = f.read()
    return tree


def retrieve_tree(wrapper, path):
    """reads a directory tree from an FS or FTP wrapper into nested
    dictionaries.
    """
    if wrapper.isFileSystem():
        return read_tree(wrapper.fullpath(path))
    else:
        tmpfilename = os.path.join(tempfile.gettempdir(), "dowload_" +
                                   str(uuid.uuid1()))
        tree = {}
        directory = wrapper.listdir(path)
        for entry in directory:
            descendant = os.path.join(path, entry)
            if wrapper.isdir(descendant):
                tree[entry] = retrieve_tree(wrapper, descendant)
            else:
                wrapper.download(descendant, tmpfilename)
                with open(tmpfilename, "r", encoding="utf-8") as f:
                    tree[entry] = f.read()
        if os.path.exists(tmpfilename):
            os.remove(tmpfilename)
        return tree


def get_emptylog():
    return {"uploaded": set(),
            "skipped": set(),
            "created": set(),
            "deleted": set(),
            "removed": set()}


def touch(filename):
    with open(filename, 'r') as f:
        data = f.read()
    with open(filename, 'w') as f:
        f.write(data)


#############################################################################
#
# FSWrapper tests
#
#############################################################################

class TestFSWrapper(unittest.TestCase):

    # setup

    @classmethod
    def setUpWrapper(cls):
        os.mkdir(cls.testdir)
        return upload.FileSystemWrapper(cls.testdir)

    @classmethod
    def tearDownWrapper(cls):
        cls.ftp.close()

    @classmethod
    def setUpClass(cls):
        cls.tmp = os.path.join(tempfile.gettempdir(), "test_upload_" +
                               str(uuid.uuid1()))
        os.mkdir(cls.tmp)
        cls.testdir = os.path.join(cls.tmp, "testdir")
        cls.ftp = cls.setUpWrapper()
        cls.files = cls.add_some_files()

    @classmethod
    def tearDownClass(cls):
        cls.remove_files(cls.files)
        cls.tearDownWrapper()
        shutil.rmtree(cls.tmp)

    # utility

    @classmethod
    def add_some_files(cls):
        files = {"file_1": "first file", "file_2": "second file"}
        create_tree(cls.tmp, files)
        # cls test
        fname = next(iter(files))
        assert os.stat(os.path.join(cls.tmp, fname)).st_size == \
            len(files[fname])

        for key in files:
            cls.ftp.upload(os.path.join(cls.tmp, key), "")
            assert cls.ftp.exists(key)
        return files

    @classmethod
    def remove_files(cls, file_names):
        for name in file_names:
            cls.ftp.remove(name)
            assert not cls.ftp.exists(name)

    # test

    def test_fullpath(self):
        self.assertEqual(os.path.join(self.testdir, "subdir/file.txt"),
                         self.ftp.fullpath("subdir/file.txt"))
        self.assertEqual(os.path.join(self.testdir, "subdir/file.txt"),
                         self.ftp.fullpath("/subdir/file.txt"))

    def test_listdir(self):
        self.assertEqual(set(self.files.keys()), set(self.ftp.listdir(".")))

    def test_listdir_attr(self):
        directory = self.ftp.listdir_attr(".")
        self.assertEqual(set(self.files.keys()),
                         {entry.filename for entry in directory})
        for entry in directory:
            self.assertEqual(entry.st_size, len(self.files[entry.filename]))
            self.assertNotEqual(entry.st_mtime, 0.0)

    def test_exists(self):
        for fname in self.files:
            self.assertTrue(self.ftp.exists(fname))
        fname = "no_file"
        assert fname not in self.files
        self.assertFalse(self.ftp.exists(fname))
        self.ftp.mkdir(fname)
        self.assertTrue(self.ftp.exists(fname))
        self.ftp.rmdir(fname)

    def test_isfile(self):
        fname = "directory_1"
        assert fname not in self.files
        self.ftp.mkdir(fname)
        # a directory is not a file
        self.assertFalse(self.ftp.isfile(fname))
        self.ftp.rmdir(fname)
        fname = "no_file"
        assert fname not in self.files
        # a non existant file is not a file
        self.assertFalse(self.ftp.isfile(fname))
        # isfile should return True for proper files
        for fname in self.files:
            self.assertTrue(self.ftp.isfile(fname))

    def test_isdir(self):
        fname = "directory_1"
        assert fname not in self.files
        self.ftp.mkdir(fname)
        # isdir() should return True for a directory
        self.assertTrue(self.ftp.isdir(fname))
        self.ftp.rmdir(fname)
        fname = "no_file"
        assert fname not in self.files
        # a non existant directory is not a directory
        self.assertFalse(self.ftp.isdir(fname))
        # isdir should return False for files
        for fname in self.files:
            self.assertFalse(self.ftp.isdir(fname))

    def test_mtime(self):
        fname = next(iter(self.files))
        fpath = os.path.join(self.tmp, fname)
        mt1 = os.stat(fpath).st_mtime
        time.sleep(1.1)
        self.ftp.upload(fpath, "")
        mt2 = self.ftp.mtime(fname)
        self.assertTrue(mt2 >= mt1, "%s not >= %s" % (str(mt2), str(mt1)))

    def test_size(self):
        for fname in self.files:
            size = self.ftp.size(fname)
            self.assertEqual(size, len(self.files[fname]))

    def test_upload_and_download(self):
        fname = next(iter(self.files))
        local_path = os.path.join(self.tmp, fname)
        alt_local_path = os.path.join(self.tmp, "downloaded")
        assert not os.path.exists(alt_local_path)

        self.ftp.upload(local_path, "")
        self.assertTrue(self.ftp.isfile(fname))

        self.ftp.download(fname, alt_local_path)
        with open(alt_local_path, "r", encoding="utf-8") as f:
            data = f.read()
        self.assertEqual(data, self.files[fname])
        os.remove(alt_local_path)

        alt_name = "alt_file"
        assert not self.ftp.exists(alt_name)
        self.ftp.upload(local_path, alt_name)
        self.assertTrue(self.ftp.isfile(alt_name))
        self.ftp.remove(alt_name)
        assert not self.ftp.exists(alt_name)

        dir_name = "sub_dir"
        assert not self.ftp.exists(dir_name)
        self.ftp.mkdir(dir_name)
        assert self.ftp.isdir(dir_name)

        self.ftp.upload(local_path, dir_name)
        self.assertTrue(self.ftp.isfile(os.path.join(dir_name, fname)))
        self.ftp.remove(os.path.join(dir_name, fname))

        self.ftp.upload(local_path, os.path.join(dir_name, alt_name))
        self.assertTrue(self.ftp.isfile(os.path.join(dir_name, alt_name)))

        with open(alt_local_path, "w", encoding="utf-8") as f:
            f.write("Überschreib Test: Das hier sollte nicht zu lesen sein!")
        self.ftp.download(os.path.join(dir_name, alt_name), alt_local_path)
        with open(alt_local_path, "r", encoding="utf-8") as f:
            data = f.read()
        self.assertEqual(data, self.files[fname])
        os.remove(alt_local_path)

        self.ftp.remove(os.path.join(dir_name, alt_name))

        self.ftp.rmdir(dir_name)
        assert not self.ftp.exists(dir_name)

    def test_remove(self):
        fname = next(iter(self.files))
        local_path = os.path.join(self.tmp, fname)
        alt_name = "alt_file"
        assert not self.ftp.exists(alt_name)
        self.ftp.upload(local_path, alt_name)
        assert self.ftp.isfile(alt_name)
        self.ftp.remove(alt_name)
        self.assertFalse(self.ftp.exists(alt_name))

    def test_mkdir_rmdir(self):
        dir_name = "sub_dir"
        assert not self.ftp.exists(dir_name)
        self.ftp.mkdir(dir_name)
        self.assertTrue(self.ftp.isdir(dir_name))
        self.ftp.rmdir(dir_name)
        self.assertFalse(self.ftp.exists(dir_name))

    def test_rmtree(self):
        dir_name = "sub_dir"
        assert not self.ftp.exists(dir_name)
        self.ftp.mkdir(dir_name)
        for fname in self.files:
            self.ftp.upload(os.path.join(self.tmp, fname), dir_name)
            assert self.ftp.isfile(os.path.join(dir_name, fname))
            with self.assertRaises(NotADirectoryError):
                self.ftp.rmtree(os.path.join(dir_name, fname))

        subdir1 = os.path.join(dir_name, "subsub_dir1")
        subdir2 = os.path.join(dir_name, "subsub_dir2")
        self.ftp.mkdir(subdir1)
        assert self.ftp.isdir(subdir1)
        self.ftp.mkdir(subdir2)
        assert self.ftp.isdir(subdir2)
        for fname in self.files:
            self.ftp.upload(os.path.join(self.tmp, fname), subdir2)
            assert self.ftp.isfile(os.path.join(subdir2, fname))

        self.ftp.rmtree(dir_name, keep_topdir=True)
        self.assertTrue(self.ftp.exists(dir_name))
        self.assertFalse(self.ftp.listdir(dir_name))

        self.ftp.rmtree(dir_name, keep_topdir=False)
        self.assertFalse(self.ftp.exists(dir_name))

        # check that nothing in the parent dir has been deleted
        for fname in self.files:
            self.assertTrue(self.ftp.isfile(fname))


@unittest.skip("")
class TestFTPWrapper(TestFSWrapper):

    site = "test_ftp"

    @classmethod
    def setUpWrapper(cls):
        print("\nconnecting to " + cls.site)
        ftp = upload.connect("test_sites.ini", cls.site)
        cls.testdir = "testdir"
        if ftp.isdir(cls.testdir):
            ftp.rmtree(cls.testdir)
        elif ftp.isfile(cls.testdir):
            ftp.remove(cls.testdir)
        ftp.mkdir(cls.testdir)
        try:
            ftp.ftp.cwd(cls.testdir)
        except AttributeError:
            ftp.sftp.chdir(cls.testdir)
        return ftp

    @classmethod
    def tearDownWrapper(cls):
        cls.ftp.close()

    def test_fullpath(self):
        # tests are FS specific and fo not work with ftp, therefore ignore
        pass


@unittest.skip("")
class TestSFTPWrapper(TestFTPWrapper):

    site = "test_sftp"


############################################################################
#
# upload tests
#
#############################################################################


class TestUpload(unittest.TestCase):

    # setup and tear down

    @classmethod
    def setUpWrapper(cls):
        return upload.FileSystemWrapper(cls.tmp)

    @classmethod
    def tearDownWrapper(cls):
        cls.remote.close()

    @classmethod
    def setUpClass(cls):
        cls.tmp = os.path.join(tempfile.gettempdir(), "test_upload_" +
                               str(uuid.uuid1()))
        os.mkdir(cls.tmp)
        cls.treeA = {"file_1": "file 1",
                     "file_2": "file 2",
                     "subdir": {"file_3": "file 3"}}
        cls.treeB = {"file_1": "file 1",
                     "file_2": "file 2",
                     "subdir": {"file_3": "file 3",
                                "file_4": "file 4"}}
        cls.treeC = {"file_1": "file 1",
                     "subdir": {"file_3": "file 3",
                                "file_4": "file 4"}}

        cls.srcC_path = os.path.join(cls.tmp, "srcC")
        create_tree(cls.srcC_path, cls.treeC)

        cls.srcB_path = os.path.join(cls.tmp, "srcB")
        create_tree(cls.srcB_path, cls.treeB)

        cls.srcA_path = os.path.join(cls.tmp, "srcA")
        create_tree(cls.srcA_path, cls.treeA)

        cls.dst_path = "dst"
        cls.remote = cls.setUpWrapper()
        if cls.remote.isdir(cls.dst_path):
            cls.remote.rmtree(cls.dst_path)
        elif cls.remote.isfile(cls.dst_path):
            cls.remote.remove(cls.dst_path)
        cls.remote.mkdir(cls.dst_path)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp)
        cls.tearDownWrapper()

    # utility

    @classmethod
    def cleanup_dest(cls):
        cls.remote.rmtree(cls.dst_path)
        cls.remote.mkdir(cls.dst_path)

    # test code

    def test_selftest(self):
        self.assertEqual(self.treeA, read_tree(self.srcA_path))

    def test_simple_upload(self):
        local = upload.FileSystemWrapper(self.srcA_path)
        upload.upload_tree(local, "", self.remote, self.dst_path)
        self.assertEqual(self.treeA, retrieve_tree(self.remote, self.dst_path))
        self.cleanup_dest()

    def test_differential_upload(self):
        # setup
        local = upload.FileSystemWrapper(self.srcA_path)
        upload.upload_tree(local, "", self.remote, self.dst_path)

        # test
        local = upload.FileSystemWrapper(self.srcB_path)
        upload.upload_tree(local, "", self.remote, self.dst_path)
        self.assertEqual(self.treeB, retrieve_tree(self.remote, self.dst_path))

        self.cleanup_dest()

    def test_NIL_Proxy(self):
        # setup
        local = upload.FileSystemWrapper(self.srcA_path)
        upload.upload_tree(local, "", self.remote, self.dst_path)

        # test
        local = upload.FileSystemWrapper(self.srcC_path)
        remote = upload.NILProxy(self.remote)
        upload.upload_tree(local, "", remote, self.dst_path, delete=True)
        self.assertEqual(self.treeA, retrieve_tree(remote, self.dst_path))

        self.cleanup_dest()

    def test_upload_new_files_only(self):
        # setup
        local = upload.FileSystemWrapper(self.srcA_path)
        upload.upload_tree(local, "", self.remote, self.dst_path)

        expected_log = get_emptylog()
        del expected_log['skipped']

        # test
        # print(local.mtime("file_1"), self.remote.mtime("dst/file_1"))
        log = upload.upload_tree(local, "", self.remote, self.dst_path)
        del log['skipped']
        self.assertEqual(log, expected_log)

        time.sleep(1.1)
        touch(local.fullpath('file_2'))
        assert local.mtime('file_2') != \
            self.remote.mtime(os.path.join(self.dst_path, 'file_2')), \
            "mtime resolution of your system is too small for this test." \
            "choose another value for sleep() in test_upload_new_files_only!"
        expected_log['uploaded'] = {os.path.join(self.dst_path, 'file_2')}
        log = upload.upload_tree(local, "", self.remote, self.dst_path)
        del log['skipped']
        self.assertEqual(log, expected_log)

        local = upload.FileSystemWrapper(self.srcB_path)
        log = upload.upload_tree(local, "", self.remote, self.dst_path)
        self.assertEqual(log['uploaded'],
                         {os.path.join(self.dst_path, 'subdir/file_4')})
        self.assertEqual(log['skipped'],
                         {os.path.join(self.dst_path, entry) for entry in
                          ['file_2', 'file_1', 'subdir/file_3']})
        self.cleanup_dest()

    def test_differential_upload_wo_delete(self):
        # setup
        local = upload.FileSystemWrapper(self.srcA_path)
        upload.upload_tree(local, "", self.remote, self.dst_path)

        tree = copy.deepcopy(self.treeA)
        tree.update(self.treeC)
        assert tree == self.treeB

        local = upload.FileSystemWrapper(self.srcC_path)
        upload.upload_tree(local, "", self.remote, self.dst_path, delete=False)
        self.assertEqual(self.treeB, retrieve_tree(self.remote, self.dst_path))
        self.cleanup_dest()

    def test_differential_upload_w_delete(self):
        # setup
        local = upload.FileSystemWrapper(self.srcA_path)
        upload.upload_tree(local, "", self.remote, self.dst_path)

        tree = copy.deepcopy(self.treeA)
        tree.update(self.treeC)
        assert tree == self.treeB

        local = upload.FileSystemWrapper(self.srcC_path)
        upload.upload_tree(local, "", self.remote, self.dst_path, delete=True)
        tree = copy.deepcopy(self.treeB)
        del tree['file_2']
        self.assertEqual(tree, retrieve_tree(self.remote, self.dst_path))
        self.cleanup_dest()


@unittest.skip("")
class test_FTP_upload(TestUpload):

    site = "test_ftp"

    @classmethod
    def setUpWrapper(cls):
        print("\nconnecting to " + cls.site)
        ftp = upload.connect("test_sites.ini", cls.site)
        return ftp

    @classmethod
    def tearDownWrapper(cls):
        cls.remote.close()


@unittest.skip("")
class test_SFTP_upload(test_FTP_upload):

    site = "test_sftp"


if __name__ == '__main__':
    unittest.main()
