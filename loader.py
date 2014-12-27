"""loader.py -- loader for markup text
"""
import collections
import csv
import functools
import io
import os
import warnings

import jinja2
import markdown
import yaml

from bibloader import bibtex_loader
import locale_strings
import sitetree


__update__ = "2014-12-06"


warnings.simplefilter('always')


##############################################################################
#
# utility functions
#
##############################################################################


def warn(msg):
    """Issue a warning."""
    print(msg)
    warnings.warn(msg, Warning)


def translate(expression, lang, folder, generator):
    """Search for a translation of 'expression' into language 'lang'.

    The search starts in 'folder', continues through 'folder's parent folders
    and ultimately searches 'generator'['_data']['_transtable']
    """
    try:
        tr = sitetree.cascaded_getitem(expression, folder, '_transtable', lang)
    except KeyError:
        tr = generator['_data']['_transtable'].\
            bestmatch(lang)['content'][expression]
    return tr


@jinja2.environmentfilter
def jinja2_tr(env, expression):
    """Translates expression within the given jinja2 environment.

    This requires that the variables 'local', 'language' and 'generator' are
    defined in the jinja2 environment.
    """
    return translate(expression, env.globals['language'], env.globals['local'],
                     env.globals['generator'])


###############################################################################
#
# loader functions for specific data types
#
###############################################################################


def completing_loader(loader_func):
    """Decorator that marks a function as full loader.

    Completing loaders assemble different language versions of the data all by
    themselves, whereas ordinary loader leave this to the load() function.

    They can be chained with ordinary loaders, but there can be only one
    completing loader in the chain and it must appear at the end of the chain.
    A chain that contains a completing loader is itself considered as a
    completing loader.

    Completing loaders return a dictionary of one ore more language versions of
    content found in the file (instead of just the processed content).
    """
    @functools.wraps(loader_func)
    def wrapper(filename, metadata):
        assert isinstance(metadata, collections.Mapping)
        entry = loader_func(filename, metadata)
        assert isinstance(entry, collections.Mapping)
        if isinstance(entry, sitetree.Entry):
            return entry
        else:
            return sitetree.Entry(entry)

    wrapper.completing_loader = True
    return wrapper


def is_completing_loader(loader_func):
    return hasattr(loader_func, 'completing_loader')


def markdown_loader(data, metadata):
    """A loader function for markdown."""
    return markdown.markdown(data)


def yaml_loader(data, metadata):
    """A loader function for yaml."""
    if data:
        return yaml.load(data)
    else:
        return ""


def csv_loader(data, metadata):
    """A loader for csv data.
    """
    with io.StringIO(data, newline='') as csvfile:
        dialect = csv.Sniffer().sniff(csvfile.read(2048), delimiters=";, \t")
        csvfile.seek(0)
        reader = csv.reader(csvfile, dialect)
        table = list(reader.__iter__())
        return table


class CustomJinja2Loader(jinja2.FileSystemLoader):

    """A custom jinja2 loader that returns the page templates and reads
    further templates from the disk if requested.

    Attributes:
        data(string): The page template
    """

    def __init__(self, data, template_paths):
        paths = ["./"]
        if template_paths:
            paths.extend(template_paths)
        jinja2.FileSystemLoader.__init__(self, paths)
        self.data = data

    def get_source(self, environment, template):
        if template:
            return jinja2.FileSystemLoader.get_source(self, environment,
                                                      template)
        else:
            return (self.data, "", lambda: True)


def jinja2_loader(data, metadata):
    """A loader for jinja2 templates.
    """
    templ_paths = ""
    if "config" in metadata and "template_paths" in metadata["config"]:
        templ_paths = metadata["config"]["template_paths"]
    env = jinja2.Environment(loader=CustomJinja2Loader(data, templ_paths))
    env.globals.update(metadata)
    env.filters['TR'] = jinja2_tr
    templ = env.get_template("")
    try:
        result = templ.render()  # tmpl.render(metadata)
    except jinja2.exceptions.TemplateNotFound:
        print(os.getcwd())
        print(os.path.abspath(os.getcwd()))
        assert False
    return result


def gen_chainloader(loader_list):
    """Returns a loader function that applies a list of loaders sequentially.

    Args:
        loader_list: A list of functions (data, metadata) -> data
    """
    assert loader_list  # must not be empty
    chain = tuple(loader_list)

    def chainloader(data, metadata):
        for loader in chain:
            data = loader(data, metadata)
        return data

    if is_completing_loader(chain[-1]):
        return completing_loader(chainloader)
    else:
        return chainloader


class RedundantTransTable(Exception):
    pass


@completing_loader
def load_transtable(table, metadata):
    """Reads a translation table from the disk.

    Each column contains the translations for one particular language.
    The first column is considered to contain the reference language.
    The first row of the table must contain the language codes.

    Args:
        table(nested list): A list of table rows
        metadata(dict): A metadata dictionary
    """
    keys = [table[row][0] for row in range(1, len(table))]
    if len(keys) != len(set(keys)):
        raise RedundantTransTable("Multiple occurrences of: {0!s}".format(
            collections.Counter(keys).most_common(3)))
    variants = sitetree.Entry()
    for i, lang in enumerate(table[0]):
        locale_strings.valid_locale(lang, raise_error=True)
        variants[lang] = {'metadata': metadata.copy(), 'content': {}}
        for k, key in enumerate(keys, 1):
            variants[lang]['content'][key] = table[k][i]
    return variants


##############################################################################
#
# high level generic loading functions for (compound) files and directories
#
##############################################################################


STOCK_LOADERS = {".md": markdown_loader,
                 ".jinja2": jinja2_loader,
                 ".bib": bibtex_loader,
                 ".csv": csv_loader,
                 ".ttbl": load_transtable}


def extract_locale(filepath):
    """Extracts locale information from filename or parent directory.
    Returns locale string or 'any'.

    Locale information is assumed to reside at the end of the basename of the
    file, right before the extension. It must either have the form "_xx_XX" or
    "_XX", eg. "_de_DE" or simply "_DE", and represent a valid locale.

    If no locale information is found in the file name the names of the parent
    directory are checked inward out for locale information.

    An error is reported, if there appears to be locale information
    but if it is malformed.

    'any' is returned if no (intended) locale information seems to be
    present in the filename or any of the parent directories' names.
    """

    def get_locale(name):
        L = len(name)
        if L > 4 and name[-4].upper() == "_ANY":
            return 'ANY'
        if L > 6 and name[-6] == "_" and name[-3] == "_":
            lc = name[-5:]
            if lc in locale_strings.fourletter_set:
                return lc
            elif name[-5:-3].islower() and name[-2:].isupper():
                raise locale_strings.LocaleError("%s in file %s" %
                                                 (lc, filepath))
        if L > 3 and name[-3] == "_":
            lc = name[-2:]
            if lc in locale_strings.twoletter_set:
                return lc
            elif lc.isalpha():
                raise locale_strings.LocaleError("%s in file %s" %
                                                 (lc, filepath))
        return 'nope'

    parent, path = os.path.split(filepath)
    while path:
        basename = os.path.splitext(path)[0]
        locale = get_locale(basename)
        if locale != 'nope':
            return locale
        parent, path = os.path.split(parent)
    return 'ANY'


def fullpath(path, root):
    """Returns the path starting from path root. Raises an error if root is
    not the beginning of the absolute path of the path."""
    abspath = os.path.abspath(path)
    if abspath.startswith(root):
        return abspath[len(root):]
    else:
        raise ValueError(("Mismatch between supposed root:\n%s\nand " +
                          "absolute path:\n%s") % (root, abspath))


class MalformedFile(Exception):
    END_MARKER_MISSING = "No end marker for last header"
    LANGUAGE_INFO_MISSING = "Language info missing in chunk header"


def load(filepath,
         data_loader=lambda data, metadata: data,
         metadata_loader=lambda data: yaml_loader(data, {}),
         injected_metadata={},
         delimiter="+++"):
    """Loads a file containing markup-text or data and possibly metadata
    in one or more different languages.

    Metadata, if present, stands at the beginning of the file and is enclosed
    by delimiter lines (e.g. '+++').

    The file itself may either a) contain different language versions of the
    same text or data or it may b) as a whole represent a specific language
    version.

    If a) the different language versions are contained within the file,
    each language version must follow as one block which is preceeded by
    a metadata header that assigns a language code to the key 'language',
    e.g. " language: DE " and possibly further metadata that is specific to
    the following language version of the text or data.

    General metadata and data which is valid for all language versions can
    be defined at the beginning of the file. In this case the 'language'
    variable must not be set in the first block of the file The data of this
    block is then prepended to all subsequent blocks and its metadata merged
    into their metadata.

    if b) the file as a whole represents a specific language version, the
    language code must be added to the file name between the basename and the
    file extension with an underscore as delimiter, e.g "index_DE.html".

    The type of text or data that is expected in the file is determined
    by the loader. It can be anything, e.g. html, markdown, plaintext, yaml,
    jason. Care should be taken that no delimiter lines appear accidentally
    in the text or data.

    The load() function itself behaves agnostic as to whether the file
    contains (markup) text or data. This is entirely up to the data_loader
    to decide, which may either return a text string or a dictionary.
    The metadata loader must return data in form of a dictionary.

    Example:

    +++
    layout: master
    URL: /example
    +++
    <!-- this will be shared by all language versions -->
    <script>console.log(":-)");</script>
    +++
    langauge: EN
    +++
    <p>Good Morning!</p>
    +++
    language: DE
    +++
    <p>Guten Morgen!</p>


    Args:
        filepath (string): A file path, e.g. "example.html"
        data_loader(func): A function that processes a data block and returns
                           a text string or a dictionary.
        metadata_loader(func): A function that parses the metadata and returns
                               a dictionary of that data.
        injected_metadata(dict): Further metadata that is added to the common
                                 metadata. Injected Metadata will be overridden
                                 by metadata in the file in case of identical
                                 key names.
        delimiter (string): A delimiter line for metadata blocks, e.g. "+++"

    Returns:
        A dict mapping language keys to the corresponding metadata and data.
        For example:
        {'DE': {'metadata': {...}, 'content': '<p>Guten Morgen!</p>'},
         'EN': ... }
    """
    assert not is_completing_loader(data_loader)
    assert not is_completing_loader(metadata_loader)

    metadata_headers = []
    data_chunks = []
    with open(filepath, "r") as f:
        line = f.readline()
        # skip leading empty lines
        while line and not line.rstrip():
            line = f.readline()
        while line:
            if line.rstrip() == delimiter:
                # process yaml header
                header = []
                line = f.readline()
                while line and line.rstrip() != delimiter:
                    header.append(line)
                    line = f.readline()
                if not line:
                    raise MalformedFile(MalformedFile.END_MARKER_MISSING)
                line = f.readline()
                # add empty data block if next header directly follows
                # or if end of file is reached after delimiter
                if not line or line.rstrip() == delimiter:
                    data_chunks.append("")
                metadata_headers.append("".join(header))
            else:
                # process markup chunk
                chunk = []
                while line and line.rstrip() != delimiter:
                    chunk.append(line)
                    line = f.readline()
                data_chunks.append("".join(chunk))
    if not data_chunks:
        data_chunks.append("")
    if len(metadata_headers) < len(data_chunks):
        metadata_headers.insert(0, "")

    entry = sitetree.Entry()
    common_metadata = {}
    common_data = ""
    first_chunk_flag = True  # Only one common chunk is allowed and this must
    # be at the very beginning of the file
    for raw_metadata, raw_data in zip(metadata_headers, data_chunks):
        metadata = injected_metadata.copy()
        metadata.update(common_metadata)
        metadata.update(metadata_loader(raw_metadata))
        data = common_data + raw_data if common_data else raw_data
        if "language" not in metadata:
            if first_chunk_flag:
                common_metadata = metadata
                common_data = data
                first_chunk_flag = False
            else:
                raise MalformedFile(MalformedFile.LANGUAGE_INFO_MISSING +
                                    "\nheader data:\n" + raw_metadata)
        else:
            variant = {
                'metadata': metadata,
                'content': data_loader(data, metadata)
            }
            entry[metadata["language"]] = variant
    if not entry:
        # the whole file contains only one language version and no 'language'
        # in its metadata (or no metadata at all). Therefore the language
        # will be inferred from the filename or directory name or set to 'ANY'
        site_path = injected_metadata.get('config', {}).get('site_path', '')
        lang = extract_locale(fullpath(filepath, site_path))
        entry[lang] = {'metadata': common_metadata,
                       'content': data_loader(common_data, common_metadata)}

    return entry


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
        if name.startswith('__'):
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

    def read_entry(filename):
        basename, ext = os.path.splitext(filename)
#         if is_completing_loader(loaders.get(ext, None)):
#             metadata = injected_metadata.copy()
#             metadata.update({'basename': basename, 'local': folder})
#             folder[basename] = loaders[ext](filename, metadata)
#         else:
        # generate a chain of loaders for all subsequent extensions of a
        # file (e.g. "file.markdown.jinja2") so that the loader for the
        # last extension will be applied first.
        chain = []  # reset chain variable
        while ext:
            if ext in loaders:
                chain.append(loaders[ext])
                basename, ext = os.path.splitext(basename)
            else:
                warn("No loader registered for extension '%s'" % ext)
                ext = ""
        if chain:
            print("Loading file %s" % filename)
            metadata = injected_metadata.copy()
            metadata.update({'basename': basename, 'local': folder})
            chainloader = gen_chainloader(chain)
            if is_completing_loader(chainloader):
                with open(filename) as f:
                    folder[basename] = chainloader(f.read(), metadata)
            else:
                folder[basename] = load(filename, chainloader,
                                        injected_metadata=metadata)

    for filename in data_entries:
        read_entry(filename)
    for dirname in data_dirs + page_dirs:
        folder[dirname] = scan_directory(dirname, loaders, injected_metadata,
                                         parent=folder)
    for filename in page_entries:
        read_entry(filename)

    os.chdir(old_dir)
    return folder


###############################################################################
#
# test code
#
###############################################################################


def test_load():
    old_dir = os.getcwd()
    generator = sitetree.Folder()
    generator['_data'] = scan_directory("_data",
                                        {".yaml": yaml_loader,
                                         ".csv": csv_loader,
                                         ".ttbl": load_transtable},
                                        {})
    os.chdir("tests/testdata")
    bibdata = load("_bibdata.bib", bibtex_loader)
    result = load("Kants_Friedensschrift.md.jinja2",
                  gen_chainloader([jinja2_loader, markdown_loader]),
                  injected_metadata={'basename': "Kants_Friedensschrift",
                                     'local': {"_bibdata": bibdata},
                                     'config': {"template_paths":
                                                ["../../"]},
                                     'generator': generator})
    for lang in result:
        print(result[lang]['content'])
    os.chdir(old_dir)


def test_scan_directory(metadata):
    tree = scan_directory("./", STOCK_LOADERS, metadata)
    for lang in ["DE", "EN"]:
        with open("output_%s.html" % lang, "w") as out:
            out.write(
                '<html>\n<head>\n<meta charset="utf-8"/>\n</head>\n<body>\n')
            for page in tree:
                if lang in tree[page]:
                    out.write(str(tree[page][lang]['content']))
            out.write("\n</body>\n</html>\n")


if __name__ == "__main__":
    test_load()
    # test_scan_directory()
