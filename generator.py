

import os
import re
import sys
import warnings

import sitetree
import loader
from locale_strings import extract_locale, remove_locale


warnings.simplefilter('always')


include_patterns = [
    r'.htaccess'
]
exclude_patterns = [
    r'^[\.#].*',
    r'.*~$',
    r'__.*$'
]


def is_excluded(name):
    """Returns true if file or directory is to be excluded from processing.
    """
    return (any(re.match(ptrn, name) for ptrn in exclude_patterns) and not
            any(re.match(ptrn, name) for ptrn in include_patterns))


def warn(msg):
    """Issue a warning."""
    print(msg)
    warnings.warn(msg, Warning)


def scan_directory(path, loaders, injected_metadata, parent=None):
    """Reads all files in the directory path for which a loader is given
    for at least the last extension.

    If a file a several extensions, e.g. "example.markdown.jinja2" then the
    loaders are applied subsequently. In case no loader exists in the loaders
    dictionary for the last extension (e.g. ".jinja2") the file is ignored
    completely and not read from the disk at all.

    If no loader is given for a particular extension in the middle of
    the extension chain (e.g. ".markdown.") then the parsing process stops
    at this point and the read data will not be processed further even if
    loaders for other extensions earlier in the chain exist. (A warning
    is issued in this case, because it is probably a mistake.)

    The files are processed in alphabetical order of their filename. Files
    that define data that needs to be accessed from within other files should
    receive a filename that appears earlier in the alphabetical order, e.g.
        00_data_definition.json
        data_consumer.jinja2

    See function load() for how the files themselves are processed.

    Args:
        path (string): the directory to be scanned
        loaders (dict): A mapping file extension -> loader function.
                        see load()
        injected_metadata (dict): metadata that can be accessed from templates
        parent(sitetree.Folder): A reference to the parent folder object
    Returns:
        An sitetree.Folder mapping the basenames of each processed file to the
        contents as returned by the load() function.
    """
    assert not ('basename' in injected_metadata or
                'local' in injected_metadata)
    assert not parent or isinstance(parent, sitetree.Folder)

    folder = sitetree.Folder()
    if parent:
        folder['__parent'] = parent

    old_dir = os.getcwd()
    os.chdir(path)

    contents = os.listdir()
    contents.sort(key=str.lower)
    data_entries, data_dirs, page_dirs, page_entries = [], [], [], []
    for name in contents:
        if name.startswith("."):
            pass
        if is_excluded(name):
            continue
        if name.startswith('_'):
            if os.path.isdir(name):
                data_dirs.append(name)
            else:
                data_entries.append(name)
        else:
            if os.path.isdir(name):
                page_dirs.append(name)
            else:
                page_entries.append(name)

    site_path = injected_metadata.get('config', {}).get('site_path', '')
    languages = injected_metadata.get('config', {}).get('languages', ['ANY'])

    def read_entry(filename):
        if os.path.isdir(filename):
            folder[remove_locale(dirname)] = scan_directory(
                dirname, loaders, injected_metadata, parent=folder)
            return
        basename, ext = os.path.splitext(filename)
        # generate a chain of loaders for all subsequent extensions of a
        # file (e.g. "file.markdown.jinja2") so that the loader for the
        # last extension will be applied first.
        chain = []  # reset chain variable
        while ext:
            if ext in loaders:
                chain.append(loaders[ext])
                basename, ext = os.path.splitext(basename)
            else:
                warn("No loader registered for extension '%s' of file %s" %
                     (filename, ext))
                while ext:
                    basename, ext = os.path.splitext(basename)
        if chain:
            print("Loading file %s" % filename)
            metadata = injected_metadata.copy()
            metadata.update({'basename': basename, 'local': folder})
            chainloader = loader.gen_chainloader(chain)
            folder[remove_locale(basename)] = loader.load(
                filename, chainloader, injected_metadata=metadata)

    def multilang(entry_name):
        """Unless the entry specifies a particular language (or 'ANY') in its
        file name, parent directories or metadata within the file, read the
        entry several times, one time for each language specified in the
        configuration data of the site.
        """
        if 'language' in injected_metadata or loader.peep_lang(entry_name):
            read_entry(entry_name)
        else:
            locale = extract_locale(loader.fullpath(entry_name, site_path))
            locales = [locale] if locale else languages
            for lang in locales:
                # consider file to be of language 'lang' when reading and
                # rendering templates
                injected_metadata['language'] = lang
                read_entry(entry_name)
            del injected_metadata['language']

    for filename in data_entries:
        multilang(filename)
    for dirname in data_dirs + page_dirs:
        multilang(dirname)
    for filename in page_entries:
        multilang(filename)

    os.chdir(old_dir)
    return folder


###############################################################################
#
# test code
#
###############################################################################


def test_load():
    """Simple Test for load()-function."""
    old_dir = os.getcwd()
    generator = sitetree.Folder()
    generator['_data'] = scan_directory("_data",
                                        {".yaml": loader.yaml_loader,
                                         ".csv": loader.csv_loader,
                                         ".ttbl": loader.load_transtable},
                                        {'language': 'ANY'})
    os.chdir("tests/testdata")
    bibdata = loader.load("_bibdata_ANY.bib", loader.bibtex_loader,
                          injected_metadata={'config': {"template_paths":
                                                        ["../../"],
                                                        "site_path": ""}})  # sys.argv[1] if len(sys.argv) > 1 else os.getcwd()}})
    result = loader.load("Kants_Friedensschrift.md.jinja2",
                         loader.gen_chainloader([loader.jinja2_loader,
                                                 loader.markdown_loader]),
                         injected_metadata={'basename': "Kants_Friedensschrift",
                                            'local': {"_bibdata": bibdata},
                                            'config': {"template_paths":
                                                       ["../../"],
                                                       "site_path": sys.argv[1] if len(sys.argv) > 1 else os.getcwd()},
                                            'root': generator})
    for lang in result:
        print(result[lang]['content'])
    os.chdir(old_dir)


def test_scan_directory(metadata):
    """Simple Test for scan_directory()-function."""
    tree = scan_directory("./", loader.STOCK_LOADERS, metadata)
    for lang in ["DE", "EN"]:
        with open("output_%s.html" % lang, "w") as out:
            out.write(
                '<html>\n<head>\n<meta charset="utf-8"/>\n</head>\n<body>\n')
            for page in tree:
                if lang in tree[page]:
                    out.write(str(tree[page][lang]['content']))
            out.write("\n</body>\n</html>\n")


if __name__ == "__main__":
    # print("hi")
    test_load()
    # test_scan_directory()
