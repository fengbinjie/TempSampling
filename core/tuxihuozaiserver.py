import selectors
import socket
import serial
import socketserver
import os
import core
import core.util as util
import core.serial_with_protocol as Serial

_select = selectors.DefaultSelector()
keep_running = True

def get_serial():
    setting_dict = util.get_setting(os.path.join(core.PROJECT_DIR, 'setting.yml'))
    if os.name is 'nt':
        default_com = setting_dict['default_nt_com']
    elif os.name is 'posix':
        default_com = setting_dict['default_posix_com']
    else:
        raise Exception('unsupported system')
    default_baudrate = setting_dict['default_baudrate']
    return Serial.ReadWrite(default_com, default_baudrate, 0.01)

def get_nodes():
    return "get_nodes"

def get_ports():
    return "get_ports"

def get_current_temp(node):
    serial.send_to_node(node,0x10)

def process(connection, mask):
    global  keep_running
    client_address = connection.getpeername()
    data = connection.recv(1024).decode()
    if data:
        if data == 'get_nodes':
            msg = get_nodes()

        elif data == 'get_ports':
            msg = get_ports()
        connection.sendall(msg.encode())
    else:
        _select.unregister(connection)
        connection.close()

def accept(connection, mask):
    new_connection, addr = connection.accept()
    new_connection.setblocking(False)
    _select.register(new_connection,selectors.EVENT_READ, process)

def read(connection, mask):
    data = connection.read()
    #给
def write(connection, mask):


server_address = ('localhost', 10000)
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.setblocking(False)
server.bind(server_address)
server.listen(5)

_select.register(server, selectors.EVENT_READ, accept)

while keep_running:
    for key, mask in _select.select(timeout=0.5):
        callback = key.data
        callback(key.fileobj, mask)



