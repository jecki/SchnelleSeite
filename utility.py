"""utility.py -- utility functions that might be useful for loaders,
    postprocessors and the like

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

import contextlib
import datetime
import fnmatch
import hashlib
import os
import re
import shutil
from typing import Iterable


##############################################################################
#
# python enhancements
#
##############################################################################

def deep_update(dest_dict, with_dict):
    """Updates 'dest_dict' recursively with 'with_dict'."""
    for k, v in with_dict.items():
        if k in dest_dict and isinstance(v, dict) and \
                isinstance(dest_dict[k], dict):
            deep_update(dest_dict[k], with_dict[k])
        else:
            dest_dict[k] = with_dict[k]


##############################################################################
#
# html meta data
#
##############################################################################

RX_META = re.compile(
    r'<meta\s+name\s*=\s*"(?P<name>.*?)"\s+content\s*=\s*"(?P<content>.*?)"\s*/?>',
    re.IGNORECASE)


##############################################################################
#
# sitemap handling
#
##############################################################################

class Sitemap(list):
    """Class Sitemap is a list of dictionaries that will be written to the
    sitemap.xml file. Other than a simple list, it receives a list of
    fnmatch-patterns (e.g. "secrets/*") to exclude files that should not be
    added to the sitemap."""

    def __init__(self, exclude_patterns: list):
        super().__init__()
        self.exclude_patterns = exclude_patterns

    def append(self, entry: dict):
        assert isinstance(entry, dict)
        if any(fnmatch.fnmatch(entry['loc'], pattern)
               for pattern in self.exclude_patterns):
            print('Entry "%s" excluded from sitmap.' % entry['loc'])
        else:
            filetype = entry['loc'][-5:].lower()
            if filetype == '.html' or filetype[-4:] == '.htm':
                try:
                    with open(entry['loc'], 'r', encoding='utf-8') as f:
                        page = f.read()
                except FileNotFoundError as e:
                    # dirty hack
                    if not re.match(r'[A-Z][A-Z]/', entry['loc']):
                        raise e
                    with open(entry['loc'][3:], 'r', encoding='utf-8') as f:
                        page = f.read()
                for meta in RX_META.finditer(page):
                    if meta['name'].upper() == "ROBOTS" \
                            and meta['content'].upper().find('NOINDEX') >= 0:
                        print('Entry "%s" excluded from sitemap, because '
                              'meta tag "ROBOTS" contains "NOINDEX"!'
                              % entry['loc'])
                        return
            super().append(entry)

    def extend(self, iterable: Iterable):
        for entry in iterable:
            self.append(entry)

    def write(self, filename, base_url):
        """Writes the sitemap in xml form to a file named ``filename``"""
        self.sort(key=lambda item: item['loc'])
        with open(filename, 'w') as f:
            f.write('<?xml version="1.0" encoding="UTF-8"?>\n <urlset '
                    'xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
                    'xmlns:xhtml="http://www.w3.org/1999/xhtml">\n')

            f.write('<url>\n<loc>' + base_url + '/index.html</loc>\n'
                    '<lastmod>' + isodate('index.html') + '</lastmod>'
                    '\n<changefreq>yearly</changefreq>\n'
                    '<priority>0.1</priority>\n</url>\n')

            for entry in self:
                alt_locs_xml = [('<xhtml:link rel="alternate" '
                                 'hreflang="{lang}" '
                                 'href="' + base_url + '/{loc}" />').
                                format(**alt) for alt in entry['alt_locs']]

                f.write('<url>\n'
                        '<loc>' + base_url + "/" + entry['loc'] + '</loc>\n' +
                        "\n".join(alt_locs_xml) +
                        '\n<lastmod>' + entry['lastmod'] + '</lastmod>\n'
                        '<changefreq>' + entry['changefreq'] + '</changefreq>'
                        '\n<priority>' + entry['priority'] + '</priority>\n'
                        '</url>\n')

            f.write('</urlset>\n\n')

##############################################################################
#
# file and directory management
#
##############################################################################

@contextlib.contextmanager
def enter_dir(directory):
    """Context manager for temporarily descending into a specific directory."""
    cwd = os.getcwd()
    os.chdir(directory)
    yield
    os.chdir(cwd)


@contextlib.contextmanager
def create_and_enter_dir(directory):
    """Context manager for creating a directory (unless it already exists) and
    temporarily descending into it."""
    if not os.path.exists(directory):
        os.mkdir(directory)
    cwd = os.getcwd()
    os.chdir(directory)
    yield
    os.chdir(cwd)


def is_newer(src_file, dst_file):
    """Returns True, if src_file's date is newer_or equal than dst_file's or
    if dst_file does not exist. Returns False otherwise. Raises an error if
    src_file and dst_file have different names or are different kinds of
    entities, e.g. directory and file.
    """
    src_name = os.path.basename(src_file)
    dst_name = os.path.basename(dst_file)
    if src_name != dst_name:
        raise ValueError(("Source file %s does not have the same name " +
                          "as destination file %s") % (src_file, dst_file))
    if (os.path.exists(dst_file) and not
        ((os.path.isfile(src_file) and os.path.isfile(dst_file)) or
         (os.path.isdir(src_file) and os.path.isdir(dst_file)))):
        raise ValueError(("Source %s and destination %s are of different " +
                          "kind.") % (src_file, dst_file))
    # > instead of >= to avaoid to much copying, could be dangerous in
    # case of changes that were made within less than a second...
    return (not os.path.exists(dst_file) or
            os.path.getmtime(src_file) > os.path.getmtime(dst_file))
    # or os.path.getsize(src_file) != os.path.getsize(dst_file)


def isodate(filename):
    return datetime.date.fromtimestamp(os.stat(filename).st_mtime).isoformat()


def copy_on_condition(src, dst, cond, preprocessors={}, sitemap=[]):
    """Copies src to dst, if cond(src, dst) returns True. If a preprocessor
    is given for the extentions of the file, the preprocessor function is
    called with the source and destination name instead of the system's
    copy function.
    Adds `dst` to sitemap if `dst` is an HTML or PDF file,
    otherwise an empty list is returned.
    """
    def add_to_sitemap(src, dst):
        ext = os.path.splitext(dst)[1].lower()
        if ext == ".pdf" or ext == ".html":
            sitemap.append({"loc": dst,
                            "alt_locs": [],
                            "lastmod": isodate(src),
                            "changefreq": "yearly",
                            "priority": "0.4"})

    if cond(src, dst):
        ext = os.path.splitext(src)[1]
        if ext in preprocessors:
            new_dst = preprocessors[ext](src, dst)
            if not isinstance(new_dst, type(None)):
                assert isinstance(new_dst, str), \
                    "Prprocessor %s did not return a destination file name" + \
                    " but non string type %s with content %s" % \
                    (preprocessors[ext], str(type(new_dst)), str(new_dst))
                dst = new_dst
        else:
            shutil.copy2(src, dst)
    add_to_sitemap(src, dst)


def copytree_on_condition(src, dst, cond, preprocessors={}, sitemap=[]):
    """Copies all files and directories from src to dst. Files are only copied
    if cond(src, dst) is True. Copying may be channeled through a preprocessor.
    Adds files sitemap entries (dict) to `sitemap`, in case the destination
    file name ends with '.html' or '.pdf'
    """

    names = os.listdir(src)
    os.makedirs(dst, exist_ok=True)
    for name in names:
        srcname = os.path.join(src, name)
        dstname = os.path.join(dst, name)
        if os.path.isdir(srcname):
            if not name.startswith('_'):    # TODO: this should already be excluded at tree scanning stage!
                copytree_on_condition(srcname, dstname, cond, preprocessors,
                                      sitemap)
        else:
            copy_on_condition(srcname, dstname, cond, preprocessors, sitemap)
    shutil.copystat(src, dst)


##############################################################################
#
# HTML processing
#
##############################################################################

RX_HTML_COMMENTS = re.compile("<!--.*?-->", re.DOTALL)
RX_ATTRIBUTES = re.compile(' ([a-zA-Z]+?) *?= *?["\'](.*?)["\']')


def segment_data(data, regexp):
    """Splits the data string into segments that either match or do not match
    the regular expression 'regexp'. Other than re.split() (or "".split()),
    which leave out the separation string, the segments matching 'regexp'
    are included in the result.

    Args:
        data (string): the data to be segmented, e.g. an HTML page
        regexp (string or regex object): a regular expression object or string
            that is used to divide the data into segments.

    Returns:
        list. A list of segments.

    Example:
        >>> segment_data("Text <h1>HEADING</h1> More Text", "<h1>.*?</h1>")
       ["Text ", "<h1>HEADING</h1>", " More Text" ]

    Use the following code to determine the offset of the first matching
    segment:  first = 0 if regexp.match(data) else 1
    """
    if isinstance(regexp, str):
        regexp = re.compile(regexp)
    segments = []
    pos = 0
    for match in regexp.finditer(data):
        start = match.start()
        end = match.end()
        if start > pos:
            segments.append(data[pos:start])
        segments.append(data[start:end])
        pos = end
    if pos < len(data):
        segments.append(data[pos:])
    return segments


def matching_segment_range(segments, regexp, invert=False):
    """Returns a range object that yields the indices of those segments that
    match 'regexp' from all segments that are returned by function
    'segment_data'.

    Args:
        segments (list): List of segments as returned by function
            'segment_data'.
        regexp (string or regex object): the regular expression object or
            string that has been used to divide the data into segments with
            function 'segment_data'.
        invert(boolean): If True, return the range of segments that do not
            match regexp

    Returns:
        range object. Indices of the matching segments.
    """
    if isinstance(regexp, str):
        regexp = re.compile(regexp)
    if invert:
        return range(1 if regexp.match(segments[0]) else 0, len(segments), 2)
    else:
        return range(0 if regexp.match(segments[0]) else 1, len(segments), 2)


def get_attributes(data, pos):
    """Returns a dictionary of all attributes and their values of the html
    tag that starts at position pos in string 'data'. All attribute names are
    converted to lower case.
    """
    assert data[pos] == "<"
    endpos = data.find(">", pos)
    assert endpos > pos
    return {key.lower(): value
            for (key, value) in RX_ATTRIBUTES.findall(data, pos, endpos)}


def set_attributes(data, pos, attributes):
    """Sets the attributes of the html tag at pos in string data to those
    stored in the 'attributes' dictionary. Any existing attributes will be
    overwritten or deleted.
    """
    assert data[pos] == "<"
    endpos = data.find(">", pos)
    assert endpos > pos
    start = data.find(" ", pos, endpos)
    if start < 0:
        start = endpos
    attr_list = ['%s="%s"' % (key, attributes[key]) for key in attributes]
    attr_str = " " + " ".join(attr_list) + " "
    data = data[:start] + attr_str + data[endpos:]
    return data


def md5(*txt):
    """Returns the md5-checksum for `txt`. This can be used to test if
    some piece of text, for example a grammar source file, has changed.
    """
    md5_hash = hashlib.md5()
    for t in txt:
        md5_hash.update(t.encode('utf8'))
    return md5_hash.hexdigest()
