import unittest
import core.async_serial as aserial
import core.async_serial as async_serial


class AsyncSerialTestSuite(unittest.TestCase):
    def test_get_protocol(self):
        result = aserial.get_protocol("protocol.yml")
        print(result)
        self.assertIsInstance(result, dict)

    def test_get_content(self):
        result = aserial._Protocol.get_protocol().header
        print(result)
    def test_set_content(self):
        result = aserial._Protocol.get_protocol().set_content(1,2,3,4,5,6)
        print(result)
    def test_get_bytes(self):
        result = aserial._Protocol.get_protocol().produce_package(1, 2, 3, 4, 5, b'6')
        print(result)
    def test_get_header_content(self):
        result = aserial._Protocol.get_protocol().get_header_content(b'\xcd\xab\x00\x00\x01\x02\x03\x00\x04\x00\x05\x006Q')
        print(result)

    def test_sub_get_bytes(self):
        data = b''
        result = aserial.Sub_Protocol.get_sub_protocol().produce_sub_package(len(data), 2, 3, 4, 5, data)
        print(result)

    def test_complete_package(self):
        data = b''
        result = aserial.complete_package(device_type=1,profile_id=2,serial_num=3,client_id=4,dest_addr=5,Data=data)
        print(result)