"""loader.py -- loader for markup text
"""


__update__ = "2014-12-06"


import os
import warnings

import jinja2
import markdown
import yaml

from bibloader import bibtex_loader
import locale_strings
import sitetree
warnings.simplefilter('always')


def markdown_loader(data, metadata):
    """A loader function for markdown."""
    return markdown.markdown(data)


def yaml_loader(data, metadata):
    """A loader function for yaml."""
    if data:
        return yaml.load(data)
    else:
        return ""


class CustomJinja2Loader(jinja2.FileSystemLoader):

    """A custom jinja2 loader that returns the page templates and reads
    further templates from the disk if requested.

    Attributes:
        data(string): The page template
    """

    def __init__(self, data, template_paths):
        paths = ["./"]
        if template_paths:
            if isinstance(template_paths, str):
                paths.append(template_paths)
            else:
                paths.extend(template_paths)
        jinja2.FileSystemLoader.__init__(self, paths)
        self.data = data

    def get_source(self, environment, template):
        print(">>> " + template, environment.globals)
        # assert False
        if template:
            return jinja2.FileSystemLoader.get_source(self, environment,
                                                      template)
        else:
            return (self.data, "", lambda: True)


def jinja2_loader(data, metadata):
    """A loader for jinja2 templates.
    """
    templ_path = ""
    if "config" in metadata and "template_path" in metadata["config"]:
        templ_path = metadata["config"]["template_path"]
    env = jinja2.Environment(loader=CustomJinja2Loader(data, templ_path))
    env.globals.update(metadata)
    templ = env.get_template("")
    result = templ.render()  # metadata)
    return result


def gen_chainloader(loader_list):
    """Returns a loader function that applies a list of loaders sequentially.

    Args:
        loader_list: A list of functions (data, metadata) -> data
    """
    chain = tuple(loader_list)

    def chainloader(data, metadata):
        for loader in chain:
            data = loader(data, metadata)
        return data

    return chainloader


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
                raise ValueError("Unrecognized locale %s in filename %s" %
                                 (lc, filepath))
        if L > 3 and name[-3] == "_":
            lc = name[-2:]
            if lc in locale_strings.twoletter_set:
                return lc
            elif lc.isalpha():
                raise ValueError("Unrecognized locale %s in filename %s" %
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
    HEADER_DATA_MISMATCH = "Wrong number of headers"
    END_MARKER_MISSING = "No end marker for last header"
    LANGUAGE_INFO_MISSING = "Language info missing in chunk header"


def load(filepath,
         data_loader=lambda data, metadata: data,
         metadata_loader=lambda data: yaml_loader(data, {}),
         injected_metadata={},
         delimiter="+++"):
    """Loads a file containing markup-text or data and (potentially) metadata.

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

    End of Example

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

    page = sitetree.Entry()
    common_metadata = {}
    common_data = ""
    first_chunk_flag = True  # Only one common chunk is allowed and this must
    # be at the very beginning of the file
    for raw_metadata, raw_data in zip(metadata_headers, data_chunks):
        metadata = {}
        metadata.update(injected_metadata)
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
            page[metadata["language"]] = variant
    if not page:
        site_path = injected_metadata.get('config', {}).get('site_path', '')
        lang = extract_locale(fullpath(filepath, site_path))
        page[lang] = {'metadata': common_metadata,
                      'content': data_loader(common_data, common_metadata)}

    return page


def scan_directory(path, loaders, injected_metadata):
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
                        see load_and_split()
        injected_metadata (dict): metadata that can be accessed from templates
    Returns:
        An OrderedDict mapping the basenames of each processed file to the
        contents as returned by the load_and_split() function.
    """
    old_dir = os.getcwd()
    os.chdir(path)
    pages = sitetree.Folder()
    chain = []  # declare chain variable
    contents = os.listdir()
    contents.sort(key=str.lower)
    for filename in contents:
        if filename.startswith("__"):
            continue
        basename, ext = os.path.splitext(filename)
        # generate a chain of loaders for all subsequent extensions of a file
        # (e.g. "file.markdown.jinja2") so that the loader for the last
        # extension will be applied first.
        chain = []  # reset chain variable
        while ext:
            if ext in loaders:
                chain.append(loaders[ext])
                basename, ext = os.path.splitext(basename)
            else:
                warnstr = "No loader registered for extension '%s'" % ext
                print(warnstr)
                warnings.warn(warnstr, Warning)
                ext = ""
        if chain:
            print("Loading file %s" % filename)
            metadata = {'basename': basename, 'local': pages}
            for key in metadata:
                if key in injected_metadata:
                    raise ValueError(("Keys {0!s} not allowed in injected " +
                                      " metadata. Stuck on key {1!s}").format(
                                     metadata.keys(), key))
            metadata.update(injected_metadata)
            pages[basename] = load(filename, gen_chainloader(chain),
                                   injected_metadata=metadata)
            # local access to local data only during loading!
            for lang in pages[basename]:
                del pages[basename][lang]['metadata']['local']

    os.chdir(old_dir)
    return pages


def test_load_and_split():
    old_dir = os.getcwd()
    os.chdir("tests/testdata")
    bibdata = load("_bibdata.bib", bibtex_loader)
    result = load("Kants_Friedensschrift.md.jinja2",
                  gen_chainloader([jinja2_loader, markdown_loader]),
                  injected_metadata={'basename': "Kants_Friedensschrift",
                                     'local': {"_bibdata": bibdata},
                                     'config': {"template_path":
                                                "../../"}})
    for lang in result:
        print(result[lang]['content'])
    os.chdir(old_dir)


def test_scan_directory(metadata):
    tree = scan_directory("./", {".md": markdown_loader,
                                 ".jinja2": jinja2_loader,
                                 ".bib": bibtex_loader},
                          metadata)
    for lang in ["DE", "EN"]:
        with open("output_%s.html" % lang, "w") as out:
            out.write(
                '<html>\n<head>\n<meta charset="utf-8"/>\n</head>\n<body>\n')
            for page in tree:
                if lang in tree[page]:
                    out.write(str(tree[page][lang]['content']))
            out.write("\n</body>\n</html>\n")


if __name__ == "__main__":
    test_load_and_split()
    # test_scan_directory()
