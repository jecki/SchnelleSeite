"""site.py - Types and functions for the internal representation of the
site tree.

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


import collections
import os

import locale_strings
from utility import copy_on_condition, copytree_on_condition, is_newer


class Entry(dict):

    """A dictionary that contains different language variants of one and
    the same a) page or b) page fragment or c) data.

    Class Entry does some sanity checks to ensure that a variant is always
    one of a,b,c above and that all variants of one entry are of the same
    of these three types.

    Attributes:
        language_substitutes(list): class attribute; list of possible
            substitution languages if a particular language version of the
            entry does not exist, e.g. assume lang_subst = ["EN", "DE", "ANY"]
            and entry contains only the keys "DE" and "ES", then entry["FR"]
            will yield entry["DE"]. If key "DE" does not exist, it will
            yield "ES", because "ANY" in the substitution list matches
            any language variant whatsoever.
    """

    language_substitutes = ["EN", "ANY"]

    def __init__(self, *args):
        dict.__init__(self, *args)
        self.__content_type = ""

    def __entrytype(self, content):
        """Determines the type of content and returns 'page', 'fragment' or
        'data' accordingly or raises a ValueError.
        """
        if isinstance(content, str) or isinstance(content, bytes):
            if content.find("<html") >= 0 or content.find("<HTML") >= 0:
                content_type = "page"
            else:
                content_type = "fragment"
        else:
            content_type = "data"

        return content_type

    def __setitem__(self, key, value):
        """Guarded __setitem__ to ensure that only valid entry data is added
        to the dictionary."""
        locale_strings.valid_locale(key, raise_error=True)
        if not isinstance(value, collections.Mapping):
            raise ValueError("Not a dictionary: %s" % str(value))
        elif set(value.keys()) != {'metadata', 'content'}:
            illegal_keys = set(value.keys()) - {'metadata', 'content'}
            raise ValueError("Illegal key(s): %s" % str(illegal_keys))
        elif not isinstance(value['metadata'], collections.Mapping):
            raise ValueError("metadata must be dictionary type not %s" %
                             type(value['metadata']))
        else:
            try:
                firstkey = self.keys().__iter__().__next__()
            except StopIteration:
                firstkey = None
            if firstkey and key != firstkey:
                if (type(self[firstkey]['content']) != type(value['content'])):
                    raise ValueError(("%s does not match previously stored " +
                                      "types") % type(value['content']))
            else:
                self.__content_type = self.__entrytype(value['content'])

        dict.__setitem__(self, key, value)

    def __delitem__(self, key):
        dict.__delitem__(self, key)
        if len(self) == 0:
            self.__content_type = ""

    def is_page(self):
        """Returns true if entry contains (different language versions of) an
        HTML page."""
        return self.__content_type == "page"

    def is_fragment(self):
        """Returns true if entry contains (different language versions of)
        HTML code that can be placed in the body of an HTML page."""
        return self.__content_type == "fragment"

    def is_data(self):
        """Returns true if entry contains (different language versions of)
        data."""
        return self.__content_type == "data"

    def is_dictionary(self):
        """Returns true if the entry contains (different language versions of)
        data in form of a dictionary.
        """
        return (self.is_data() and
                isinstance(self['content'], collections.Mapping))

    def bestmatch(self, lang):
        """Returns a specific language version of the entry or an acceptable
        substitute, if the the preferred language version is not available.

        Raises an Error if no accepted substitute is available.
        """
        try:
            key = locale_strings.match(lang, set(self.keys()),
                                       self.language_substitutes)
        except KeyError as error:
            raise error
        return self[key]


class StaticEntry:

    """Static entries represent resource that are completely language
    independent. They exist only once and reside not in any of the language
    trees but under the top-level. Static Entries must not link back into the
    language dependent part of the site, but only to is very top level.

    Static Entries need to be explicitly marked as such in the configuration
    data. They are not run through the usual processing queue of the site
    generator but simply copied to their destination.

    Attributes:
        entryname(str): the file or directory name of the static entry
        entrypath(str): the absolute path of the entry
        isdir(bool): indicates whether the entry represents
    """

    def __init__(self, entryname):
        self.entryname = entryname
        self.entrypath = os.path.abspath(entryname)
        self.isdir = os.path.isdir(entryname)

    # TODO: Maybe, Symlinking would even be better!!
    def copy_entry(self, dst_path="", preprocessors={}):
        """Copies the entry to the build path of the site.
        Arguments:
           dest_path(string): the destination directory
           preprocessors(dict): A mapping of file extensions to functions
              that take the source and destination file name (including
              the directory path) as input. The preprocessor is expected
              to read, process and write the file all by itself. No copying
              is done if a preprocessor for the file extension is found in
              the dictionary. Preprocessors can be employed to minify
              javascript files or compile less stylsheets to css stylesheets.
        """
        sitemap = []
        if self.isdir:
            copytree_on_condition(self.entrypath,
                                  os.path.join(dst_path, self.entryname),
                                  is_newer, preprocessors, sitemap)
        else:
            copy_on_condition(self.entrypath,
                              os.path.join(dst_path, self.entryname),
                              is_newer, preprocessors, sitemap)
        return sitemap


class Folder(collections.OrderedDict):

    """An ordered dictionary that contains (Sub-)Folders and Entries and
    optionally a reference to a parent folder, e.g. folder['__parent']
    """

    def __init__(self):
        collections.OrderedDict.__init__(self)
        self.parent = None
        self.metadata = {}

    def __setitem__(self, key, value, *args):
        if (isinstance(value, Folder) or isinstance(value, Entry) or
                isinstance(value, StaticEntry)):
            collections.OrderedDict.__setitem__(self, key, value, *args)
        else:
            raise ValueError(("Item for key %s is of type %s, but should be " +
                              "site.Entry, site.StaticEntry or site.Folder!") %
                             (key, type(value)))

    def entries(self):
        """Returns a generator that yields all pages or data entries in the
        folder but no sub-folders."""
        return (entry for entry in self.keys()
                if not isinstance(self[entry], Folder))

    def subfolders(self):
        """Returns a generator that yields all subfolders."""
        return (entry for entry in self.keys()
                if isinstance(self[entry], Folder))


##############################################################################
#
# special functions for retrieving data
#
##############################################################################


class MissingItemError(KeyError):

    """A special kind of key error that is raised if a particular item was
    expected in a content dictionary (e.g. translation table) but not found.
    """


class MissingEntryError(KeyError):

    """A special kind of key error that is raised if a particular entry was
    expected in a folder but not found."""


def getentry(folder, path, lang):
    """Traverses the path to a particular entry under folder and returns the
    best matching language version of that entry.
    """
    path = path.split("/")
    for part in path[:-1]:
        folder = folder[part]
    if path[-1] not in folder:
        raise MissingEntryError(path[-1])
    return folder[path[-1]].bestmatch(lang)


def getitem(key, folder, source, lang):
    """Retrieve the value assigned to 'key' from either the content of a
    data entry 'source' under 'folder' in the language version 'lang'
    or a best match for 'lang' as a fallback option.

    Example: getitem(folder, "transtable", "DE", "save file")

    Raises MissingItemError in case 'key' is not found in the content.
    An ordinary KeyError is raised if either 'source' is not found in 'folder'
    or there is no best match for 'lang' in 'source'.
    """
    content = getentry(folder, source, lang)['content']
    if not isinstance(content, collections.Mapping):
        raise ValueError("Mapping type instead of %s expected in %s" %
                         (type(content), source))
    try:
        value = content[key]
    except KeyError:
        raise MissingItemError(key)
    return value


def cascaded_getitem(key, folder, source, lang):
    """Retrieve the value assigned to 'key' from the entry that is stored in
    'folder' or any parent folder of 'folder' under the name 'source' in the
    language version 'lang'.

    Other than getitem, cascaded_getitem continues the search for key in
    databases with the same name in the parent folders (going inside out).
    """
    try:
        value = getitem(key, folder, source, lang)
    except (MissingItemError, MissingEntryError):
        if folder.parent:
            value = cascaded_getitem(key, folder.parent, source, lang)
        else:
            raise KeyError(key)
    return value


##############################################################################
#
# special functions for translations
#
##############################################################################


def raw_translate(expression, lang, folder, generator_resources):
    """Search for a translation of 'expression' into language 'lang'.

    The search starts in 'folder', continues through 'folder's parent folders
    and ultimately searches site_generator['_data']['_transtable']
    """
    try:
        tr = cascaded_getitem(expression, folder, '_transtable', lang)
    except KeyError as err:
        if err.args[0] == expression:
            tr = generator_resources['_data']['_transtable'].\
                bestmatch(lang)['content'][expression]
        else:
            raise err
    return tr


def translate(expression, metadata):
    """Search for a translation of 'expression' into the language set in the
    metadata.
    """
    return raw_translate(expression, metadata['language'], metadata['local'],
                         metadata['config']['generator_resources'])


def collect_fragments(folder, foldername, order):
    """Collects the fragments in 'folder' and returns the pathnames of the
    fragements (starting from folder) ordered by the value of the order
    metadata parameter in each fragment.
    """
    fragments = [entry for entry in folder if folder[entry].is_fragment()]
    if order:
        fragments.sort(
            key=lambda item: folder[item].bestmatch('ANY')['metadata'][order],
            reverse=True)
    return [foldername + "/" + entry for entry in fragments]
