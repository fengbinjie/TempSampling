from xmlrpc.server import SimpleXMLRPCServer

server = SimpleXMLRPCServer(('localhost', 9000),logRequests=True)

def get_serial():
    return "get_serial"

server.register_function(get_serial)

try:
    print("Use Control-C to exit")
    server.serve_forever()
except KeyboardInterrupt:
    print("Exiting")
