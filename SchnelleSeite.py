#!/usr/bin/python3

import os
import sys

import loader

# alt: os.path.dirname(os.path.abspath(__file__))
SCRIPT_PATH = os.path.dirname(os.path.abspath(sys.argv[0]))
SITE_PATH = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()


config = {
    "template_path": os.path.join(SCRIPT_PATH, "templates"),
    "site_path": SITE_PATH,
    "build_path": "__site",
    "generator_path": SCRIPT_PATH
}

site = loader.scan_directory(os.path.join(SCRIPT_PATH, "data"),
                             {".yaml": loader.yaml_loader}, {})

if __name__ == "__main__":
    os.chdir("../newsite")
    config['site_path'] = os.path.dirname(os.path.abspath(os.getcwd()))
    os.chdir("_philosophy")
    loader.test_scan_directory({'config': config, 'site': site})
