"""jinja2_loader.py -- loader for jinja2 templates

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
import time

import jinja2
import markdown

import sitetree
from utility import translate, collect_fragments


##############################################################################
#
# jinja2 environment filters
#
##############################################################################

def jinja2_current_date():
    """Returns the current date as YYYY-MM-DD."""
    return time.strftime('%Y-%m-%d')


@jinja2.environmentfilter
def jinja2_translate(env, expression):
    """Translates expression within the given jinja2 environment.

    This requires that the variables 'local', 'language' and 'root' are
    defined in the jinja2 environment.
    """
    return translate(expression, env.globals)


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


##############################################################################
#
# jinja2 loader
#
##############################################################################


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
    env.globals['current_date'] = jinja2_current_date
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
