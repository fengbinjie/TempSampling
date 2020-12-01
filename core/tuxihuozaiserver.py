from xmlrpc.server import SimpleXMLRPCServer

server = SimpleXMLRPCServer(('localhost', 9000),logRequests=True)

def get_nodes():
    return "get_nodes"
def get_ports():
    return "get_ports"
server.register_function(get_nodes,'list.nodes')
server.register_function(get_ports,'list.ports')

try:
    print("Use Control-C to exit")
    server.serve_forever()
except KeyboardInterrupt:
    print("Exiting")
