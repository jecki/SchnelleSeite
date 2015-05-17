"""mako_loader.py -- loader for jinja2 templates

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


from mako.template import Template
from mako.lookup import TemplateLookup


# TODO: This is a stub!

def mako_loader(text, metadata):
    """A loader for mako templates.
    """
    templ_paths = ""
    if "config" in metadata and "template_paths" in metadata["config"]:
        templ_paths = metadata["config"]["template_paths"]
    lookup_obj = TemplateLookup(directories=templ_paths)
    return Template(text, lookup=lookup_obj).render_unicode(**metadata)
