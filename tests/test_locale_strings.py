
import os
import sys
import unittest
from locale_strings import *

# import locale_strings  --> see below


class TestLocaleStrings(unittest.TestCase):

    def test_narrow_match(self):
        self.assertEqual(narrow_match('ANY', {'ANY'}), 'ANY')

    def test_get_locale(self):
        self.assertEqual(get_locale("name_ANY"), 'ANY')
        self.assertEqual(get_locale("name_en_US"), 'en_US')
        self.assertEqual(get_locale("name_DE"), 'DE')
        self.assertEqual(get_locale("name"), '')

        self.assertRaises(LocaleError, get_locale, "name_XY")
        self.assertRaises(LocaleError, get_locale, "name_De")
        self.assertRaises(LocaleError, get_locale, "name_ex_US")
        self.assertRaises(LocaleError, get_locale, "name_EN_US")

        # assume no mistake in the following case
        self.assertEqual(get_locale("name_ABC"), '')

    def test_remove_locale(self):
        self.assertEqual(remove_locale("test_ANY.txt"), "test.txt")
        self.assertEqual(remove_locale("test.txt"), "test.txt")
        self.assertEqual(remove_locale("test"), "test")
        self.assertEqual(remove_locale("test_en_US.txt"), "test.txt")
        self.assertEqual(remove_locale("test_DE"), "test")
        # don't remove locales if filename only consists of a locale
        self.assertEqual(remove_locale("_EN.txt"), "_EN.txt")
        # raise an error for false locales
        self.assertRaises(LocaleError, remove_locale, "test_US.txt")

    def test_extract_locale(self):
        self.assertEqual(extract_locale("alpha/beta_DE/gamma.txt"), "DE")
        self.assertEqual(extract_locale("alpha_DE/beta_EN/gamma.txt"), "EN")
        self.assertEqual(extract_locale("alpha/beta/gamma_DE.txt"), "DE")
        self.assertEqual(extract_locale("alpha/beta/gamma.txt"), "")
        self.assertEqual(extract_locale("alpha/beta_DE/gamma_ANY.txt"), "ANY")


# if __name__ == "__main__":
#     sys.path.append(
#         os.path.split(os.path.dirname(os.path.abspath(sys.argv[0])))[0])
#     from locale_strings import *
#     unittest.main()
