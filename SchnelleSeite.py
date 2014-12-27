#!/usr/bin/python3

import os
import sys

import loader
import sitetree
# alt: os.path.dirname(os.path.abspath(__file__))
SCRIPT_PATH = os.path.dirname(os.path.abspath(sys.argv[0]))
SITE_PATH = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()


config = {
    "template_paths": [os.path.join(SCRIPT_PATH, "templates")],
    "site_path": SITE_PATH,
    "build_path": "__site",
    "generator_path": SCRIPT_PATH
}

generator = sitetree.Folder()
generator['_data'] = loader.scan_directory(os.path.join(SCRIPT_PATH, "_data"),
                                           loader.STOCK_LOADERS, {})

if __name__ == "__main__":
    os.chdir("../newsite")
    config['site_path'] = os.path.dirname(os.path.abspath(os.getcwd()))
    os.chdir("_philosophy")
    loader.test_scan_directory({'config': config, 'generator': generator})
