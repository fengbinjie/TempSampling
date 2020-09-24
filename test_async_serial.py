import unittest
import core.async_serial as aserial
import core.async_serial as async_serial


class AsyncSerialTestSuite(unittest.TestCase):
    def test_get_protocol(self):
        result = aserial.get_protocol("protocol.yml")
        print(result)
        self.assertIsInstance(result, dict)

