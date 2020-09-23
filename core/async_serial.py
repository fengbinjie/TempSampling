import serial
import serial.tools.list_ports
import argparse

__title__ = 'tempsampling'
__version__ = '0.1.0'
__build__ = 0x000100
__author__ = 'Binjie Feng'
__license__ = 'ISC'
__copyright__ = 'Copyright 2020 Binjie Feng'


def detect_serial_port():
    port_list = find_serial_port_list()
    if port_list:
        for port in port_list:
            # TODO:输出格式化
            pass
    return port_list


def find_serial_port_list():
    return sorted(serial.tools.list_ports.comports())

class Com:
    def __init__(self, url, baudrate):
        if url in find_serial_port_list():
            self.com = serial.Serial()
        else:
            raise Exception("there is no such port")
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

    def receive_data(self):
        try:
            length = max(1, min(2048, self.com.in_waiting))
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