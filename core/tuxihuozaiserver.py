import selectors
import socket

_select = selectors.DefaultSelector()
keep_running = True

def get_nodes():
    return "get_nodes"
def get_ports():
    return "get_ports"

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



