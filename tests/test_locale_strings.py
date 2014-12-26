
import os
import sys
import unittest


class TestLocaleStrings(unittest.TestCase):

    def test_narrow_match(self):
        self.assertEqual(locale_strings.narrow_match('ANY', {'ANY'}), 'ANY')

if __name__ == "__main__":
    sys.path.append(
        os.path.split(os.path.dirname(os.path.abspath(sys.argv[0])))[0])
    import locale_strings
    unittest.main()
