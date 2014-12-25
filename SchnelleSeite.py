#!/usr/bin/python3

import sys
import os
import loader

# alt: os.path.dirname(os.path.abspath(__file__))
SCRIPT_PATH = os.path.dirname(os.path.abspath(sys.argv[0]))
SITE_PATH = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()


config = {
    "template_path": SCRIPT_PATH,
    "site_path": SITE_PATH,
    "build_dir": "__site",
    "script_path": SCRIPT_PATH
}


if __name__ == "__main__":
    os.chdir("../newsite")
    config['site_path'] = os.path.dirname(os.path.abspath(os.getcwd()))
    os.chdir("_philosophy")
    loader.test_scan_directory(config=config)
