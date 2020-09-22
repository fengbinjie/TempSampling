import serial
import serial.tools.list_ports


def find_serial_port_list():
    return sorted(serial.tools.list_ports.comports())

