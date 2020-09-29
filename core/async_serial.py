import argparse
import contextlib
import os
import time
import struct
import serial
import serial.tools.list_ports
import yaml
from collections import OrderedDict
import types
__title__ = 'tempsampling'
__version__ = '0.1.0'
__build__ = 0x000100
__author__ = 'Binjie Feng'
__license__ = 'ISC'
__copyright__ = 'Copyright 2020 Binjie Feng'

DEFAULT_COM = None
if os.name is 'nt':
    DEFAULT_COM = ''
elif os.name is 'posix':
    DEFAULT_COM = '/dev/ttyAMA0'
else:
    raise Exception('unsupported system')


class Com:
    def __init__(self, url=DEFAULT_COM, baudrate=115200):
        if url in find_serial_port_list():
            self.com = serial.Serial()
        else:
            raise Exception("there is no such a port")
        self.receiveProgressStop = False
        self.sendProgressStop = False
        self.noFeedBackCount = 0
        self.feedBackCount = 0
        self.sendCount = 0

    def get_noFeedBackCount(self):
        return self.sendCount - self.feedBackCount

    def get_feedBackCount(self):
        return self.feedBackCount

    def get_sendCount(self):
        return self.sendCount

    def receive_data(self, length_set=1):
        while not self.receiveProgressStop:
            length = length_set if length_set else max(1, min(2048, self.com.in_waiting))
            try:
                _bytes = self.com.read(length)
            except Exception as why:
                raise why
            else:
                self.feedBackCount += 1
                return _bytes

    def send_data(self, data):
        if self.com.is_open and data != -1:
            return
        try:
            self.com.write(data)
        except Exception as why:
            raise why
        else:
            self.sendCount += 1

    def close(self):
        self.receiveProgressStop = True
        if self.com.is_open:
            try:
                self.com.close()
            except Exception as why:
                raise why


class ProtocolParamAttribute:
    def __init__(self, index, fmt, value):
        self.index, self.fmt, self.value = index, fmt, value


class Sub_Protocol:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        self.fixed_token = ProtocolParamAttribute(1,'B',0xcb)
        self.LEN = ProtocolParamAttribute(2,'B',None)
        self.client_id = ProtocolParamAttribute(3,'B',None)
        self.dest_addr = ProtocolParamAttribute(4,'H',None)
        self.profile_id = ProtocolParamAttribute(5,'B',None)
        self.serial_num = ProtocolParamAttribute(6,'B',None)
        self.header = OrderedDict()
        for var, value in self.__dict__.items():
            if isinstance(value, ProtocolParamAttribute):
                self.header[var] = value

        self.header_fmt = ''.join([v.fmt for v in self.header.values()])
        self.header_fmt_size = sum({'B': 1, 'H': 2, 'I': 4}[c.fmt] for c in self.header.values())
        self.endian = '<'
        self.data = None

    def _set_header(self,LEN,client_id,dest_addr,profile_id,serial_num):
        kwargs = locals()
        kwargs.pop('self')
        for var_name, var_value in kwargs.items():
            self.header[var_name].value = var_value

    def _get_header_content(self):
        return [v.value for v in self.header.values()]

    def produce_sub_package(self, LEN, client_id, dest_addr, profile_id, serial_num, DATA):
        self._set_header(LEN, client_id,dest_addr,profile_id,serial_num)
        complete_fmt = self.endian + self.header_fmt + f'{LEN}s'
        # 打包头、数据
        values_bytes = struct.pack(complete_fmt, *(self._get_header_content()), DATA)

        return values_bytes

    def unpack_bytes(self, acquired_bytes):
        fixed_token,\
        LEN, \
        client_id, \
        dest_addr, \
        profile_id,\
        serial_number = struct.unpack_from(self.endian+self.header_fmt, acquired_bytes)
        data = struct.unpack_from(f'{self.endian}{LEN}s', acquired_bytes, offset=self.header_fmt_size)
        return data

    @classmethod
    def get_sub_protocol(cls):
        return cls._instance if cls._instance else cls()


class _Protocol:
    # TODO: 该类应该可以动态生成
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        self.fixed_token = ProtocolParamAttribute(1, 'H', 0xabcd)
        self.reservered_token = ProtocolParamAttribute(2, 'H', 0x0000)
        self.D_LEN = ProtocolParamAttribute(3, 'B', None)
        self.device_type = ProtocolParamAttribute(4, 'B', None)
        self.profile_id = ProtocolParamAttribute(5, 'H', None)
        self.serial_number = ProtocolParamAttribute(6, 'B', None)
        self.client_id = ProtocolParamAttribute(7, 'B', None)

        # 将所有协议头格式存在header_content顺序字典中
        self.header = OrderedDict()
        for var, value in self.__dict__.items():
            if isinstance(value, ProtocolParamAttribute):
                self.header[var] = value

        self.header_fmt = ''.join(c.fmt for c in self.header.values())
        self.header_fmt_size = sum({'B': 1, 'H': 2, 'I': 4}[c.fmt] for c in self.header.values())
        self.endian = '<'

    @staticmethod
    def _get_protocol_from_file(path):
        with open_file(path) as f:
            try:
                protocol_dict = yaml.load(f)
            except yaml.YAMLError as why:
                print("error format")
            else:
                return protocol_dict

    @classmethod
    def get_protocol(cls):
        return cls._instance if cls._instance else cls()

def check(buf):
    xor_result = 0
    for v in buf:
        xor_result = xor_result ^ v
    return xor_result

sub_protocol = Sub_Protocol.get_sub_protocol()
protocol = _Protocol.get_protocol()




def package_init(self, **kwargs):
    print(self.__slot__)
    print(kwargs)
    for parameter, value in kwargs.items():
        if parameter in self.__slot__:
            setattr(self, parameter, value)
        else:
            raise Exception("invalid keyword arguments")

    self.package_value_list = kwargs.values()

def package_produce(self, DATA):
    complete_fmt = protocol.endian + protocol.header_fmt + f'{self.D_LEN}s'
    # 打包头、数据
    values_bytes = struct.pack(complete_fmt, *self.package_value_list, DATA)
    # 打包校验码
    check_byte = struct.pack(f'{protocol.endian}B', check(values_bytes))

    return values_bytes + check_byte

def package_parse(self):
    pass


Package = type('Package', (object,), {'__slot__': tuple(v for v in protocol.header.keys()),
                                      '__init__': package_init,
                                      'produce': package_produce,
                                      'parse': package_parse}
               )

def sub_package_produce(self, DATA):
    complete_fmt = sub_protocol.endian + sub_protocol.header_fmt + f'{self.LEN}s'
    # 打包头、数据
    values_bytes = struct.pack(complete_fmt, *self.package_value_list, DATA)
    # 打包校验码
    return values_bytes

def sub_package_parse(self):
    pass

Sub_Package = type('Sub_Package', (object,),{'__slot__': tuple(v for v in sub_protocol.header.keys()),
                                             '__init__': package_init,
                                             'produce': sub_package_produce,
                                             'parse': sub_package_parse}
                   )

def complete_package(device_type,profile_id,serial_num,client_id,dest_addr,Data):
    if not isinstance(Data, bytes):
        raise Exception("arguements is not a bytes")

    sub_package = sub_protocol.produce_sub_package(len(Data), client_id, dest_addr, profile_id, serial_num, Data)
    package = protocol.produce_package(len(sub_package), device_type, profile_id, serial_num, client_id, sub_package)
    return package

def parse_package(package):
    protocol.get_header_content(package)
    pass

def detect_serial_port():
    port_list = find_serial_port_list()
    if port_list:
        for port in port_list:
            # TODO:输出格式化
            pass
    return port_list


def find_serial_port_list():
    return sorted(serial.tools.list_ports.comports())


@contextlib.contextmanager
def open_file(path, mode='r'):
    file_handler = open(path, mode)
    try:
        yield file_handler
    except IOError as why:
        print('File is not accessible')
    finally:
        file_handler.close()
        return


class ComReadWrite:
    def __init__(self):
        self.com = Com()
        self.protocol = _Protocol()
        self.current_sent_package = None
        self.expected_package_lv1 = None
        self.expected_package_lv2 = None
        self.expected_package_lv3 = None
        self.lost_package_list = []
        self.timeout_recv_package_list_1 = []
        self.timeout_recv_package_list_2 = []
        self.recv_data_process_flag = False
        self.send_data_process_flag = False
        self.next_send = 0

    def receive_data_with_protocol(self):
        ba = bytearray()
        state = 0b00000001
        temp_data_len = 0
        len_token = 0
        while self.com.com.inWaiting():
            x = self.com.receive_data()
            ch = ord(x)
            if state & 0b00000001 and 0xcd == ch:
                state <<= 1
                ba.append(ch)
            elif state & 0b00000010 and 0xab == ch:
                state <<= 1
                ba.append(ch)
            elif state & 0b00000100:
                state <<= 1
                ba.append(ch)
            elif state & 0b00001000:
                state <<= 1
                ba.append(ch)
            elif state & 0b00010000:
                state <<= 1
                len_token = ch
                ba.append(ch)
                temp_data_len = 0
            elif state & 0b00100000:
                ba.append(ch)
                temp_data_len += 1
                if temp_data_len == len_token + 7:
                    state <<= 0b01000000
            elif state & 0b01000000:
                ba.append(ch)
            else:
                state = 0b00000001
        return bytes(ba)

    def _send_data(self, data):
        self.com.send_data(data)

    def recv_data_process(self):
        if self.recv_data_process_flag:
            data = self.receive_data_with_protocol()
            serial_num = data.serial_getserialnum()

            if serial_num == self.expected_package_lv1:
                self.expected_package_lv1 = None
            elif serial_num == self.expected_package_lv2:
                self.expected_package_lv2 = None
                self.timeout_recv_package_list_1.append(serial_num)
            elif serial_num == self.expected_package_lv3:
                self.expected_package_lv3 = None
                self.timeout_recv_package_list_2.append(serial_num)
            else:
                pass

    def send_data_process(self, package):
        if self.send_data_process_flag:
            serial_num = package.get_seiralnum()
            self.current_sent_package = serial_num

            if self.expected_package_lv3:
                self.lost_package_list.append(self.expected_package_lv3)
            if self.expected_package_lv2:
                self.expected_package_lv3 = self.expected_package_lv2
            if self.expected_package_lv1:
                self.expected_package_lv2 = self.expected_package_lv1

            self._send_data(package)
            self.expected_package_lv1 = serial_num
            self.recv_data_process_flag = True

    def close(self):
        self.recv_data_process_flag = False
        self.send_data_process_flag = False
        error_filename = generate_filename('error')
        lag_filename = generate_filename('lag')
        with open_file(error_filename, 'w') as f:
            for info in self.lost_package_info:
                f.write(info)

        with open_file(lag_filename, 'w') as f:
            for info in self.lag_package_info:
                f.write(info)


def generate_filename(fragment):
    return fragment + generate_timestamp()


def generate_timestamp():
    return str(int(time.time()))


def setup():
    com_process = ComReadWrite()


def main():
    parser = argparse.ArgumentParser(description=f'TempSampling {__version__} - TUXIHUOZAIGONGCHENG',
                                     prog='TempSampling')

    parser.add_argument('-p',
                        '--ports',
                        help='Show serial ports list',
                        dest='ports',
                        action='store_true'
                        )
    parser.add_argument('-m',
                        dest='mapping',
                        help='Show all files and node mapping',
                        action='store_true'
                        )
    parser.add_argument('--serial_connect',
                        dest='serial_connect',
                        action='store_true',
                        help='Connect to serial'
                        )
    parser.add_argument('--server_start',
                        dest='server_start',
                        action='store_true',
                        help='Start Server'
                        )
    args = parser.parse_args()
    if args.ports:
        ports = find_serial_port_list()
        print(ports if ports else "there is no port")
        return
    if args.mapping:
        pass
        # TODO:补充映射文件节点的逻辑
        return
    if args.server_start:
        pass
        # TODO:服务器开始运行
    if args.serial_connect:
        pass
        # TODO:串口连接


if __name__ == '__main__':
    main()
