#!/usr/bin/python3

import os
import sys

import yaml

import generator
import loader

# alt: os.path.dirname(os.path.abspath(__file__))
SCRIPT_PATH = os.path.dirname(os.path.abspath(sys.argv[0]))
SITE_PATH = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()


config = {
    "template_paths": [os.path.join(SCRIPT_PATH, "templates")],
    "copyonly": ['robots.txt'],
    "site_path": SITE_PATH,
    "build_path": "__site",
    "generator_path": SCRIPT_PATH,
    "generator_resources": {},
}

config['generator_resources']['_data'] = generator.scan_directory(
    os.path.join(SCRIPT_PATH, "_data"), loader.STOCK_LOADERS,
    {'language': 'ANY'})

# read config file


def read_configfile():
    with open(os.path.join(SITE_PATH, "_site-config.yaml")) as cfg_file:
        cfg = yaml.load(cfg_file)
    if 'template_paths' in cfg:
        cfg['template_paths'].extend(config['template_paths'])
        config['template_paths'] = cfg['template_paths']
        del cfg['template_paths']
    if 'copyonly' in cfg:
        config['copyonly'] = list(set(config['copyonly']) |
                                  set(cfg['copyonly']))
        del cfg['copyonly']
    overlap = set(config.keys()) & set(cfg.keys())
    if overlap:
        raise ValueError("Illegal keys in '_site-config': {0!s}".
                         format(overlap))
    config.update(cfg)

read_configfile()

if __name__ == "__main__":
    os.chdir("../newsite")
    config['site_path'] = os.path.dirname(os.path.abspath(os.getcwd()))
    os.chdir("_philosophy")
    generator.test_scan_directory({'config': config})
