import serial
import serial.tools.list_ports
import argparse

__title__ = 'tempsampling'
__version__ = '0.1.0'
__build__ = 0x000100
__author__ = 'Binjie Feng'
__license__ = 'ISC'
__copyright__ = 'Copyright 2020 Binjie Feng'

def find_serial_port_list():
    return sorted(serial.tools.list_ports.comports())

def main():
    parser = argparse.ArgumentParser(description=f'TempSampling {__version__} - TUXIHUOZAIGONGCHENG', prog='TempSampling')

    parser.add_argument('--ports',
                        help='show serial ports list',
                        default=True)

    args = parser.parse_args()
    if args.ports:
        print(find_serial_port_list())
    else:
        print('there is no port')

if __name__ == '__main__':
    main()