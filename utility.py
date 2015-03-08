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

import re
import sitetree


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


RX_HTML_COMMENTS = re.compile("<!--.*?-->")


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
        (list, list). A tuple of a list of segments and a list of those indices
            that match 'regexp'

    Example:
        >>> segment_data("Text <h1>HEADING</h1> More Text", "<h1>.*?</h1>")
        (["Text ", "<h1>HEADING</h1>", " More Text" ], [2])
    """
    if isinstance(regexp, str):
        regexp = re.compile(regexp)
    segments = []
    indices = []
    pos = 0
    for match in regexp.finditer(data):
        start = match.start()
        end = match.end()
        if start > pos:
            segments.append(data[pos:start])
        indices.append(len(segments))
        segments.append(data[start:end])
        pos = end
    if pos < len(data):
        segments.append(data[pos:])
    return (segments, indices)
