
import io
import os
import sys
import unittest


class TestLoader(unittest.TestCase):

    def writeSnippet(self, snippet):
        file_name = "testdata/loadertest.txt"
        with open(file_name, "w") as f, \
                io.StringIO(snippet) as g:
            for line in g:
                f.write(line.lstrip())
        return file_name

    def loadSnippet(self, snippet):
        file_name = self.writeSnippet(snippet)
        result = loader.load(file_name)
        os.remove(file_name)
        return result

    def tearDown(self):
        unittest.TestCase.tearDown(self)
        if os.path.exists("testdata/loadertest.txt"):
            os.remove("testdata/loadertest.txt")

    def test_boundary_cases(self):
        snp1 = "+++\na: 1\n+++\ninhalt\n"
        res1 = {'ANY': {'metadata': {'a': 1}, 'content': "inhalt\n"}}
        # leading and trailing empty lines
        self.assertEqual(
            self.loadSnippet("\n  \n\n" + snp1 + "   \n \n\n"), res1)

        # additional empty lines
        snp2 = snp1.replace("\n", "\n  \n\n \n")
        self.assertEqual(self.loadSnippet(snp2), res1)

    def test_zero_header_files(self):
        res = {'ANY': {'metadata': {}, 'content': "inhalt"}}
        self.assertEqual(self.loadSnippet("inhalt"), res)
        res['ANY']['content'] = "inhalt\n"
        self.assertEqual(self.loadSnippet("\ninhalt\n\n"), res)

    def test_empty_header_file(self):
        snp = "+++\n+++\ninhalt"
        res = {'ANY': {'metadata': {}, 'content': "inhalt"}}
        self.assertEqual(self.loadSnippet(snp), res)

    def test_single_header_file(self):
        snp1 = "+++\na: 1\n+++\ninhalt\n"
        res1 = {'ANY': {'metadata': {'a': 1}, 'content': "inhalt\n"}}
        self.assertEqual(self.loadSnippet(snp1), res1)

    def test_multiple_header_files(self):
        pass

#     def test_missing_language(self):
#         self.assertEqual(self.loadSnippet("+++\n+++\n" + snp4), res4)
#         self.assertEqual(self.loadSnippet("+++\n+++\n+++\n+++\n" + snp4), res4)

    def test_empty_files(self):
        empty = {'ANY': {'metadata': {}, 'content': ""}}
        self.assertEqual(self.loadSnippet(""), empty)
        self.assertEqual(self.loadSnippet("+++\n+++\n"), empty)
        file_name = self.writeSnippet("+++\n+++\n+++\n+++\n")
        self.assertRaises(loader.MalformedFile, loader.load(file_name))


if __name__ == "__main__":
    sys.path.append(
        os.path.split(os.path.dirname(os.path.abspath(sys.argv[0])))[0])
    import loader
    unittest.main()
