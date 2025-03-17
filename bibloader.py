#!/usr/bin/python3

"""bibloader.py - A loader for bibtex bibliography databases


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

# TODO: Add COINS support!

import re
from utility import deep_update


__update__ = "2016-01-09"


def strip_texcmds(tex):
    """Removes all tex or latex commands from a text-string.
    QUICK HACK: DO NOT RELY ON THIS! (MIGHT DELETE TOO MUCH in SOME CASES)
    """
    return re.sub(r"\\\\\S+\s|\\\\\S", "", tex.replace("\\&", "&"))


def end_of_block(text, pos):
    """Return the position of the closing '}' starting from pos
    """
    assert text[pos] == '{'
    cnt = 1;  i = pos
    while cnt > 0:
        k = text.find('{', i + 1)
        i = text.find('}', i + 1)
        if k >= 0 and k < i:
            cnt += 1
            i = k
        else:
            cnt -= 1
    return i


class ParserError(Exception):

    """An error that occurred during Parsing."""


class BibTeXParser(object):

    """Parser for a bibtex file that stores the content of the file
    as a nested dictionary indexed by the entry names on the first level.

    Attributes:
        text(str): the bibtext file as text string
        pos(int): the current position in the text string during parsing
    """

    def __init__(self, text):
        self.text = text
        self.pos = 0

    def assert_cond(self, cond, errstr):
        """Raises a ParserError if 'cond' is false, outputting the
        line number and the 'errstr'."""
        if not cond:
            lineNr = self.text.count("\n", 0, self.pos) + 1
            raise ParserError(("Error in line %i: " % lineNr) + errstr)

    def assert_token(self, token):
        """Checks if 'token' follows at the current position in the text.
        Raises a ParseError exception in case it does not."""
        cond = self.text[self.pos:self.pos + len(token)] == token
        self.assert_cond(cond, "'%s' expected" % token)

    def consume_blanks(self):
        """Advance current position to the next position that is neither
        a blank or a newline or a carriage return character or that
        is not part of a commentary (i.e. characters following a '%'
        until the end of line."""
        N = len(self.text)
        while True:
            while self.pos < N and self.text[self.pos] in " \n\r":
                self.pos += 1
            if self.pos < N and self.text[self.pos] == "%":
                i = self.text.find("\n", self.pos)
                if i >= 0:
                    self.pos = i + 1
                else:
                    self.pos = N
            else:
                break

    def parse_value(self):
        """Parses and returns the value of a field in a bibtex-entry."""
        self.assert_token("{")
        i = end_of_block(self.text, self.pos)
        self.assert_cond(i >= 0, "'}' expected after %s..." %
                         self.text[self.pos:self.pos + 6])
        value = strip_texcmds(self.text[self.pos + 1:i])
        self.pos = i + 1
        return value

    def parse_field(self):
        """Parses one field in a bibtex-entry and returns a dictionary of the
        field name and value."""
        i = self.text.find("=", self.pos)
        k = self.text.find('}', self.pos)
        if k >= 0 and k < i:
            return {}
        self.assert_cond(i >= 0, "'=' expected after field name: " + self.text[self.pos:])
        field_name = self.text[self.pos:i].strip().lower()
        # if field_name == 'journal':
        #     field_name == 'journal_title'
        self.pos = i + 1
        self.consume_blanks()
        value = self.parse_value()
        # if field_name.upper() == "URL":
        #     value = value.replace("\\-", "")
        return {field_name: value}

    def parse_all_fields(self):
        """Parses and returns as dictionary all fields of a bibtex-entry."""
        fields = {}
        while self.text[self.pos] == ",":
            self.pos += 1
            fields.update(self.parse_field())
            self.consume_blanks()
        self.assert_token("}")
        self.pos += 1
        return fields

    def parse_entry(self):
        """Parses one entry of the bibtex data and returns it as a dictionary
        with entry name as key and a dictionary of all fields plus one special
        field 'type' that contains the entry type (e.g. "InCollection")
        as value."""
        self.assert_token("@")
        i = self.text.find("{", self.pos)
        self.assert_cond(i >= 0, "'{' expected after entry type")
        entry_type = self.text[self.pos + 1:i]
        if entry_type.lower() == 'comment':
            self.pos = end_of_block(self.text, i) + 1
            return {}
        self.pos = i + 1
        i = self.text.find(",", self.pos)
        self.assert_cond(i >= 0, "',' expected after entry name")
        entry_name = self.text[self.pos:i].strip().lower()
        self.pos = i
        fields = self.parse_all_fields()
        fields["type"] = entry_type
        return {entry_name: fields}

    def parse_bibtex(self):
        """Parses a complete bibtex database and returns it as nested
        dictionary with entry names as keys on the first level.
        """
        assert self.pos == 0, "BibTeXParser.parse_bibtex() must be called " +\
                              "only once!"
        bib = {}
        self.consume_blanks()
        while self.pos < len(self.text):
            bib.update(self.parse_entry())
            self.consume_blanks()
        return bib


trans_table = {}
trans_table["EN"] = {
    "Ed": "Ed.",
    "Eds": "Eds.",
    "ed_by": "ed. by",
    "in": "in:",
    "preprint": "preprint",
    "and": "and"
}
trans_table["DE"] = {
    "Ed": "Hrsg.",
    "Eds": "Hrsg.",
    "ed_by": "hrsg. von",
    "in": "in:",
    "preprint": "Vordruck",
    "and": "und"
}


def author(entry, lang):
    """Returns the author's or the editor's name in a form suitable for
    `(author year)` quotation, e.g. `Bill Clinton and Barack Obama` will become
    `Clinton and Obama`. if there are more than three names only the
    first name will be picked and ` et al.` will be appended.
    """
    def familiy_name(name):
        if name.find(',') >= 0:
            return name.split(',')[0].strip()
        else:
            return name.split(' ')[-1].strip()
        
    name_field =  entry['author'] if 'author' in entry else entry['editor']
    names = name_field.split(' and ')
    name = family_name(names[0])
    if len(names) > 2:
        name += ' et al. '
    elif len(names) == 2:
        name += ' ' + trans_table[lang]['and'] + ' ' + family_name(names[1])
    return name


def bib_strings(entry, lang):
    """Returns a dictionary with different (short and long) string
    representations of the entry.
    """
    def eds(entry):
        """Return "{Eds.}" or "{Ed.}" depending on the whether there are several
        or just one editor in entry.
        """
        if ("Editor" in entry and
            (entry["editor"].find("and") >= 0 or
             entry["editor"].find(",") >= 0)):
            return "{Eds}"
        else:
            return "{Ed}"

    entry_dict = {"address": "", "publisher": ""}
    entry_dict.update(entry)
    entry_dict.update(trans_table[lang])

    # special patch
    if entry_dict.get('pages') == "forthcoming" and lang.upper() == "DE":
        entry_dict['pages'] = "im Erscheinen"

    if entry["type"] == "Book":
        if "author" in entry and "editor" in entry:
            bib_full = "{author}: {title}, {ed_by} {editor}," \
                " {publisher} {address} {year}.".format(**entry_dict)
            bib_short = "{ed_by} {editor}," \
                " {publisher} {address} {year}.".format(**entry_dict)
        elif "Editor" in entry:
            bib_full = ("{editor} (" + eds(entry) + "): {title}" +
                        ", {publisher} {address} {year}.") \
                .format(**entry_dict)
            bib_short = "{publisher} {address} {year}."\
                .format(**entry_dict)
        else:
            bib_full = "{author}: {title}, {publisher} " \
                "{address} {year}.".format(**entry_dict)
            bib_short = "{publisher} {address} {year}." \
                .format(**entry_dict)

    elif entry["type"] in ["InCollection", "InProceedings"]:
        bib_full = ("{author}: {title}, {in} {editor}"
                    "(" + eds(entry) + "): {booktitle}, " +
                    "{publisher} {address} {year}.") \
            .format(**entry_dict)
        bib_short = ("{editor} (" + eds(entry) +
                     "): {booktitle}, {publisher} " +
                     "{address} {year}.").format(**entry_dict)
        if "pages" in entry_dict:
            bib_full = bib_full[:-1] + ", {pages}.".format(**entry_dict)
            bib_short = bib_short[:-1] + ", {pages}.".format(**entry_dict)

    elif entry["type"] == "Article":
        if "number" in entry:
            tmpl = "{journal} {number}/{year}"
        else:
            tmpl = "{journal} {year}"
        if 'pages' in entry_dict:
            tmpl += ', {pages}'
        tmpl_full = ""
        if "doi" in entry:
            tmpl_full += ", DOI: {doi}"
        if "url" in entry and len(entry["url"]) < 80:
            tmpl_full += ', URL: <a href="{url}">{url}</a>'
        tmpl += "."
        bib_full = ("{author}: {title}, {in} " + tmpl + tmpl_full) \
            .format(**entry_dict)
        bib_short = tmpl.format(**entry_dict)

    elif entry["type"] == "Proceedings":
        bib_full = ("{editor} (" + eds(entry) + "): {title}, {publisher} " +
                    "{address} {year}.").format(**entry_dict)
        bib_short = "{publisher} {address} {year}." \
            .format(**entry_dict)

    else:  # fallback option
        if 'author' not in entry_dict:
            entry_dict['author'] = entry_dict['editor']
        bib_full = "{author}: {title}, {publisher} " \
            "{address} {year}.".format(**entry_dict)
        bib_short = "{publisher} {address} {year}." \
            .format(**entry_dict)

    return {"bib_short": {lang: bib_short}, "bib_full": {lang: bib_full}}


def add_bib_strings(bib, bibentry_to_strs):
    """Adds several useful string representations to each entry in the
    bib dictionary.

    The following strings are added:
    "bib_short": A short string representation, leaving out the author's name
                 and the title.
    "bib_full": A long string representation contianing all bibliographic
                data

    Arguments:
        bib(dictionary): The bibliography dictionary as produced by the
            BibTexParser
        bibentry_to_strs(function): A function that receives a bibtex entry
            and a language string (e.g. "DE") and returns a tuple that
            contains a short and long string representation of that entry.
    """
    for entry in bib.values():
        for lang in trans_table.keys():
            deep_update(entry, bibentry_to_strs(entry, lang))


# bibtex entries that should not be exported to metadata
BLACK_LIST = {"timestamp", "bib_short", "bib_full", "owner",
              "__markedentry", "quality"}


def citation_metadata(entry, entryname=""):
    """Converts a bibtex entry in a very rough way to highwire citation
    metadata.
    """
    replace_list = {"journal": "journal_title", "number": "issue"}
    md = []
    if entryname:
        md.append('<meta name="citation_bibtexkey" content="%s"/>' %
                  entryname)
    for key in entry:
        key_lower = key.lower()
        if key_lower == "pages":
            page_range = entry[key].split("-")
            if page_range[0].isnumeric():
                md.append('<meta name="citation_firstpage" content="%s" />' %
                          page_range[0])
                md.append('<meta name="citation_lastpage" content="%s" />' %
                          page_range[-1])
        elif key_lower in ["author", "editor"]:
            names = entry[key].split(" and ")
            for name in names:
                md.append('<meta name="citation_%s" content="%s" />' %
                          (key_lower, name))
        elif key_lower in ["url"]:
            url = entry[key].replace(r"\-", "").replace(r"\_", "")
            if url.endswith(".pdf"):
                key_name = "pdf_url"
            elif url.endswith(".html"):
                key_name = "full_html_url"
                md.append('<meta name="citation_abstract_html_url"' +
                          ' content="%s" />' % url)
                md.append('<meta name="citation_public_url" content="%s" />' %
                          url)
            else:
                key_name = "public_url"
            md.append('<meta name="citation_%s" content="%s" />' %
                      (key_name, url))
        elif key_lower not in BLACK_LIST:
            md.append('<meta name="citation_%s" content="%s" />' %
                      (replace_list.get(key_lower, key_lower),
                       entry[key].replace('"', "'")))
    md.append("\n")
    md_str = "\n".join(md)
    return md_str


def XMP_metadata(entry, entryname=""):
    """Returns a bibtex entry as XMP metadata.
    """

    xmp = ['<?xpacket begin="r" id="%s"?>' % (entryname or entry['Title']),
           '<x:xmpmeta xmlns:x="adobe:ns:meta/">',
           '<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">']

    xmp.append('<rdf:Description xmlns:bibtex="'
               'http://jabref.sourceforge.net/bibteXMP/"')  # + '>')
    if entryname:
        xmp.append('    bibtex:bibtexkey="' + entryname + '" ')
        # xmp.append('    <bibtex:bibtexkey>' + entryname +
        #            '</bibtex:bibtexkey>')
    for key in entry:
        kl = key.lower()
        if kl not in BLACK_LIST and kl not in ["author", "editor"]:
            xmp.append('    bibtex:' + kl + '="' + entry[key] + '"')
            # xmp.append('    <bibtex:' + kl + '> ' + entry[key] +
            #            ' </bibtex:' + kl + '>')
    xmp[-1] += '>'

    for key in entry:
        kl = key.lower()
        if kl in ["author", "editor"]:
            names = entry[key].split(" and ")
            if len(names) > 1:
                xmp.append(' ' * 8 + '<bibtex:' + kl + '>')
                xmp.append(' ' * 12 + '<rdf:Seq>')
                for name in names:
                    xmp.append(' ' * 16 + '<rdf:li> ' + name + ' </rdf:li>')
                xmp.append(' ' * 12 + '</rdf:Seq>')
                xmp.append(' ' * 8 + '</bibtex:' + kl + '>')
            else:
                xmp.append(' ' * 8 + '<bibtex:' + kl + '> ' + entry[key] +
                           ' </bibtex:' + kl + '>')
    xmp.append('</rdf:Description>')

    xmp.extend(['</rdf:RDF>', '</x:xmpmeta>', '<?xpacket end="r"?>'])
    return "\n".join(xmp)


# Taugt wegen der geschweiften Klammern in der folgenden Form
# noch nicht für str.format() !!!
TEMPLATE_SCHEMA_ARTICLE = """<script type="application/ld+json">
    {
      "@context": "http://schema.org",
      "@graph": [
        {
            "@id": "#issue",
            "@type": "PublicationIssue",
            "issueNumber": "{Number}",
            "datePublished": "{year}",
            "isPartOf": {
                "@id": "#periodical",
                "@type": [
                    "PublicationVolume",
                    "Periodical"
                ],
                "name": "Cataloging & Classification Quarterly",
                "issn": [
                    "{Issn}"
                ],
                "volumeNumber": "{Volume}",
                "publisher": "{Publisher}"
            }
        },
        {
            "@type": "ScholarlyArticle",
            "isPartOf": "#issue",
            "description": "{Abstract}",
            "sameAs": "http://dx.doi.org/{Doi}",
            "about": [
                "Works",
                "Catalog"
            ],
            "pageStart": {PageStart},
            "pageEnd": "{PageEnd}",
            "name": "{Title}",
            "author": "{Author}"
        }
      ]
    }
    </script>
"""


def schema_org_metadata(entry):
    # TODO: Add schema.org metadata generation for bibtex entries
    pass


def bibtex_loader(data, metadata, bibentry_to_strs=bib_strings):
    """Scans the bibtex-data contained in string text and returns it as
    nested dictionary indexed by the entry names on the first level.
    """
    parser = BibTeXParser(data)
    bib = parser.parse_bibtex()
    add_bib_strings(bib, bibentry_to_strs)
    return bib


def print_bibfile(bibfile):
    """Prints the entries of a bibfile as strings on the console.
    """
    with open(bibfile, "r") as in_file:
        bibdata = in_file.read()
    bibliography = bibtex_loader(bibdata, {})
    for entry in bibliography.values():
        print(entry["bib_full"])

if __name__ == "__main__":
    with open("tmp/_bibdata_ANY.bib", "r") as in_file:
        bibdata = in_file.read()
    bib = bibtex_loader(bibdata, {})
    for key in bib:
        print(citation_metadata(bib[key], key))
        # print(bib[key]["bib_full"]["DE"])
        print(bib[key]["bib_full"]["EN"])
        print(XMP_metadata(bib[key], key))
