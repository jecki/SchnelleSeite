#!/usr/bin/python3

"""SchnelleSeite - A static site generator for multilingual websites 

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
import shutil
import sys
import webbrowser

import yaml

import generator
import loader
helptxt = """SchnelleSeite - A static site generator.

Usage:
    python3 SchnelleSeite.py --init [directory]
            Create a new project in 'directory' or in the current directory

    python3 SchnelleSeite.py [directory]
            Compile the project, i.e. generate the static site from the
            sources in 'directory' or in the current directory.
            The result will be placed in the sub-directory '__site' of this
            directory.
"""

# alternative: os.path.dirname(os.path.abspath(__file__))
SCRIPT_PATH = os.path.dirname(os.path.abspath(sys.argv[0]))


def new_project(path):
    shutil.copytree(os.path.join(SCRIPT_PATH, "templates/default"), path)


def make_project(path):

    SITE_PATH = path

    config = {
        "template_paths": [os.path.join(SCRIPT_PATH, "macros")],
        "static_entries": ['robots.txt'],
        "site_path": SITE_PATH,
        "build_path": "__site",
        "generator_path": SCRIPT_PATH,
        "generator_resources": {},
    }

    config['generator_resources']['_data'] = generator.scan_directory(
        os.path.join(SCRIPT_PATH, "_data"), loader.STOCK_LOADERS,
        {'language': 'ANY'})

    # read config file
    with open(os.path.join(SITE_PATH, "__site-config.yaml")) as cfg_file:
        cfg = yaml.load(cfg_file)
    if 'template_paths' in cfg:
        cfg['template_paths'].extend(config['template_paths'])
        config['template_paths'] = cfg['template_paths']
        del cfg['template_paths']
    if 'static_entries' in cfg:
        config['static_entries'] = list(set(config['static_entries']) |
                                        set(cfg['static_entries']))
        del cfg['static_entries']
    overlap = set(config.keys()) & set(cfg.keys())
    if overlap:
        raise ValueError("Illegal keys in '__site-config': {0!s}".
                         format(overlap))
    config.update(cfg)
    if 'languages' not in config:
        config['languages'] = ['EN']

    generator.generate_site(SITE_PATH, {'config': config})


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--init":
        path = sys.argv[2] if len(sys.argv) > 2 else "./"
        new_project(path)
    elif len(sys.argv) > 1 and sys.argv[1] == "--help":
        print(helptxt)
    else:
        path = os.path.abspath(
            sys.argv[1] if len(sys.argv) > 1 else os.getcwd())
        make_project(path)
        fullpath = os.path.join(path, "__site/EN/index.html")
        print("showing " + fullpath)
        webbrowser.open(fullpath)
