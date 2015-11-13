"""permalinks.py -- postprocessor to add permalinks to headings

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

from sitetree import translate
from utility import segment_data, matching_segment_range, RX_HTML_COMMENTS, \
    set_attributes, get_attributes


RX_PERMALINK_CLASS = re.compile('class *?= *?["\']permalink["\']',
                                re.IGNORECASE)
RX_TAG = re.compile("<.*?>", re.DOTALL)
RX_ENTITIES = re.compile("&.*?;", re.DOTALL)
VISIBLE_PERMALINK = '&nbsp;&nbsp;<a class="visible_permalink" ' \
        'href="#{target}" title="{tooltip}">{sign}</a>'
SILENT_PERMALINK = '<a class="silent_permalink" href="#{target}" ' \
        'title="{tooltip}">'


def visible_permalink(heading, target, metadata):
    """Adds a visible link at the end of heading to target.  The
    (perma-)link is marked by metadata["permalink_sign"] (fallback: &infin;)
    which appears at the end of the heading separated by two spaces.
    Depending on the stylsheet it can be made to appear only when hovering
    over the heading. CSS class 'visible_permalink'.

    Args:
        heading (string): The heading as HTML snippet, e.g. "<h1>Heading</h1>"
        target (string): The targent of the permalink. Usually this is the
             same as the id-attribute of the heading.
        metadata (dictionary): The metadata of the current page. If the key
             "permalink_sign" is present, then it's value is taken as the
             permalink marker, otherwise "&infin;" serves as the default.
    
    Returns:
        string. The heading as HTML snippet with the (perma-)link added.
    """
    tp = translate("permalink", metadata)
    pmsign = metadata.get("permalink_sign", "&infin;")
    pos = heading.rfind("<")
    link = VISIBLE_PERMALINK.format(target=target,
                                    tooltip=tp, sign=pmsign)
    return heading[:pos] + link + heading[pos:]


def silent_permalink(heading, target, metadata):
    """Puts a 'silent permalink' under a head, i.e. a link that covers the
    complete heading, but does not have a particular sign.

    Args:
        heading (string): The heading as HTML snippet, e.g. "<h1>Heading</h1>"
        target (string): The targent of the permalink. Usually this is the
             same as the id-attribute of the heading.
        metadata (dictionary): The metadata of the current page. 
    
    Returns:
        string. The heading as HTML snippet with the (perma-)link added.    
    """
    tp = translate("permalink", metadata)
    start = heading.find(">") + 1
    end = heading.rfind("<")
    # special case treatment in case the heading alread contains some a tags
    atag = heading.find("<a")
    if atag > start:
        end = atag
    else:
        atag = heading.find("</a>") + 4
        assert atag < end, "no room for silent permalink here:" + heading
        
    link = SILENT_PERMALINK.format(target=target, tooltip=tp)
    return heading[:start] + link + heading[start:end] + '</a>' + heading[end:]


def permalinks(html, args, metadata):
    """Add permalinks to the headings specified by 'args' in 'html'.

    Args:
        html (string): The web page to which permalinks shall be added.
        args (string): Range of headings to which the permalinks shall be
            added, e.g. "H1-H3" or "H1, H3-H5"
        metadata(dictionary): The metadata dictionary for the current page.
            the keys 'permalink_type' and 'permalink_sign' will be
            interpreted if present. 'permalink_type' must be the name
            of a function (heading, target, metadata) -> heading with permalink

    Returns:
        string. The same web page with permalinks added.
    """

    def parse_args(args):
        # TODO: Check for correct syntax with regular expression
        headings = set()
        parts = args.split(",")
        for part in parts:
            rng = part.split("-")
            a = int(rng[0][1])
            if len(rng) > 1:
                b = int(rng[1][1])
                if a > b:
                    a, b = b, a
                headings |= set(range(a, b + 1))
            else:
                headings.add(a)
        return headings

    def permalink_exists(heading):
        if RX_PERMALINK_CLASS.search(heading):
            print("Warning, permanent link already exists in: " + heading)
            return True
        if heading[-9:-5].lower() == "</a>" and \
                "id" in get_attributes(heading, 0):
            print("Remark, maybe %s already has a permalink?" % heading)
        return False

    def gen_id(heading):
        start = heading.find(">") + 1
        end = heading.rfind("<")
        text = RX_ENTITIES.sub("", RX_TAG.sub("", heading[start:end]))
        return re.sub(r"\W", " ", text).strip().replace(" ", "-")

    headings = parse_args(args)
    hstr = "".join([str(h) for h in headings])
    rx_htags = re.compile("<h[%s].*?>.*?</h[%s]>" %
                          (hstr, hstr), re.IGNORECASE | re.DOTALL)

    def add_permalinks(segment):
        parts = segment_data(segment, rx_htags)
        for i in matching_segment_range(parts, rx_htags):
            if not permalink_exists(parts[i]):
                attributes = get_attributes(parts[i], 0)
                if "id" not in attributes:
                    attributes['id'] = gen_id(parts[i])
                parts[i] = set_attributes(parts[i], 0, attributes)
                pm_func = eval(metadata.get("permalink_type",
                                            "visible_permalink"))
                parts[i] = pm_func(parts[i], attributes['id'], metadata)
        return "".join(parts)

    segments = segment_data(html, RX_HTML_COMMENTS)
    for i in matching_segment_range(segments, RX_HTML_COMMENTS, invert=True):
        segments[i] = add_permalinks(segments[i])
    return "".join(segments)
