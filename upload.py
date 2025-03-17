#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""upload.py - Upload website files to server via ftp

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

[ADD DESCRIPTION HERE]

Example for a configuration file entry:

[test]
server   = www.finalfrontier.org
port     = 21
protocol = ftp
user     = krirk
password = enterprise

"""


import configparser
import datetime
import ftplib
import getpass
import os
import shutil
import stat

import paramiko


##############################################################################
#
# utility functions
#
##############################################################################

local_tz = datetime.timezone(datetime.timedelta(seconds=round(
    (datetime.datetime.now() - datetime.datetime.utcnow()).total_seconds())))


def timestamp(datetime_str, tzinfo=None):
    """-> timestamp that represents a `datetime_str` of the form
    "YYYYMMDDHHMMSS", e.g. "20150521134020"
    """
    d = datetime_str
    dt = datetime.datetime(int(d[:4]), int(d[4:6]), int(d[6:8]),
                           int(d[8:10]), int(d[10:12]), int(d[12:14]),
                           tzinfo=tzinfo)
    return dt.timestamp()


##############################################################################
#
# FTPWrappers
#
##############################################################################

class AbstractConnectionWrapper:

    def close(self):
        """Closes the wrapped connection."""
        pass

    def isFileSystem(self):
        """-> True, if the wrapped connection is a file system that can be
        accessed via open(), OS.listdir() etc...
        """
        return False

    def listdir(self, path):
        """Returns the list of file and/or directory names contained in the
        directory at `path`."""
        return [entry.filename for entry in self.listdir_attr(path)]

    def listdir_attr(self, path):
        """Returns the files and/or directories contained in the directory
        at location `path` as a list of `paramiko.SFTPAttributes` objects."""
        raise NotImplementedError

    def exists(self, path):
        """Retuns true if a somethong (e.g., file, directory, link...) exists
        at location `path` false otherwise"""
        raise NotImplementedError

    def isfile(self, path):
        """Returns true, if a file exists at location `path`, false if it is
        not a file or if the path does not even exist."""
        raise NotImplementedError

    def isdir(self, path):
        """Returns true, if a directory exists at location `path`, false if it
        is not a directory or if the path does not even exist."""
        raise NotImplementedError

    def mtime(self, path):
        """Returns the time of the last modification of the object located at
        `path` as a timestamp."""
        raise NotImplementedError

    def size(self, path):
        """Returns the size of the file at location `path`."""
        raise NotImplementedError

    def upload(self, local_path, remote_path):
        """Uploads a file from `local_path` on the file system to
        `remote_path` on the wrapped connection."""
        return NotImplementedError

    def download(self, remote_path, local_path):
        """Downloads a file from `remote_path` on the wrapped connection to
        `local_path` on the file system."""
        raise NotImplementedError

    def remove(self, path):
        """Removes the file located at `path`."""
        raise NotImplementedError

    def mkdir(self, path):
        """Creates a directory at `path`."""
        raise NotImplementedError

    def rmdir(self, path):
        """Removes the (empty!) directory at location `path`."""
        raise NotImplementedError

    def _rmtree(self, path):
        """Removes everything that is contained in the directory `path` or
        any of its subdirectories and finally removes the directory `path`
        itself.
        This method should be considered as "protected", it should be
        implemented by subclasses but not be called from the outside. From
        the outside, use `rmtree()` instead."""
        raise NotImplementedError

    def rmtree(self, path, keep_topdir=False):
        """Removes everything that is contained in the directory `path` or
        any of its subdirectories, but removes the top level directory `path`
        only if `keep_topdir` is false.
        """
        if not self.isdir(path):
            raise NotADirectoryError(path)
        if keep_topdir:
            files = self.listdir(path)
            for name in files:
                if self.isdir(os.path.join(path, name)):
                    self._rmtree(os.path.join(path, name))
                else:
                    self.remove(os.path.join(path, name))
        else:
            self._rmtree(path)


class NILProxy(AbstractConnectionWrapper):

    def __init__(self, connection):
        self.connection = connection

    def close(self):
        self.connection.close()

    def isFileSystem(self):
        return self.connection.isFileSystem()

    def fullpath(self, path):
        return self.connection.fullpath(path)

    def listdir_attr(self, path):
        if self.connection.isdir(path):
            return self.connection.listdir_attr(path)
        else:
            return []

    def upload(self, local_path, remote_path):
        assert os.path.exists(local_path)

    def download(self, remote_path, local_path):
        shutil.copy2(self.fullpath(remote_path), local_path)

    def remove(self, path):
        pass

    def mkdir(self, path):
        pass

    def rmdir(self, path):
        pass

    def _rmtree(self, path):
        pass

    def rmtree(self, path, keep_topdir=False):
        pass


class FileSystemWrapper(AbstractConnectionWrapper):

    def __init__(self, root):
        self.root = root or "."

    def close(self):
        pass

    def isFileSystem(self):
        return True

    def fullpath(self, path):
        """This method is specific for FileSystemWrapper objects and
        returns the full path (i.e. including the root path which was passed
        to the constructor of the object) of `path`."""
        if path[:len(os.path.sep)] == os.path.sep:
            path = path[len(os.path.sep):]
        return os.path.normpath(os.path.join(self.root, path))

    def listdir(self, path):
        return os.listdir(self.fullpath(path))

    def listdir_attr(self, path):
        filenames = self.listdir(path)
        fullpath = self.fullpath(path)
        dir_attr = []
        for name in filenames:
            st = os.stat(os.path.join(fullpath, name))
            dir_attr.append(paramiko.SFTPAttributes.from_stat(st, name))
        return dir_attr

    def exists(self, path):
        return os.path.exists(self.fullpath(path))

    def isfile(self, path):
        return os.path.isfile(self.fullpath(path))

    def isdir(self, path):
        return os.path.isdir(self.fullpath(path))

    def mtime(self, path):
        return os.path.getmtime(self.fullpath(path))

    def size(self, path):
        return os.path.getsize(self.fullpath(path))

    def upload(self, local_path, remote_path):
        shutil.copy2(local_path, self.fullpath(remote_path))

    def download(self, remote_path, local_path):
        shutil.copy2(self.fullpath(remote_path), local_path)

    def remove(self, path):
        os.remove(self.fullpath(path))

    def mkdir(self, path):
        os.mkdir(self.fullpath(path))

    def rmdir(self, path):
        os.rmdir(self.fullpath(path))

    def _rmtree(self, path, keep_topdir=False):
        shutil.rmtree(self.fullpath(path))


class FTPWrapper(AbstractConnectionWrapper):

    def __init__(self, root, ftp):
        assert isinstance(ftp, ftplib.FTP)
        if root:
            ftp.cwd(root)
        self.ftp = ftp

    def close(self):
        print("FTP closed")
        self.ftp.close()

    def isFileSystem(self):
        return False

    def listdir(self, path):
        if not path:
            path = "."
        return [entry[0] for entry in self.ftp.mlsd(path)
                if entry[0] not in {".", ".."}]

    def listdir_attr(self, path):
        if not path:
            path = "."
        directory = []
        for name, attrs in self.ftp.mlsd(path):
            entry = paramiko.sftp_attr.SFTPAttributes()
            if name not in {".", ".."}:
                entry.filename = name
                entry.st_size = int(attrs['size'] if 'size' in attrs
                                    else attrs['sizd'])
                entry.st_uid = int(attrs['unix.uid'], 10) \
                    if 'unix.gid' in attrs else 0
                entry.st_gid = int(attrs['unix.gid'], 10) \
                    if 'unix.gid' in attrs else 0
                entry.st_mode = int(attrs['unix.mode'], 8) \
                    if 'unix.gid' in attrs else 0o755
                if attrs['type'][-3:] == "dir":
                    entry.st_mode |= 0o40000
                entry.st_mtime = timestamp(attrs['modify'],
                                           datetime.timezone.utc)
                entry.st_atime = entry.st_mtime
                directory.append(entry)
        return directory

    def exists(self, path):
        parent, name = os.path.split(path)
        directory = self.listdir(parent)
        return name in directory

    def __attr(self, path):
        parent, name = os.path.split(path)
        directory = {name: attrs for name, attrs in
                     self.ftp.mlsd(parent)}
        if name not in directory:
            raise IOError("FileNotFound: " + path)
        return directory[name]

    def isfile(self, path):
        try:
            return self.__attr(path)['type'] == "file"
        except IOError:
            return False

    def isdir(self, path):
        if not path:
            path = "."
        try:
            return self.__attr(path)['type'][-3:] == "dir"
        except IOError:
            return False

    def mtime(self, path):
        return timestamp(self.__attr(path)['modify'], datetime.timezone.utc)

    def size(self, path):
        return self.ftp.size(path)

    def upload(self, local_path, remote_path):
        dest_name = os.path.join(remote_path, os.path.basename(local_path)) \
            if not remote_path or self.isdir(remote_path) else remote_path
        with open(local_path, "rb") as f:
            self.ftp.storbinary("STOR " + dest_name, f)

    def download(self, remote_path, local_path):
        with open(local_path, "wb") as f:
            self.ftp.retrbinary("RETR " + remote_path, f.write)

    def remove(self, path):
        self.ftp.delete(path)

    def mkdir(self, path):
        self.ftp.mkd(path)

    def rmdir(self, path):
        self.ftp.rmd(path)

    def _rmtree(self, path, keep_topdir=False):
        for entry, attrs in self.ftp.mlsd(path):
            if entry not in {".", ".."}:
                entry_path = os.path.join(path, entry)
                if attrs['type'][-3:] == "dir":
                    self.rmtree(entry_path)
                else:
                    self.remove(entry_path)
        self.rmdir(path)


class SFTPWrapper(AbstractConnectionWrapper):

    def __init__(self, root, sftp):
        assert isinstance(sftp, paramiko.SFTPClient), str(sftp)
        if root:
            sftp.chdir(root)
        self.sftp = sftp

    def close(self):
        print("SFTP closed")
        self.sftp.close()

    def isFileSystem(self):
        return False

    def listdir(self, path):
        if not path:
            path = "."
        return [entry for entry in self.sftp.listdir(path)
                if entry not in {".", ".."}]

    def listdir_attr(self, path):
        if not path:
            path = "."
        return [entry for entry in self.sftp.listdir_attr(path)
                if entry.filename not in {".", ".."}]

    def exists(self, path):
        try:
            self.sftp.stat(path)
            return True
        except FileNotFoundError:
            return False

    def isfile(self, path):
        try:
            if stat.S_ISREG(self.sftp.stat(path).st_mode):
                return True
            else:
                return False
        except FileNotFoundError:
            return False

    def isdir(self, path):
        if not path:
            path = "."
        try:
            if stat.S_ISDIR(self.sftp.stat(path).st_mode):
                return True
            else:
                return False
        except FileNotFoundError:
            return False

    def mtime(self, path):
        return self.sftp.stat(path).st_mtime

    def size(self, path):
        return self.sftp.stat(path).st_size

    def upload(self, local_path, remote_path):
        dest_name = os.path.join(remote_path, os.path.basename(local_path)) \
            if not remote_path or self.isdir(remote_path) else remote_path
        self.sftp.put(local_path, dest_name)

    def download(self, remote_path, local_path):
        self.sftp.get(remote_path, local_path)

    def remove(self, path):
        self.sftp.remove(path)

    def mkdir(self, path):
        self.sftp.mkdir(path)

    def rmdir(self, path):
        self.sftp.rmdir(path)

    def _rmtree(self, path, keep_topdir=False):
        for entry in self.listdir(path):
            if entry not in {".", ".."}:
                entry_path = os.path.join(path, entry)
                if self.isdir(entry_path):
                    self.rmtree(entry_path)
                else:
                    self.remove(entry_path)
        self.rmdir(path)


##############################################################################
#
# upload functions
#
##############################################################################

def upload_tree(local, local_path, remote, remote_path, delete=False,
                logger=lambda msg: 0):
    assert local.isFileSystem()
    logger("entering " + remote_path + "...")

    report = {"uploaded": set(),  # file uploaded
              "skipped": set(),   # file skipped
              "created": set(),   # directory created
              "deleted": set(),   # file deleted
              "removed": set()}   # directory removed

    def log(category, entry_name):
        report[category].add(entry_name)
        logger(category + " " + entry_name)

    local_dict = {entry.filename: entry
                  for entry in local.listdir_attr(local_path)}
    remote_dict = {entry.filename: entry
                   for entry in remote.listdir_attr(remote_path)}

#    print("LOCAL:", [(k, v.st_mtime) for k, v in local_dict.items()])
#    print("REMOTE:", [(k, v.st_mtime) for k, v in remote_dict.items()])

    for entry in local_dict:
        src_path = os.path.join(local_path, entry)
        dst_path = os.path.join(remote_path, entry)
        if stat.S_ISDIR(local_dict[entry].st_mode):
            if entry not in remote_dict or not \
                    stat.S_ISDIR(remote_dict[entry].st_mode):
                if entry in remote_dict:
                    if delete:
                        remote.remove(dst_path)
                        log('deleted', dst_path)
                    else:
                        for e in remote_dict:
                            print(remote_dict[e])
                        raise IOError("Can't overwrite file "
                                      "%s with a directory" % dst_path)
                remote.mkdir(dst_path)
                log('created', dst_path)
            result = upload_tree(local, src_path, remote, dst_path,
                                 delete, logger)
            for key in report:
                report[key].update(result[key])
        else:
            if entry in remote_dict:
                local_time = local_dict[entry].st_mtime
                remote_time = remote_dict[entry].st_mtime
                if local_time > remote_time or \
                        (local_time == remote_time and
                         local_dict[entry].st_size !=
                         remote_dict[entry].st_size):
                    if stat.S_ISDIR(remote_dict[entry].st_mode):
                        if delete:
                            remote.rmtree(dst_path)
                            log('removed', dst_path)
                        else:
                            raise IOError("Can't overwrite dir %s with file" %
                                          dst_path)
                    remote.upload(local.fullpath(src_path), dst_path)
                    log('uploaded', dst_path) 
                        # + " %f %f %i %s" %
                        # (local_time, remote_time, local_dict[entry].st_size,
                        #  remote_dict[entry].st_size))
                else:
                    log('skipped', dst_path)
            else:
                remote.upload(local.fullpath(src_path), dst_path)
                log('uploaded', dst_path)

    if delete:
        for entry in remote_dict.keys() - local_dict.keys():
            dst_path = os.path.join(remote_path, entry)
            if stat.S_ISDIR(remote_dict[entry].st_mode):
                remote.rmtree(dst_path)
                log('removed', dst_path)
            else:
                remote.remove(dst_path)
                log('deleted', dst_path)

    logger("...leaving " + remote_path)
    return report


##############################################################################
#
# connections
#
##############################################################################


def query_if_necessary(username, password):
    """queries user for username and password in case `username` or `password`
    are empty. Returns username and password.
    Example:
        # assume `user` and `pw` have been read from some configuration file
        # and might possibly be empty
        user, pw = get_user_and_password(user, pw)
    """
    if username.strip() == "":
        username = input("user name: ")
        if username.strip() == "":
            username = "anonymous"
    if username != "anonymous" and not password:
        password = getpass.getpass("password: ")
    return (username, password)


def FTP_connect(host, port, username, password):
    username, password = query_if_necessary(username, password)
    ftp = ftplib.FTP()
    ftp.connect(host, port)
    ftp.login(username, password)
    return ftp


def SFTP_connect(host, port, username, password):
    remote = paramiko.Transport((host, port))
    username, password = query_if_necessary(username, password)
    remote.connect(username=username, password=password)
    sftp = paramiko.SFTPClient.from_transport(remote)
    return sftp


PROTOCOLS = {22: "sftp",
             21: "ftp",
             0: "filesystem"}

PORTS = {"sftp": 22,
         "ftp": 21,
         "filesystem": 0}


def connect(cfg_filename, cfg_section):
    config = configparser.ConfigParser()
    config.read(cfg_filename)
    if cfg_section == "":
        cfg_section = "default"
    if cfg_section not in config:
        raise ValueError("Section %s not in config file %s" %
                         (cfg_section, cfg_filename))
    section = config[cfg_section]
    if "server" not in section:
        raise ValueError('Key "host" missing in section %s of config file %s' %
                         (cfg_section, cfg_filename))
    host = section["server"]
    port = int(section["port"] if "port" in section else
               PORTS[section["protocol"]] if "protocol" in section else 22)
    protocol = section["protocol"] if "protocol" in section \
        else PROTOCOLS[int(section["port"])] if "port" in section else "ftp"
    root = section["root"] if "root" in section else ""
    username = section["user"] if "user" in section else ""
    password = section["password"] if "password" in section else ""

    if protocol == "ftp":
        return FTPWrapper(root, FTP_connect(host, port, username, password))
    elif protocol == "sftp":
        return SFTPWrapper(root, SFTP_connect(host, port, username, password))
    elif protocol == "filesystem":
        return FileSystemWrapper(os.path.join(host, root))
    else:
        raise ValueError("unknown protokol %s. Should be one of %" %
                         (protocol, str(list(PROTOCOLS.values()))))

    
def save_log(name, log):
    """Saves an upload log dictionary as YAML file.
    """
    t = datetime.datetime.now().isoformat()
    tstmp = t[0:10].replace("-", "") + t[10:16].replace(":", "")
    filename = name + "-" + tstmp + ".log"
    with open(filename, "w") as f:
        timestamp = str(datetime.datetime.now())
        f.write("# log created " + timestamp[:timestamp.find(".")] + "\n")
        for key in log:
            f.write("\n" + key + ":\n")
            for entry in sorted(list(log[key])):
                f.write("  - " + entry + "\n")

