import serial
import serial.tools.list_ports
import argparse
import yaml
import time
import contextlib
import os


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
                bytes = self.com.read(length)
            except Exception as why:
                raise why
            else:
                self.feedBackCount += 1
                return bytes

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

class Protocol:
    _instance = None
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        self.fixed_token =(1,2,0xabcd)
        self.reservered_token = (2,2,0x0000)
        self.D_LEN = [3,1,None]
        self.device_type = [4,1,None]
        self.message_id = [5,2,None]
        self.serial_number = [6,2,None]
        self.client_id = [7,2,None]
        self.DATA = [8,None,None]
        self.CHECK = [9,1,None]
        pass


    @staticmethod
    def _get_protocol_from_file(path):
        with open_file(path) as f:
            try:
                protocol_dict = yaml.load(f)
            except yaml.YAMLError as why:
                print("error format")
            else:
                return protocol_dict

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
        self.protocol = Protocol()
        self.lost_package_info = []
        self.lag_package_info = []
        self.max_lag_pack_len = 3
        self.ready_recv_pack_info = None
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
                raise Exception("串口数据接收错误")
        return bytes(ba)

    def _send_data(self, data):
        self.com.send_data(data)

    def recv_data_process(self):
        if self.recv_data_process_flag:
            data = self.receive_data_with_protocol()
            serial_num = data.serial_getserialnum()
            if serial_num == self.ready_recv_pack_info:
                self._update_recv_pack_info(None)
            elif serial_num in self.lag_package_info:
                self.lag_package_info.remove(serial_num)
            else:
                self.lost_package_info.append(serial_num)


    def send_data_process(self, package):
        if self.send_data_process_flag:
            if self.ready_recv_pack_info:
                if self.max_lag_pack_len <= len(self.lag_package_info):
                    last_pack_info = self.lag_package_info.pop(-1)
                    self.lost_package_info.append(last_pack_info)
                else:
                    self.lag_package_info.append(self.ready_recv_pack_info)
            self._send_data(package)
            self._update_recv_pack_info(package.get_seiralnum())

            self.recv_data_process_flag = True

    def _update_recv_pack_info(self, new_pack_info):
        self.ready_recv_pack_info = new_pack_info

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
    parser = argparse.ArgumentParser(description=f'TempSampling {__version__} - TUXIHUOZAIGONGCHENG', prog='TempSampling')

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