"""generator.py - loading at directory level and site generation

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

import os
import re
import shutil
import subprocess

import loader
from locale_strings import extract_locale, remove_locale
import sitetree
import utility


##############################################################################
#
# read site data
#
##############################################################################

include_patterns = [
    r'\.ht.*$'
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


def is_static_entry(name, site_path, config, folder_config):
    """Returns true, if file or subdirectory shall only be copied, but not be
    processed."""
    # print(config.get('static_entries', set()))
#     if name == "apppages":
#         print(loader.fullpath(name, site_path))
#         print(name, site_path)
#         print(config.get('static_entries', set()))
#         print(name in config.get('static_entries', set()))
    return name in folder_config.get('static_entries', set()) or \
        loader.fullpath(name, site_path) in config.get('static_entries', set())


def get_basename(filepath):
    """Returns the filename without path, extension, locale information or
    order number.
    """
    basename, ext = os.path.splitext(os.path.basename(filepath))
    while ext:
        basename, ext = os.path.splitext(basename)
    # return remove_locale(basename)
    return re.sub(r"^\d+_", "", remove_locale(basename))


class BadStructureError(Exception):
    PAGE_ENTRY_IN_DATA_DIR = "Data directories should only contain fragments"\
                             " or data, but no complete pages!"


def scan_directory(path, loaders, injected_metadata={}, organizers=[],
                   parent=None):
    """Reads all files in the directory path for which a loader is given
    for at least the last extension.

    If a file has several extensions, e.g. "example.markdown.jinja2" then the
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
        organizers (list): A list of functions that are applied successively
                           to all already scanned folders.
        parent (sitetree.Folder): A reference to the parent folder object
    Returns:
        An sitetree.Folder mapping the basenames of each processed file to the
        contents as returned by the load() function.
    """
    assert 'local' not in injected_metadata
    assert 'basename' not in injected_metadata
    assert not parent or isinstance(parent, sitetree.Folder)

    config = injected_metadata.get('config', {})
    site_path = config.get('site_path', '')
    languages = config.get('languages', ['ANY'])
    is_datadir = os.path.basename(path).startswith("_")

    folder = sitetree.Folder()
    folder.parent = parent
    folder.metadata['config'] = config
    folder.metadata['foldername'] = get_basename(path)
    folder.metadata['folderconfig'] = {}

    old_dir = os.getcwd()
    os.chdir(path)
    contents = os.listdir()
    contents.sort(key=str.lower)
    for entry in contents:
        if entry.startswith("__config."):
            folder_cfg = loader.load_plain(entry, loader.STOCK_LOADERS)
            folder.metadata["folderconfig"] = folder_cfg
    data_entries, data_dirs, page_dirs, page_entries = [], [], [], []
    for name in contents:
        if is_excluded(name):
            continue
        elif is_static_entry(name, site_path, config,
                             folder.metadata['folderconfig']):
            folder[name] = sitetree.StaticEntry(name)
        elif name.startswith('_'):
            if os.path.isdir(name):
                data_dirs.append(name)
            else:
                data_entries.append(name)
        else:
            if os.path.isdir(name):
                page_dirs.append(name)
            else:
                page_entries.append(name)

    def read_entry(filename, metadata):
        if os.path.isdir(filename):
            folder[remove_locale(filename)] = scan_directory(
                filename, loaders, metadata, parent=folder)
            return
        # generate a chain of loaders for all subsequent extensions of a
        # file (e.g. "file.markdown.jinja2") so that the loader for the
        # last extension will be applied first.
        chainloader = loader.get_loader(filename, loaders)
        # for debugging:
        if chainloader == loader.passthru_loader:
            return
        # fp = os.path.join(os.getcwd(), filename)
        # print("Loading file %s" % loader.fullpath(fp, site_path))
        print("Loading file %s" % filename)
        metadata.update({'local': folder, 'basename': get_basename(filename)})
        pages = loader.load(filename, chainloader, injected_metadata=metadata)
        for name, entry in pages.items():
            if is_datadir and entry.is_page():
                raise BadStructureError(
                    BadStructureError.PAGE_ENTRY_IN_DATA_DIR +
                    " Offending File: %s" % filename)
            if name in folder:
                # assume that other lang. versions of the entry already exist
                assert not (set(entry.keys()) & set(folder[name].keys())), \
                    "Overlap (ambiguity) of different language versions!\n" + \
                    "File: " + os.path.join(os.getcwd(), filename) + " " +\
                    str(set(entry.keys()) & set(folder[name].keys()))
                folder[name].update(entry)
            else:
                folder[name] = entry

    def multilang(entry_name):
        """Unless the entry specifies a particular language (or 'ANY') in its
        file name, parent directories or metadata within the file, read the
        entry several times, one time for each language specified in the
        configuration data of the site.
        """
        metadata = injected_metadata.copy()
        metadata.update(folder.metadata["folderconfig"])
        if ('language' in folder.metadata["folderconfig"] or
                loader.peep_lang(entry_name) or os.path.isdir(entry_name)):
            read_entry(entry_name, metadata)
        else:
            locale = extract_locale(loader.fullpath(entry_name, site_path))
            locales = [locale] if locale else languages
            for lang in locales:
                # consider file to be of language 'lang' when reading and
                # rendering templates
                metadata['language'] = lang
                read_entry(entry_name, metadata)

    for filename in data_entries:
        multilang(filename)
    for dirname in data_dirs:
        multilang(dirname)
        for organizer in organizers:
            organizer(dirname)
    for dirname in page_dirs:
        multilang(dirname)
    for filename in page_entries:
        multilang(filename)

    os.chdir(old_dir)
    return folder


##############################################################################
#
# write site
#
##############################################################################


#
# writers
#

def remove_trailing_spaces(root, content):
    """Returns a version of text where all trailing spaces are removed"""
    return re.sub(" +\n", "\n", content)


def fillin_URL_templates(root, content):
    """Replaces URLs in href attributes that start with 'STATIC:' or
    'TOPLEVEL:' with proper relative URLs.
    TOPLEVEL means 'the highest level in the same language branch'
    STATIC means 'the root level of the site'
    """
    steps = []
    while root.parent:
        steps.append("..")
        root = root.parent
    toplevel = "/".join(steps) + "/"
    steps.append("..")
    static = "/".join(steps) + "/"

    content = re.sub('href *= *"STATIC:/?', 'href="' + static, content)
    content = re.sub('src *= *"STATIC:/?', 'src="' + static, content)
    content = re.sub('content *= *"STATIC:/?', 'content="' + static, content)
    content = re.sub('href *= *"TOPLEVEL:/?', 'href="' + toplevel, content)
    content = re.sub('src *= *"TOPLEVEL:/?', 'src="' + toplevel, content)
    content = re.sub('content *= *"TOPLEVEL:/?', 'content="' + toplevel, content)
    return content


def add_img_width_height(root, content):
    """Adds with and height attributes to image tags.
    """
    # TODO: program this function
    pass


STOCK_WRITERS = [remove_trailing_spaces, fillin_URL_templates]


#
# preprocessors
#

STOCK_PREPROCESSORS = {}    # preprocessors to be used for production code
DEBUG_PREPROCESSORS = {}    # preprocessors to be used while debugging

try:
    dump = subprocess.check_output(["cleancss", "--help"],
                                   stderr=subprocess.STDOUT)

    def css_compressor(src, dst):
        """Minifies a css stylesheet with cleancss
        (https://github.com/jakubpawlowicz/clean-css) at location `src` and
        writes the result to `dst`. Returns the destination path.
        """
        css = subprocess.check_output(["cleancss", src],
                                      stderr=subprocess.STDOUT)
        with open(dst, "wb") as css_file:
            css_file.write(css)
        return dst

    STOCK_PREPROCESSORS[".css"] = css_compressor

except FileNotFoundError:
    pass


try:
    dump = subprocess.check_output(["closure", "--help"])

    def js_compressor(src, dst):
        """Minifies a javascript file with the closure compiler
        (https://developers.google.com/closure/compiler/) at location `src`
        and writes the result to `dst`. Returns the destination path.
        """
        if src.find(".min.") < 0:
            jsmin = subprocess.check_output(["closure", src])
        else:
            with open(src, "rb") as f:
                jsmin = f.read()
        with open(dst, "wb") as jsmin_file:
            jsmin_file.write(jsmin)
        return dst

    STOCK_PREPROCESSORS[".js"] = js_compressor


except FileNotFoundError:
    pass


try:
    dump = subprocess.check_output(["lessc", "--help"])

    def less_preprocessor(src, dst, debug):
        """Preprocesses less stylesheet with less.js (http://lesscss.org/) at
        location src and writes the result to 'dst'. Resturns the destination
        path.
        """
        dst_name = os.path.splitext(dst)[0] + '.css'
        css = subprocess.check_output(["lessc", "", src])
        with open(dst_name, "wb") as css_file:
            css_file.write(css)
        if not debug and ".css" in STOCK_PREPROCESSORS:
            dst_name = STOCK_PREPROCESSORS[".css"](dst_name, dst_name)
        return dst_name

    STOCK_PREPROCESSORS[".less"] = \
        lambda src, dst: less_preprocessor(src, dst, False)
    DEBUG_PREPROCESSORS[".less"] = \
        lambda src, dst: less_preprocessor(src, dst, True)

except FileNotFoundError:
    pass


if ".less" not in STOCK_PREPROCESSORS:
    # lesscpy only second choice, because version 0.10.2 is still buggy :(
    try:
        import six
        import lesscpy

        def lesscpy_preprocessor(src, dst):
            """Preprocesses less stylesheet with lesscpy
            (https://pypi.python.org/pypi/lesscpy) at location src and writes
            the result to 'dst'.
            """
            with open(src) as less_file:
                less_data = less_file.read()
                css = lesscpy.compile(six.StringIO(less_data), minify=True)
            dst_name = os.path.splitext(dst)[0] + '.css'
            with open(dst_name, "w") as css_file:
                css_file.write(css)
            return dst_name

        STOCK_PREPROCESSORS[".less"] = lesscpy_preprocessor
        DEBUG_PREPROCESSORS[".less"] = lesscpy_preprocessor

    except ImportError:
        pass

#
# site creation
#


def create_site(root, site_path, metadata, writers=STOCK_WRITERS,
                preprocessors=STOCK_PREPROCESSORS):
    """Writes a a website or folder of a website stored in a sitetree structure
    to the disk.

    Parameters:
        root (sitetree.Folder): The tree representing the website
        site_path(string): Path where the website should be stored
        writers(list): A list of writer functions
            (root, current_content) -> content that can manipulate content
            (like replace special tokens or keywords like "STATIC") just before
            writing them to the disk.
        preprocessors(dicstionary): A dictionary of external preprocessors
            (file extension -> preprocessor) that preprocesses files before
            writing them. Other than writers, preprocessors work directly on
            the files rather than on the data, loaded into memory. Usually a
            preprocessor function is merely a stub that calls an external
            programm.
    """
    assert isinstance(root, sitetree.Folder)
    sitemap = utility.Sitemap(metadata.get('config', {}).get('sitemap_exclude', []))
    all_languages = root.metadata.get('config', {}).get('languages', ['ANY'])

    def create_static_entries(root, path):
        for entry in root:
            if isinstance(root[entry], sitetree.StaticEntry):
                print("Copying static dir or file: " + entry)
                sitemap.extend(root[entry].copy_entry(path, preprocessors))
            elif isinstance(root[entry], sitetree.Folder):
                create_static_entries(root[entry], os.path.join(path, entry))

    def create_branch(root, path, lang, writers):
        with utility.create_and_enter_dir(os.path.basename(path)):
            print("Creating directory " + path)
            for entry in root:
                if entry.startswith("_"):
                    continue

                if isinstance(root[entry], sitetree.Folder):
                    if not os.path.exists(entry):
                        os.mkdir(entry)
                    create_branch(root[entry], path + "/" + entry, lang,
                                  writers)

                elif not isinstance(root[entry], sitetree.StaticEntry):
                    if root[entry].is_data() or root[entry].is_fragment():
                        print("%s is not an html page!" % entry)
                    else:
                        page = root[entry].bestmatch(lang)
                        entryname = entry + ".html"
                        content = page['content']
                        for wr in writers:
                            content = wr(root, content)

                        # only overwrite generated files if changes occured
                        compare = ""
                        if os.path.isfile(entryname):
                            with open(entryname, "r", encoding="utf-8") as f:
                                compare = f.read()

                        # speed this up with generating and saving hash values?
                        if compare != content:
                            with open(entryname, "w", encoding="utf-8") as f:
                                print("Writing file " + entryname)
                                f.write(content)

                        pri = page['metadata'].get('sitemap-priority', '0.5')
                        cfreq = page['metadata'].get('sitemap-changefreq',
                                                     'monthly')
                        alt_locs = []
                        if len(all_languages) > 1:
                            for l in all_languages:
                                l_loc = l + path[len(lang):] + "/" + entryname
                                alt_locs.append({'lang': l, 'loc': l_loc})
                        sitemap.append({"loc": path + "/" + entryname,
                                        "alt_locs": alt_locs,
                                        "lastmod": utility.isodate(entryname),
                                        "changefreq": cfreq,
                                        "priority": "%1.1f" % float(pri)})

    shutil.copy2(metadata.get('config', {}).get('root_index', '__root.html'),
                 os.path.join(site_path, "index.html"))

    with utility.create_and_enter_dir(site_path):
        create_static_entries(root, "")
        for lang in all_languages:
            create_branch(root, lang, lang, writers)

        base_url = metadata.get('config', {}).get('base_url', '')
        assert base_url[-1:] != "/"

        print("Writing sitemap.xml")
        sitemap.write('sitemap.xml', base_url)



##############################################################################
#
# main function
#
##############################################################################


def generate_site(path, metadata):
    """Generates the site from the source at 'path'.
    """
    tree = scan_directory(path, loader.STOCK_LOADERS, metadata)
    preprocessors = DEBUG_PREPROCESSORS if metadata.get("debug", False) \
        else STOCK_PREPROCESSORS
    assert os.path.isdir(path)
    sitepath = os.path.join(path, '__site')
    if not os.path.exists(sitepath):
        os.mkdir(sitepath)
    else:
        assert os.path.isdir(sitepath)
    create_site(tree, os.path.join(path, '__site'), metadata, STOCK_WRITERS,
                preprocessors)
