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

