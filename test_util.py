import unittest
import core.util as util
class TableDisplayTestSuite(unittest.TestCase):
    t = util.TableDisplay("field1","field2","field3")

    def test_get_str_print_len(self):
        length = self.t.get_str_print_len("heel你好")
        print("heel你好\n- - - - ")
        self.assertEqual(length, 8)