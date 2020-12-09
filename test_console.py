import socket
import time
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect(('localhost',10000))

s.send("word".encode())
print(s.recv(1024).decode())
while True:
    s.send("heelo".encode())
    time.sleep(1)
    print(s.recv(1024).decode())