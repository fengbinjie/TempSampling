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
        data = b''
        result = aserial._Protocol.get_protocol().produce_package(len(data), 1, 2, 3, 4, data)
        self.assertEqual(result,b'\xcd\xab\x00\x00\x00\x01\x02\x00\x03\x04b')

    def test_get_header_content(self):
        result = aserial._Protocol.get_protocol().get_header_content(b'\xcd\xab\x00\x00\x01\x02\x03\x00\x04\x00\x05\x006Q')
        print(result)

    def test_sub_get_bytes(self):
        data = b''
        result = aserial.Sub_Protocol.get_sub_protocol().produce_sub_package(len(data), 2, 3, 4, 5, data)
        self.assertEqual(result, b'\xcb\x00\x02\x03\x00\x04\x05')

    def test_complete_package(self):
        data = b''
        result = aserial.complete_package(device_type=1,profile_id=2,serial_num=3,client_id=4,dest_addr=5,Data=data)
        self.assertEqual(result,b'\xcd\xab\x00\x00\x07\x01\x02\x00\x03\x04\xcb\x00\x04\x05\x00\x02\x03\xae')

    def test_dynamic_package(self):
        data = b''
        package =aserial.Package(fixed_token=0xabcd,reservered_token=0,D_LEN=len(data),device_type=1,profile_id=2,serial_number=3,client_id=4)
        result = package.produce(data)
        self.assertEqual(result, b'\xcd\xab\x00\x00\x00\x01\x02\x00\x03\x04b')

    def test_dynamic_sub_package(self):
        data = b''
        package = aserial.Sub_Package(fixed_token=0xcb,LEN=len(data),client_id=2,dest_addr=3,profile_id=4,serial_num=5)
        result = package.produce(data)
        self.assertEqual(result,b'\xcb\x00\x02\x03\x00\x04\x05')