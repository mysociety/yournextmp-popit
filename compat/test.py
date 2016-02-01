from __future__ import unicode_literals

import unittest

from ._compat import StreamDictReader, StreamDictWriter


# These tests were adapted from the Python 3.5 stdlib test/test_csv.py
# module.

class TestDictFields(unittest.TestCase):
    ### "long" means the row is longer than the number of fieldnames
    ### "short" means there are fewer elements in the row than fieldnames
    def test_write_simple_dict(self):
        writer = StreamDictWriter(fieldnames=["f1", "f2", "f3"])
        writer.writeheader()
        writer.f.seek(0)
        self.assertEqual(writer.f.readline(), "f1,f2,f3\r\n")
        writer.writerow({"f1": 10, "f3": "abc"})
        writer.f.seek(0)
        writer.f.readline() # header
        self.assertEqual(writer.f.read(), "10,,abc\r\n")

    def test_write_multiple_dict_rows(self):
        writer = StreamDictWriter(fieldnames=["f1", "f2", "f3"])
        writer.writeheader()
        self.assertEqual(writer.output, "f1,f2,f3\r\n")
        writer.writerows([{"f1": 1, "f2": "abc", "f3": "f"},
                          {"f1": 2, "f2": 5, "f3": "xyz"}])
        self.assertEqual(writer.output,
                         "f1,f2,f3\r\n1,abc,f\r\n2,5,xyz\r\n")

    def test_write_no_fields(self):
        self.assertRaises(TypeError, StreamDictWriter)

    def test_write_fields_not_in_fieldnames(self):
        writer = StreamDictWriter(fieldnames=["f1", "f2", "f3"])
        # Of special note is the non-string key (issue 19449)
        with self.assertRaises(ValueError) as cx:
            writer.writerow({"f4": 10, "f2": "spam", 1: "abc"})
        exception = str(cx.exception)
        self.assertIn("fieldnames", exception)
        self.assertIn("'f4'", exception)
        self.assertNotIn("'f2'", exception)
        self.assertIn("1", exception)

    def test_read_dict_fields(self):
        reader = StreamDictReader("1,2,abc\r\n",
                                  fieldnames=["f1", "f2", "f3"])
        self.assertEqual(next(reader), {"f1": '1', "f2": '2', "f3": 'abc'})

    def test_read_dict_no_fieldnames(self):
        reader = StreamDictReader("f1,f2,f3\r\n1,2,abc\r\n")
        self.assertEqual(next(reader), {"f1": '1', "f2": '2', "f3": 'abc'})
        self.assertEqual(reader.fieldnames, ["f1", "f2", "f3"])

    # Two test cases to make sure existing ways of implicitly setting
    # fieldnames continue to work.  Both arise from discussion in issue3436.

    # This one's not supported

    # def test_read_dict_fieldnames_from_file(self):
    #     with TemporaryFile("w+") as fileobj:
    #         fileobj.write("f1,f2,f3\r\n1,2,abc\r\n")
    #         fileobj.seek(0)
    #         reader = csv.DictReader(fileobj,
    #                                 fieldnames=next(csv.reader(fileobj)))
    #         self.assertEqual(reader.fieldnames, ["f1", "f2", "f3"])
    #         self.assertEqual(next(reader), {"f1": '1', "f2": '2', "f3": 'abc'})

    def test_read_dict_fieldnames_chain(self):
        import itertools
        reader = StreamDictReader("f1,f2,f3\r\n1,2,abc\r\n")
        first = next(reader)
        for row in itertools.chain([first], reader):
            self.assertEqual(reader.fieldnames, ["f1", "f2", "f3"])
            self.assertEqual(row, {"f1": '1', "f2": '2', "f3": 'abc'})

    def test_read_long(self):
        reader = StreamDictReader("1,2,abc,4,5,6\r\n",
                                  fieldnames=["f1", "f2"])
        self.assertEqual(next(reader), {"f1": '1', "f2": '2',
                                        None: ["abc", "4", "5", "6"]})

    def test_read_long_with_rest(self):
        reader = StreamDictReader("1,2,abc,4,5,6\r\n",
                                  fieldnames=["f1", "f2"], restkey="_rest")
        self.assertEqual(next(reader), {"f1": '1', "f2": '2',
                                         "_rest": ["abc", "4", "5", "6"]})

    def test_read_long_with_rest_no_fieldnames(self):
        reader = StreamDictReader("f1,f2\r\n1,2,abc,4,5,6\r\n",
                                  restkey="_rest")
        self.assertEqual(reader.fieldnames, ["f1", "f2"])
        self.assertEqual(next(reader), {"f1": '1', "f2": '2',
                                         "_rest": ["abc", "4", "5", "6"]})

    def test_read_short(self):
        reader = StreamDictReader("1,2,abc,4,5,6\r\n1,2,abc\r\n",
                                  fieldnames="1 2 3 4 5 6".split(),
                                  restval="DEFAULT")
        self.assertEqual(next(reader), {"1": '1', "2": '2', "3": 'abc',
                                         "4": '4', "5": '5', "6": '6'})
        self.assertEqual(next(reader), {"1": '1', "2": '2', "3": 'abc',
                                         "4": 'DEFAULT', "5": 'DEFAULT',
                                         "6": 'DEFAULT'})

    def test_read_multi(self):
        sample = '\r\n'.join(
            [
                '2147483648,43.0e12,17,abc,def',
                '147483648,43.0e2,17,abc,def',
                '47483648,43.0,170,abc,def',
                ''
            ]
        )

        reader = StreamDictReader(sample,
                                  fieldnames="i1 float i2 s1 s2".split())
        self.assertEqual(next(reader), {"i1": '2147483648',
                                         "float": '43.0e12',
                                         "i2": '17',
                                         "s1": 'abc',
                                         "s2": 'def'})

    def test_read_with_blanks(self):
        sample = '\r\n'.join(
            [
                "1,2,abc,4,5,6",
                "",
                "1,2,abc,4,5,6"
                ""
            ]
        )
        reader = StreamDictReader(sample,
                                  fieldnames="1 2 3 4 5 6".split())
        self.assertEqual(next(reader), {"1": '1', "2": '2', "3": 'abc',
                                         "4": '4', "5": '5', "6": '6'})
        self.assertEqual(next(reader), {"1": '1', "2": '2', "3": 'abc',
                                         "4": '4', "5": '5', "6": '6'})

    def test_read_semi_sep(self):
        reader = StreamDictReader("1;2;abc;4;5;6\r\n",
                                  fieldnames="1 2 3 4 5 6".split(),
                                  delimiter=';')
        self.assertEqual(next(reader), {"1": '1', "2": '2', "3": 'abc',
                                         "4": '4', "5": '5', "6": '6'})

if __name__ == '__main__':
    unittest.main()
