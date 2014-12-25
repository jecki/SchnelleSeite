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
    """

    def __init__(self, *args):
        dict.__init__(self, *args)
        self.__entry_type = ""

    def __setitem__(self, key, item):
        """Guarded __setitem__ to ensure that only valid entry data is added
        to the dictionary."""
        if not (key in locale_strings.fourletter_set or
                key in locale_strings.twoletter_set or key.lower() == 'any'):
            raise ValueError("%s is not a valid locale string" % key)
        elif not (isinstance(item, dict) or
                  isinstance(item, collections.UserDict)):
            raise ValueError("Not a dictionary: %s" % str(item))
        elif set(item.keys()) != {'metadata', 'content'}:
            illegal_keys = set(item.keys()) - {'metadata', 'content'}
            raise ValueError("Illegal key(s): %s" % str(illegal_keys))
        elif not (isinstance(item['metadata'], dict) or
                  isinstance(item['metadata'], collections.UserDict)):
            raise ValueError("metadata must be dictionary type not %s" %
                             type(item['metadata']))
        elif len(self) and key != self.keys().__iter__().__next__():
            if (type(self[self.keys().__iter__().__next__()]['content']) !=
                    type(item['content'])):
                raise ValueError("%s does not match previously stored types" %
                                 type(item['content']))
        else:
            self.__entry_type = ""

        dict.__setitem__(self, key, item)
        # self.__check_entrytype("")

    def __delitem__(self, key):
        dict.__delitem__(self, key)
        if not len(self):
            self.__entry_type = ""

    def __check_entrytype(self, what):
        if not self.__entry_type:
            if len(self):
                entry = self[self.keys().__iter__().__next__()]['content']
                if isinstance(entry, str) or isinstance(entry, bytes):
                    if entry.find("<html") >= 0 or entry.find("<HTML") >= 0:
                        self.__entry_type = "page"
                    else:
                        self.__entry_type = "fragment"
                elif (isinstance(entry, dict) or
                      isinstance(entry, collections.UserDict)):
                    self.__entry_type = "data"
                else:
                    raise ValueError("Illegal Data type %s for data %s" %
                                     (type(entry), str(entry)))
            else:
                return False
        return self.__entry_type == what

    def is_page(self):
        """Returns true if entry contains (different language versions of) an
        HTML page."""
        return self.__check_entrytype("page")

    def is_page_fragment(self):
        """Returns true if entry contains (different language versions of)
        HTML code that can be placed in the body of an HTML page."""
        return self.__check_entrytype("fragment")

    def is_data(self):
        """Return true it entry contains (different language versions of)
        a data dictionary."""
        return self.__check_entrytype("data")

    def get_variant(self, lang, substitutes=('EN', 'ANY')):
        """Returns a specific language version of the entry or an acceptable
        substitute, if the the preferred language version is not available.

        Raises an Error if no accepted substitute is available.
        """
        if lang in self:
            return self[lang]
        elif len(self):
            for sub in substitutes:
                if sub in self:
                    return self[sub]
                if sub.upper() == 'ANY':
                    all_keys = list(self.keys())
                    all_keys.sort()
                    return self[all_keys[0]]
        raise KeyError("%s not in %s nor in %s" % (lang,
                                                   str(list(self.keys())),
                                                   str(substitutes)))


class Folder(collections.OrderedDict):

    """An ordered dictionary that contains (Sub-)Folders and Entries.
    """

    def __setitem__(self, key, item, *args):
        if isinstance(item, Folder) or isinstance(item, Entry):
            collections.OrderedDict.__setitem__(self, key, item, *args)
        else:
            raise ValueError(("Item for key %s is of type %s, but should be " +
                              "either site.Entry or site.Folder!") %
                             (key, type(item)))

    def entries(self):
        """Returns a generator that yield all pages or data entries in the
        folder but no sub-folders."""
        return (entry for entry in self.keys()
                if not isinstance(self[entry], Folder))

    def subfolders(self):
        """Returns a generator that yield all subfolders."""
        return (entry for entry in self.keys()
                if isinstance(self[entry], Folder))
