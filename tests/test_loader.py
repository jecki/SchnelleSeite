
import io
import os
#import sys
import unittest

import loader


class TestLoader(unittest.TestCase):

    def loadSnippet(self, snippet, injected_metadata={'basename': 'loadertest'}):
        file_name = "testdata/loadertest.txt"
        with open(file_name, "w") as f, \
                io.StringIO(snippet) as g:
            for line in g:
                f.write(line.lstrip())
        result = loader.load(file_name, injected_metadata=injected_metadata)
        os.remove(file_name)
        return result

    def tearDown(self):
        unittest.TestCase.tearDown(self)
        if os.path.exists("testdata/loadertest.txt"):
            os.remove("testdata/loadertest.txt")

    def test_boundary_cases(self):
        snp1 = "+++\na: 1\nlanguage: ANY\n+++\ninhalt\n"
        res1 = {
            'ANY': {'metadata': {'language': 'ANY', 'a': 1,
                                 'basename': 'loadertest'},
                    'content': "inhalt\n"}}
        # leading and trailing empty lines
        self.assertEqual(
            self.loadSnippet("\n  \n\n" + snp1 + "   \n \n\n")['loadertest'],
            res1)

        # additional empty lines
        snp2 = snp1.replace("\n", "\n  \n\n \n")
        self.assertEqual(self.loadSnippet(snp2)['loadertest'], res1)

    def test_zero_headers(self):
        res = {'ANY': {'metadata': {'language': 'ANY',
                                    'basename': 'loadertest'},
                       'content': "inhalt"}}
        injected_metadata = {'language': 'ANY', 'basename': 'loadertest'}
        self.assertEqual(self.loadSnippet("inhalt",
                                          injected_metadata)['loadertest'],
                         res)
        res['ANY']['content'] = "inhalt\n"
        self.assertEqual(
            self.loadSnippet("\ninhalt\n\n", injected_metadata)['loadertest'],
            res)

    def test_empty_header(self):
        snp = "+++\nlanguage: DE\n+++\ninhalt"
        res = {'DE': {'metadata': {'language': 'DE', 'basename': 'loadertest'},
                      'content': "inhalt"}}
        self.assertEqual(self.loadSnippet(snp)['loadertest'], res)

    def test_single_header(self):
        snp1 = "+++\nlanguage: ANY\na: 1\n+++\nInhalt\n"
        res1 = {
            'ANY': {'metadata': {'language': 'ANY', 'a': 1,
                                 'basename': 'loadertest'},
                    'content': "Inhalt\n"}}
        self.assertEqual(self.loadSnippet(snp1)['loadertest'], res1)

#     def test_multiple_headers(self):
#         pass

    def test_bad_headers(self):
        for snp in ["+++", "\n+++\n", "a\n+++\nb: 1", "\n+++\n+++\n+++"]:
            self.assertRaisesRegex(loader.MalformedFile,
                                   loader.MalformedFile.END_MARKER_MISSING,
                                   self.loadSnippet, snp)

    def test_empty_files(self):
        empty = {'en_US': {'metadata': {'language': 'en_US',
                                        'basename': 'loadertest'},
                           'content': ""}}
        self.assertEqual(
            self.loadSnippet("", empty['en_US']['metadata'])['loadertest'],
            empty)
        self.assertEqual(
            self.loadSnippet("+++\nlanguage: en_US\n+++\n")['loadertest'],
            empty)
        self.assertRaisesRegex(loader.MalformedFile,
                               loader.MalformedFile.LANGUAGE_INFO_MISSING,
                               self.loadSnippet, "+++\n+++\n+++\n+++\n")

    def test_multiple_blocks_of_same_lang_exceptions(self):
        snp = ("+++\nlanguage: DE\n+++\nInhalt DE\n"
               "+++\nlanguage: EN\n+++\nInhalt EN\n"
               "+++\nlanguage: DE\n+++\n2. Inhalt DE!!!\n")
        self.assertRaisesRegex(
            loader.MalformedFile,
            loader.MalformedFile.MULTIPLE_BLOCKS_OF_SAME_LANGUAGE,
            self.loadSnippet, snp)

    def test_load_transtable(self):
        transtable_csv = ("EN;DE\n"
                          "English;Englisch\n"
                          "German;Deutsch\n"
                          "\n\n")
        transtable = loader.csv_loader(transtable_csv, {})
        result = loader.load_transtable(transtable, {'item': 'test'})
        self.assertEqual(result['EN']['metadata']['item'], 'test')
        self.assertEqual(result['DE']['metadata']['item'], 'test')
        self.assertEqual(result['DE']['content']['English'], "Englisch")
        self.assertEqual(result['DE']['content']['German'], "Deutsch")
        self.assertEqual(result['EN']['content']['English'], "English")
        self.assertEqual(result['EN']['content']['German'], "German")


# if __name__ == "__main__":
#     sys.path.append(
#         os.path.split(os.path.dirname(os.path.abspath(sys.argv[0])))[0])
#     import loader
#     unittest.main()
