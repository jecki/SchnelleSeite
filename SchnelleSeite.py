#!/usr/bin/python3

import os
import sys

import generator
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

root = sitetree.Folder()
root['_data'] = generator.scan_directory(os.path.join(SCRIPT_PATH, "_data"),
                                         loader.STOCK_LOADERS, {})

if __name__ == "__main__":
    os.chdir("../newsite")
    config['site_path'] = os.path.dirname(os.path.abspath(os.getcwd()))
    os.chdir("_philosophy")
    generator.test_scan_directory({'config': config, 'root': root})
