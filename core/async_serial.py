import serial
import serial.tools.list_ports


def find_serial_port_list():
    return list(serial.tools.list_ports.comports())


