import unittest
import core.async_serial as aserial
import core.protocol as pr


class AsyncSerialTestSuite(unittest.TestCase):
    def test_get_protocol(self):
        result = aserial.get_protocol("protocol.yml")
        print(result)
        self.assertIsInstance(result, dict)

    def test_get_content(self):
        result = pr.Protocol.get_protocol().header
        print(result)

    def test_set_content(self):
        result = pr.Protocol.get_protocol().set_content(1, 2, 3, 4, 5, 6)
        print(result)

    def test_get_bytes(self):
        data = b''
        result = pr.Protocol.get_protocol().produce_package(len(data), 1, 2, 3, 4, data)
        self.assertEqual(result, b'\xcd\xab\x00\x00\x00\x01\x02\x00\x03\x04b')

    def test_get_header_content(self):
        result = pr.Protocol.get_protocol().get_header_content(b'\xcd\xab\x00\x00\x01\x02\x03\x00\x04\x00\x05\x006Q')
        print(result)

    def test_sub_get_bytes(self):
        data = b''
        result = pr.SubProtocol.get_sub_protocol().produce_sub_package(len(data), 2, 3, 4, 5, data)
        self.assertEqual(result, b'\xcb\x00\x02\x03\x00\x04\x05')

    def test_complete_package(self):
        data = b''
        result = pr.complete_package(device_type=1, profile_id=2, serial_num=3, client_id=4, dest_addr=5, Data=data)
        self.assertEqual(result, b'\xcd\xab\x00\x00\x07\x01\x02\x00\x03\x04\xcb\x00\x04\x05\x00\x02\x03\xae')

    def test_dynamic_package(self):
        data = b''
        package = pr.Package(fixed_token=0xabcd, node_addr=0, data_len=len(data), profile_id=3, serial_num=4,
                             client_id=5)
        result = package.produce(data)
        self.assertEqual(b'\xcd\xab\x00\x00\x00\x03\x04\x05', result)

    def test_dynamic_sub_package(self):
        data = b''
        package = pr.SubPackage(fixed_token=0xcb, data_len=len(data), client_id=3, serial_num=4, profile_id=5)
        result = package.produce(data)
        self.assertEqual(b'\xcb\x00\x03\x04\x05', result)

    def test_dynamic_complete_package(self):
        data = b''
        result = pr.complete_package(node_addr=0, profile_id=3, serial_num=4, client_id=5, data=data)
        self.assertEqual(b'\xcd\xab\x00\x00\x05\x03\x04\x05\xcb\x00\x03\x04\x05\xa8', result)

    def test_dynamic_parse_package(self):
        reversed_package, reversed_sub_package, data = pr.parse_package(
            b'\xcd\xab\x00\x00\x05\x03\x04\x05\xcb\x00\x03\x04\x05\xa8')

        self.assertEqual(0xabcd, reversed_package.fixed_token)
        self.assertEqual(0, reversed_package.node_addr)
        self.assertEqual(pr.sub_protocol.header_fmt_size, reversed_package.data_len, )
        self.assertEqual(3, reversed_package.profile_id)
        self.assertEqual(4, reversed_package.serial_num)
        self.assertEqual(5, reversed_package.client_id)

        self.assertEqual(0xcb, reversed_sub_package.fixed_token)
        self.assertEqual(len(data), reversed_sub_package.data_len)
        self.assertEqual(3, reversed_sub_package.profile_id)
        self.assertEqual(4, reversed_sub_package.serial_num)
        self.assertEqual(5, reversed_sub_package.client_id)

        self.assertEqual(0, len(data))
