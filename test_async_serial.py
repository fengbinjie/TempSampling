import unittest
import core.async_serial as aserial
import core.async_serial as async_serial


class AsyncSerialTestSuite(unittest.TestCase):
    def test_get_protocol(self):
        result = aserial.get_protocol("protocol.yml")
        print(result)
        self.assertIsInstance(result, dict)

    def test_get_content(self):
        result = aserial._Protocol.get_protocol().protocol_content
        print(result)
    def test_set_conten(self):
        result = aserial._Protocol.get_protocol().set_content(1,2,3,4,5,6)
        print(result)
    def test_get_bytes(self):
        result = aserial._Protocol.get_protocol().get_bytes(1,2,3,4,5,b'6')
        print(result)