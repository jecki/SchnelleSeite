"""loader.py -- loader for markup text

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
import csv
import functools
import io
import json
import math
import os

import jinja2
import markdown
import yaml

from bibloader import bibtex_loader
import locale_strings
import sitetree


__update__ = "2014-12-06"


##############################################################################
#
# utility functions
#
##############################################################################


def translate(expression, lang, folder, generator_resources):
    """Search for a translation of 'expression' into language 'lang'.

    The search starts in 'folder', continues through 'folder's parent folders
    and ultimately searches site_generator['_data']['_transtable']
    """
    try:
        tr = sitetree.cascaded_getitem(expression, folder, '_transtable', lang)
    except KeyError as err:
        if err.args[0] == expression:
            tr = generator_resources['_data']['_transtable'].\
                bestmatch(lang)['content'][expression]
        else:
            raise err
    return tr


@jinja2.environmentfilter
def jinja2_translate(env, expression):
    """Translates expression within the given jinja2 environment.

    This requires that the variables 'local', 'language' and 'root' are
    defined in the jinja2 environment.
    """
    return translate(expression, env.globals['language'], env.globals['local'],
                     env.globals['config']['generator_resources'])


@jinja2.environmentfilter
def jinja2_targetpage(env, target):
    """Returns the page basename (without ".html") of a link target.
    E.g. "authors.html#Shakespeare" yields "authors"
    """
    return (target.split("#")[0]).split(".")[0]


@jinja2.environmentfilter
def jinja2_linktarget(env, target):
    """Makes sure that target is a proper link target."""
    parts = target.split("#")
    if parts[0] and not parts[0].endswith(".html"):
        parts[0] += ".html"
    return "#".join(parts)


@jinja2.environmentfilter
def jinja2_getcontent(env, datasource):
    """Returns the content of a data source."""
    return sitetree.getentry(env.globals['local'], datasource,
                             env.globals['language'])['content']


@jinja2.environmentfilter
def jinja2_getmetadata(env, datasource, key):
    """Returns a particular item from the metadata of an entry."""
    return sitetree.getentry(env.globals['local'], datasource,
                             env.globals['language'])['metadata'][key]


@jinja2.environmentfilter
def jinja2_getitem(env, datasource, key):
    """Returns a paritcular item from a data source that is a dictionary."""
    return sitetree.getitem(key, env.globals['local'], datasource,
                            env.globals['language'])


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


@jinja2.environmentfilter
def jinja2_fragments(env, directory, orderby=None):
    """Returns a list of pathnames pathnames (starting from directory) of all
    fragments in a directory.
    Parameters:
        directory(string): The directory from the the fragments shall be taken.
        orderby(string): A metadata parameter which determines the order of
            the fragments. Instead of supplying this function with this
            parameter it may also be set in the metadata of the template
            or in the "__config" file of the fragments directory. The orderby
            parameter in the template metadata (if present) overrides the same
            parameter in the fragment's directories' "__config" file. The
            orderby argument passed to this function overrides all both.
    """
    folder = env.globals['local'][directory]
    order = orderby or env.globals.get('orderby') or \
        env.globals['local'][directory].get('orderby')
    return collect_fragments(folder, directory, order)


@jinja2.environmentfilter
def jinja2_multicast_pagename(env, subpage):
    """Returns the basename of the output page on which a particular subpage
    appears.
    """
    return env.globals['MC_PAGENAMES'][subpage]


def other_lang_URL(folder, basename, lang):
    """Returns a relative link from the file 'basename' in 'folder' to the
    the same file in the language version 'lang'.
    """
    path = []
    while folder.parent:
        path.append(folder.metadata['foldername'])
        folder = folder.parent
    path.append(lang)
    path.extend(['..'] * len(path))
    path.reverse()
    path.append(basename + ".html")
    return "/".join(path)


@jinja2.environmentfilter
def jinja2_other_lang_URL(env, lang):
    """Returns the URL to a different language version of the current page.
    """
    return other_lang_URL(env.globals['local'], env.globals['basename'], lang)


@jinja2.environmentfilter
def jinja2_markdownify(env, text):
    """Runs 'text' through a markdown processor and returns the resultant
    html.
    """
    return markdown.markdown(text)


@jinja2.environmentfilter
def jinja2_filepath_basename(env, filepath):
    """Returns the base name, i.e. the filename w/o path and extension, of
    'filepath'. Note the semantics of this filter differ from
    python's os.path.basename!.
    """
    return os.path.splitext(os.path.basename(filepath))[0]


@jinja2.environmentfilter
def jinja2_filepath_ext(env, filename):
    """Returns the extension of filename.
    """
    return os.path.splitext(filename)[1]


@jinja2.environmentfilter
def jinja2_split(env, s, ch):
    """Splits string 's' with character 'ch' as delimiter into a list of parts.
    """
    return s.split(ch)


###############################################################################
#
# loader functions for specific data types
#
###############################################################################


def completing_loader(loader_func):
    """Decorator that marks a function as full loader.

    Completing loaders assemble different language versions of the data all by
    themselves, whereas ordinary loaders leave this to the load() function.

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


def markdown_loader(text, metadata):
    """A loader function for markdown."""
    # TODO: Remove debug code here
#     if metadata['basename'] == "How_Models_Fail":
#         print(text)
#         print(markdown.markdown(text))
    return markdown.markdown(text)


def yaml_loader(text, metadata):
    """A loader function for yaml."""
    if text:
        return yaml.load(text)
    else:
        return {}


def json_loader(text, metadata):
    """A loader function for json."""
    if text:
        return json.loads(text)
    else:
        return {}


def csv_loader(text, metadata):
    """A loader for csv text.
    """
    with io.StringIO(text, newline='') as csvfile:
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


def jinja2_loader(text, metadata):
    """A loader for jinja2 templates.
    """
    templ_paths = ""
    if "config" in metadata and "template_paths" in metadata["config"]:
        templ_paths = metadata["config"]["template_paths"]
    env = jinja2.Environment(loader=CustomJinja2Loader(text, templ_paths))
    env.globals.update(metadata)
    # TODO: catch errors because of use of reserved keywords
    env.filters['CONTENT'] = jinja2_getcontent
    env.filters['DATA'] = jinja2_getitem
    env.filters['MD'] = jinja2_getmetadata
    env.filters['FRAGMENTS'] = jinja2_fragments
    env.filters['MC_PAGENAME'] = jinja2_multicast_pagename
    env.filters['PAGE_URL'] = jinja2_other_lang_URL
    env.filters['TR'] = jinja2_translate
    env.filters['LINK_TARGET'] = jinja2_linktarget
    env.filters['TARGET_PAGE'] = jinja2_targetpage
    env.filters['MARKDOWNIFY'] = jinja2_markdownify
    env.filters['SPLIT'] = jinja2_split
    env.filters['basename'] = jinja2_filepath_basename
    env.filters['ext'] = jinja2_filepath_ext
    templ = env.get_template("")
    try:
        result = templ.render()  # tmpl.render(metadata)
    except jinja2.exceptions.TemplateNotFound:
        # TEST CODE to be removed...
        print(os.getcwd())
        print(os.path.abspath(os.getcwd()))
        assert False
    return result


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
    keys = [table[row][0] for row in range(1, len(table)) if table[row]]
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


def gen_chainloader(loader_list):
    """Returns a loader function that applies a list of loaders sequentially.

    Args:
        loader_list: A list of functions (data, metadata) -> data
    """
    chain = tuple(loader_list)

    def chainloader(text, metadata):
        for loader in chain:
            text = loader(text, metadata)
        return text

    if is_completing_loader(chain[-1]):
        return completing_loader(chainloader)
    else:
        return chainloader


def passthru_loader(data, metadata):
    """A loader that leaves the data unchanged."""
    return data


class UnknownExtensionException(Exception):
    pass


def get_loader(filename, loaders):
    """Returns an appropriate loader for the file's extension(s).

    In case the filename has several extensions (e.g. "md.jinja2") a
    chain-loader is constructed.
    Parameters:
        filename(str): the name of the file for which a loader is chosen
        loaders(dict): a mapping from extensions (e.g. ".yaml") to loaders
    Returns:
        an appropriate loader function. (If no loader was found
        'passthru_loader' is returned.)
    Raises:
        UnknownExtensionException in case of an unknown exception.
    """
    chain = []  # reset chain variable
    basename, ext = os.path.splitext(filename)
    while ext:
        if ext in loaders:
            chain.append(loaders[ext])
            basename, ext = os.path.splitext(basename)
        else:
            msg = "No loader for extension '%s' of file '%s'" % (ext, filename)
            # raise UnknownExtensionException(msg)
            print(msg)  # for debugging for the time being
            ext = ""
    # helpful for debugging not to let the first to cases be dealt with by
    # the chainloader, although it would be possible
    if len(chain) == 0:
        return passthru_loader
    if len(chain) == 1:
        return chain[0]
    else:
        return gen_chainloader(chain)


##############################################################################
#
# high level generic loading function for (compound) files
#
##############################################################################


STOCK_LOADERS = {".bib": bibtex_loader,
                 ".csv": csv_loader,
                 ".html": jinja2_loader,
                 ".jinja2": jinja2_loader,
                 ".json": json_loader,
                 ".md": markdown_loader,
                 ".ttbl": load_transtable,
                 ".yaml": yaml_loader}


def peep_lang(filename, md_loader=yaml_loader, delimiter="+++"):
    """Return true, if metadata field 'language' is defined somewhere within
    the file. Returns always False if 'filename' refers to a directory.
    """
    if filename.find(".ttbl.") >= 0 or filename.endswith(".ttbl"):
        return True

    def read_md_block(f):
        block = []
        line = f.readline()
        while line and line.rstrip() != delimiter:
            block.append(line)
            line = f.readline()
        return "".join(block)

    if os.path.isdir(filename):
        return False
    with open(filename, "r") as f:
        line = f.readline()
        while line:
            if line.rstrip() == delimiter:
                md_block = read_md_block(f)
                data = md_loader(md_block, {})
                if 'language' in data:
                    return True
            line = f.readline()
    return False


def fullpath(path, root):
    """Returns the path starting from path root. Raises an error if root is
    not the beginning of the absolute path of the path."""
    abspath = os.path.abspath(path)
    if abspath.startswith(root[:-1] if root.endswith(os.pathsep) else root):
        return abspath[len(root) + 1:]
    else:
        raise ValueError(("Mismatch between supposed root:\n%s\nand " +
                          "absolute path:\n%s") % (root, abspath))


class MalformedFile(Exception):
    END_MARKER_MISSING = "No end marker for last header"
    LANGUAGE_INFO_MISSING = "Language info missing"
    MULTIPLE_BLOCKS_OF_SAME_LANGUAGE = "Multiple blocks of same language"


def _gen_entry(filepath, metadata_headers, data_chunks,
               data_loader, metadata_loader, injected_metadata):
    """Generates an entry for the site tree from an already split page
    (see function load()).
    """
    entry = sitetree.Entry()
    common_metadata = {}
    common_data = ""
    index = -1
    for raw_metadata, raw_data in zip(metadata_headers, data_chunks):
        index += 1
        chunk_metadata = metadata_loader(raw_metadata)
        metadata = injected_metadata.copy()
        metadata.update(common_metadata)
        metadata.update(chunk_metadata)
        if 'language' not in chunk_metadata:
            # Only one common chunk is allowed and this must be located
            # at the very beginning of the file
            if index == 0:
                common_metadata = metadata
                common_data = raw_data
            else:
                raise MalformedFile(MalformedFile.LANGUAGE_INFO_MISSING +
                                    "\nheader data:\n" + raw_metadata)
        else:
            variant = {
                'metadata': metadata,
                'content': data_loader(common_data + raw_data, metadata)
            }
            if metadata['language'] in entry:
                raise MalformedFile(
                    MalformedFile.MULTIPLE_BLOCKS_OF_SAME_LANGUAGE +
                    "\nheader data:\n" + raw_metadata)
            entry[metadata['language']] = variant
    if not entry:
        # the whole file contains only one language version and no 'language'
        # in its metadata (or no metadata at all). Therefore the language
        # will be inferred from the filename or directory name or set to 'ANY'
        site_path = injected_metadata.get('config', {}).get('site_path', '')
        metadata = injected_metadata.copy()
        metadata.update(common_metadata)
        lang = metadata.setdefault("language", locale_strings.extract_locale(
            fullpath(filepath, site_path)))
        if not lang:
            raise MalformedFile(MalformedFile.LANGUAGE_INFO_MISSING)
        entry[lang] = {'metadata': metadata,
                       'content': data_loader(common_data, common_metadata)}
    return entry


def _multicast_groups(subpages, metadata):
    """Order the subpages of a multicast page into groups according
    to hints given in the metadata.
    Arguments:
        subpages(list): list of subpages of the multicast page
        metadata(dict): the metadata dictionary of the multicast 
            page. The only control parameters so far is: 
            'items_per_page'
    Returns:
        a list of lists where each list represents one group of
        subpages that is to appear on one output page.
    """
    n = metadata.get('items_per_page', 1)
    return [subpages[k:k + n] for k in range(0, len(subpages), n)]


def _multicast_pagenames(basename, groups, metadata):
    """Returns an association of subpages (more precisely subpage
    paths) to (suggested) output page names.
    Arguments:
        basename(string): the name of the multicast page
        groups(list): a list of groups of subpages
        metadata(dict): the metadata dict of the multicast page
    """
    # the first output page always has the name of the multicast page
    page_names = {groups[0][0]: basename}
    if all(len(group) == 1 for group in groups):
        # use output pagename as suffix for single page groups
        for group in groups[1:]:
            page_names[group[0]] = basename + "_" + group[0].split("/")[-1]
    else:
        # generate a page number as suffix otherwise
        # fill up page numbers with zeros from the left
        fmtstr = "_%0{0}i".format(int(math.log10(len(groups))) + 1)
        for i, group in enumerate(groups[1:], 2):
            for subpage in group:
                page_names[subpage] = basename + fmtstr % i
    return page_names


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
    language code can - instead of putting it in the metadata - also be added
    to the file name between the basename and the file extension with an 
    underscore as delimiter, e.g "index_DE.html".

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
        A dictionary that associates page names to dictionaries that
        that map language keys to the corresponding metadata and data.
        Example:
        {'greeting' : 
         {'DE': {'metadata': {...}, 'content': '<p>Guten Morgen!</p>'},
          'EN': ... }
        }
    """
    assert not is_completing_loader(metadata_loader)

    metadata_headers = []
    data_chunks = []
    with open(filepath, "r") as f:
        if is_completing_loader(data_loader):
            return collections.OrderedDict([(
                injected_metadata['basename'],
                data_loader(f.read(), injected_metadata))])
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

    metadata = injected_metadata.copy()
    metadata.update(metadata_loader(metadata_headers[0]))
    if "MULTICAST" in metadata:
        basename = metadata['basename']
        foldername = metadata['MULTICAST']
        folder = metadata['local'][foldername]
        order = metadata.get('orderby') or \
            metadata['local'][foldername].get('orderby')
        subpages = collect_fragments(folder, foldername, order)
        groups = _multicast_groups(subpages, metadata)
        page_names = _multicast_pagenames(basename, groups, metadata)
        metadata['MC_ALL'] = subpages
        metadata['MC_PAGES'] = len(groups)
        metadata['MC_PAGENAMES'] = page_names
        output_pages = collections.OrderedDict()
        for group in groups:
            metadata['MC_CURRENT_BATCH'] = group
            metadata['basename'] = page_names[group[0]]
            output_pages[page_names[group[0]]] = _gen_entry(
                filepath, metadata_headers, data_chunks,
                data_loader, metadata_loader, metadata)
        return output_pages
    else:
        return collections.OrderedDict([
            (injected_metadata['basename'],
             _gen_entry(filepath, metadata_headers, data_chunks,
                        data_loader, metadata_loader, injected_metadata))])


def load_plain(filename, loaders, injected_metadata={}):
    """Loads a plain file, i.e. a file that does not consist of several
    different language chunks.
    """
    ldr = get_loader(filename, loaders)
    with open(filename) as f:
        text = f.read()
    return ldr(text, injected_metadata)
