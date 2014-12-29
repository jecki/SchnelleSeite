
import io
import os
import sys
import unittest


class TestLoader(unittest.TestCase):

    def loadSnippet(self, snippet, injected_metadata={}):
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
            'ANY': {'metadata': {'language': 'ANY', 'a': 1},
                    'content': "inhalt\n"}}
        # leading and trailing empty lines
        self.assertEqual(
            self.loadSnippet("\n  \n\n" + snp1 + "   \n \n\n"), res1)

        # additional empty lines
        snp2 = snp1.replace("\n", "\n  \n\n \n")
        self.assertEqual(self.loadSnippet(snp2), res1)

    def test_zero_headers(self):
        res = {'ANY': {'metadata': {'language': 'ANY'}, 'content': "inhalt"}}
        injected_metadata = {'language': 'ANY'}
        self.assertEqual(self.loadSnippet("inhalt", injected_metadata), res)
        res['ANY']['content'] = "inhalt\n"
        self.assertEqual(
            self.loadSnippet("\ninhalt\n\n", injected_metadata), res)

    def test_empty_header(self):
        snp = "+++\nlanguage: DE\n+++\ninhalt"
        res = {'DE': {'metadata': {'language': 'DE'}, 'content': "inhalt"}}
        self.assertEqual(self.loadSnippet(snp), res)

    def test_single_header(self):
        snp1 = "+++\nlanguage: ANY\na: 1\n+++\ninhalt\n"
        res1 = {
            'ANY': {'metadata': {'language': 'ANY', 'a': 1},
                    'content': "inhalt\n"}}
        self.assertEqual(self.loadSnippet(snp1), res1)

#     def test_multiple_headers(self):
#         pass

    def test_bad_headers(self):
        for snp in ["+++", "\n+++\n", "a\n+++\nb: 1", "\n+++\n+++\n+++"]:
            self.assertRaisesRegex(loader.MalformedFile,
                                   loader.MalformedFile.END_MARKER_MISSING,
                                   self.loadSnippet, snp)

    def test_empty_files(self):
        empty = {'en_US': {'metadata': {'language': 'en_US'}, 'content': ""}}
        self.assertEqual(
            self.loadSnippet("", empty['en_US']['metadata']), empty)
        self.assertEqual(
            self.loadSnippet("+++\nlanguage: en_US\n+++\n"), empty)
        self.assertRaisesRegex(loader.MalformedFile,
                               loader.MalformedFile.LANGUAGE_INFO_MISSING,
                               self.loadSnippet, "+++\n+++\n+++\n+++\n")


if __name__ == "__main__":
    sys.path.append(
        os.path.split(os.path.dirname(os.path.abspath(sys.argv[0])))[0])
    import loader
    unittest.main()
