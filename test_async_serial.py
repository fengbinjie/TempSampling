import unittest
import struct
import core.protocol as pr
import core


class AsyncSerialTestSuite(unittest.TestCase):
    protocol = pr.protocol
    sub_protocol = pr.sub_protocol
    data = b'temp_sample'
    fixed_token = protocol.fixed_token.default_value
    sub_fixed_token = sub_protocol.fixed_token.default_value
    node_addr = 0x1234
    profile_id = 0x01
    serial_num = 127
    client_id = 0x03

    def test_dynamic_package(self):
        actual = pr.Package(fixed_token=self.fixed_token, node_addr=self.node_addr,
                            data_len=len(self.data),
                            profile_id=self.profile_id, serial_num=self.serial_num).produce(self.data)
        expected = struct.pack(f'{self.protocol.endian}{self.protocol.header_fmt}{len(self.data)}s',
                               self.fixed_token,
                               len(self.data),
                               self.node_addr,
                               self.profile_id,
                               self.serial_num,
                               self.data)

        self.assertEqual(expected, actual)

    def test_dynamic_sub_package(self):
        actual = pr.SubPackage(fixed_token=self.sub_fixed_token,
                               serial_num=self.serial_num).produce(self.data)

        expected = struct.pack(f'{self.sub_protocol.endian}{self.sub_protocol.header_fmt}{len(self.data)}s',
                               self.sub_fixed_token,
                               self.serial_num,
                               self.data)
        self.assertEqual(expected, actual)

    def test_dynamic_complete_package(self):
        actual = pr.complete_package(node_addr=self.node_addr,
                                     profile_id=self.profile_id,
                                     serial_num=self.serial_num,
                                     data=self.data)
        sub_package = struct.pack(f'{self.sub_protocol.endian}{self.sub_protocol.header_fmt}{len(self.data)}s',
                                  self.sub_fixed_token,
                                  self.serial_num,
                                  self.data)
        expected = struct.pack(f'{self.protocol.endian}{self.protocol.header_fmt}{len(sub_package)}s',
                               self.fixed_token,
                               len(sub_package),
                               self.node_addr,
                               self.profile_id,
                               self.serial_num,
                               sub_package)
        self.assertEqual(expected, actual)

    def test_dynamic_parse_package(self):
        reversed_package, reversed_sub_package, data = pr.parse_package(b'\xcd\xab\r4\x12\x01\x7f\xcb\x7ftemp_sample')

        self.assertEqual(self.fixed_token, reversed_package.fixed_token)
        self.assertEqual(len(self.data) + self.sub_protocol.header_fmt_size, reversed_package.data_len)
        self.assertEqual(self.node_addr, reversed_package.node_addr)
        self.assertEqual(self.profile_id, reversed_package.profile_id)
        self.assertEqual(self.serial_num, reversed_package.serial_num)

        self.assertEqual(self.sub_fixed_token, reversed_sub_package.fixed_token)
        self.assertEqual(self.serial_num, reversed_sub_package.serial_num)

        self.assertEqual(self.data, data)
