"""site.py - Types and functions for the internal representation of the
site tree.
"""


import collections

import locale_strings


class Entry(dict):

    """A dictionary that contains different language variants of one and
    the same a) page or b) page fragment or c) data dictionary.

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
        elif isinstance(content, collections.Mapping):
            content_type = "data"
        else:
            raise ValueError("Illegal Data type %s for data %s" %
                             (type(content), str(content)))
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
        if not len(self):
            self.__content_type = ""

    def is_page(self):
        """Returns true if entry contains (different language versions of) an
        HTML page."""
        return self.__content_type == "page"

    def is_page_fragment(self):
        """Returns true if entry contains (different language versions of)
        HTML code that can be placed in the body of an HTML page."""
        return self.__content_type == "fragment"

    def is_data(self):
        """Return true it entry contains (different language versions of)
        a data dictionary."""
        return self.__content_type == "data"

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


class Folder(collections.OrderedDict):

    """An ordered dictionary that contains (Sub-)Folders and Entries and
    optionally a reference to a parent folder, e.g. folder['__parent']
    """

    def __setitem__(self, key, value, *args):
        if isinstance(value, Folder) or isinstance(value, Entry):
            collections.OrderedDict.__setitem__(self, key, value, *args)
        else:
            raise ValueError(("Item for key %s is of type %s, but should be " +
                              "either site.Entry or site.Folder!") %
                             (key, type(value)))

    def entries(self):
        """Returns a generator that yields all pages or data entries in the
        folder but no sub-folders."""
        return (entry for entry in self.keys()
                if not isinstance(self[entry], Folder))

    def subfolders(self):
        """Returns a generator that yield all subfolders."""
        return (entry for entry in self.keys()
                if isinstance(self[entry], Folder) and entry != "__parent")


##############################################################################
#
# special functions for retrieving data
#
##############################################################################

class MissingItemError(KeyError):

    """A special kind of key error."""


def getitem(key, folder, source, lang):
    """Retrieve the value assigned to 'key' from the entry that is stored in
    'folder' under the name 'source' in the language version 'lang' (or a
    best match for 'lang' as a fallback option).

    Example: getitem(folder, "transtable", "DE", "save file")

    Raises MissingItemError in case 'key' is not found in the entry.
    An ordinary KeyError is raised if either 'source' is not found in 'folder'
    or there is no best match for 'lang' in 'source'.
    """
    entry = folder[source].bestmatch(lang)['content']
    try:
        value = entry[key]
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
    except MissingItemError:
        if '__parent' in folder:
            value = cascaded_getitem(key, folder, source, lang)
        else:
            raise KeyError(key)
    return value
