# -*- coding: utf-8 -*-
"""
Created on Tue Dec  9 16:21:42 2014

@author: eckhart
"""

import re

with open("locale.gen", "r") as src:
    locale_gen = src.read()

locales = list(set(re.findall("[a-z][a-z]_[A-Z][A-Z]", locale_gen)))
locales.sort()
locales_short = list(set([lc[0:2].upper() for lc in locales]))
locales_short.sort()

def dump_list(l, group=6):  # 9
    result = ['\n    [ ']
    for n, item in enumerate(l,1):
        if n == len(l):
            s = '"%s"]' % item
        else:
            if n % group == 0:
                s = '"%s",\n      ' % item
            else:
                s = '"%s", ' % item
        result.append(s)
    return "".join(result)

with open("locales.json", "w") as dst:
    dst.write('{\n')
    dst.write('  "locales": ')
    dst.write(dump_list(locales, 8))
    dst.write(',\n')
    dst.write('  "locales_short": ')
    dst.write(dump_list(locales_short, 12))
    dst.write('\n}\n')


       
    