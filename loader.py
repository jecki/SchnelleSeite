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
import inspect
import io
import json
import os
import sys

import markdown
import yaml

from bibloader import bibtex_loader
from jinja2_loader import jinja2_loader
import locale_strings
from permalinks import permalinks
import sitetree


__update__ = "2015-03-07"


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


def python_loader(text, metadata):
    """A loader for python code.
    """
    cwd = os.getcwd()
    if cwd not in sys.path:
        sys.path.append(cwd)
    exec("import " + metadata['basename'])


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
# Postprocessors
#
##############################################################################


POSTPROCESSORS = {"PERMALINKS": permalinks}


def gather_postprocessors(metadata):
    """Scans the 'metadata' for postprocessing directives and returns
    a postprocessing function that calls these postprocessors in
    arbitrary (!) order on the content data.

    Args:
        metadata (dictionary): Metadata dictionary. Postprocessing
            directives are uppercase and are either built into SchnelleSeite
            or must have been registered.

    Returns:
        function: Takes a chunk of content (string) as argument and returns
            the transformed chunk of content (string)

    The functions that are registered for specific postprocessing directives
    take three arguments, a content chunk (string), the metadata value which
    represents its arguments and the metadata dictionary.

    Example: If the metadata contains the directive `PERMALINKS: H1-H3` then
    this generates the postprocessor call `permalinks(data, "H1-H3", metadata)`
    """
    post_processors = POSTPROCESSORS.copy()
    post_processor_list = [key[len("POSTPROCESSOR_"):] for key in metadata
                           if key.startswith("POSTPROCESSOR")]
    for key in post_processor_list:
        value = metadata['POSTPROCESSOR_' + key]
        if inspect.isfunction(value):
            post_processors[key] = value
        else:
            module = value.split('.')[0]
            exec("import " + module + "; post_processors[key] = " + value)
            metadata['POSTPROCESSOR_' + key] = post_processors[key]
    post_processor_list += [key for key in POSTPROCESSORS if key in metadata]

    def postprocessor(data):
        for key in post_processor_list:
            data = post_processors[key](data, metadata.get(key, ""), metadata)
        return data
    return postprocessor


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
                 ".yaml": yaml_loader,
                 ".py": python_loader}


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

    def add_metadata_from_subpages(metadata, lang):
        """Adds additional metadata from subpages to the 'metadata' dict
        and returns the enriched dict. The precedence rule is existing (i.e.
        main page) metata over subpage metadata and metadata from earlier
        subpages over metadata from later subpages.
        """
        group = metadata.get("MC_CURRENT_BATCH", [])
        for path in group:
            entry = sitetree.getentry(metadata['local'], path, lang)
            for key, value in entry['metadata'].items():
                if key not in metadata:
                    metadata[key] = value
        return metadata

    def postprocess(common_data, raw_data, metadata):
        if metadata['basename'].startswith("_"):
            return data_loader(common_data + raw_data, metadata)
        else:
            pp = gather_postprocessors(metadata)
            return pp(data_loader(common_data + raw_data, metadata))

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
                'metadata': add_metadata_from_subpages(metadata,
                                                       metadata['language']),
                'content': postprocess(common_data, raw_data, metadata)
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
        entry[lang] = {'metadata': add_metadata_from_subpages(metadata, lang),
                       'content': postprocess(common_data, "", metadata)}
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
    n = metadata.get('MC_PAGINATION', 1)
    if n < 1000:
        # interpret pagination parameter as number of items per page
        return [subpages[k:k + n] for k in range(0, len(subpages), n)]
    else:
        # interpret pagination parameter as size, i.e. number of characters
        # per page
        groups = []
        group = []
        cnt = 0
        for sp in subpages:
            size = len(sp)
            if len(group) == 0 or size + cnt <= n:
                group.append(sp)
                cnt += size
            else:
                groups.append(group)
                group = [sp]
                cnt = size
        return groups


def _multicast_pagenames(basename, groups, metadata):
    """Returns an association of subpages (more precisely subpage
    paths) to (suggested) output page names.
    Arguments:
        basename(string): the name of the multicast page
        groups(list): a list of groups of subpages
        metadata(dict): the metadata dict of the multicast page
    """
    def gen_page_name(group):
        return basename + "_" + group[0].split("/")[-1]

    # the first output page always has the name of the multicast page
    page_names = {groups[0][0]: basename}
    if all(len(group) == 1 for group in groups):
        # use output pagename as suffix for single page groups
        for group in groups[1:]:
            page_names[group[0]] = gen_page_name(group)
    else:
        # generate a page number as suffix otherwise
        # fill up page numbers with zeros from the left
        # fmtstr = "_%0{0}i".format(int(math.log10(len(groups))) + 1)
        # for i, group in enumerate(groups[1:], 2):
        #     for subpage in group:
        #         page_names[subpage] = basename + fmtstr % i
        for group in groups[1:]:
            for fragment in group:
                page_names[fragment] = gen_page_name(group)
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
        subpages = sitetree.collect_fragments(folder, foldername, order)
        groups = _multicast_groups(subpages, metadata)
        page_names = _multicast_pagenames(basename, groups, metadata)
        metadata['MC_ALL'] = subpages
        metadata['MC_PAGES'] = len(groups)
        metadata['MC_PAGENAMES'] = page_names
        output_pages = collections.OrderedDict()
        for pagenr, group in enumerate(groups, 1):
            metadata['MC_CURRENT_BATCH'] = group
            metadata['MC_CURRENT_PAGE'] = pagenr
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
