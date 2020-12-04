import serial
import selectors
s = selectors.DefaultSelector()
s2 = serial.Serial('/dev/pts/2',115200)

def process(com,mask):
    data = b''
    while com.inWaiting():
        data += com.read()
    if data:
        print(data)
        com.write(data)

s.register(s2,selectors.EVENT_READ,process)

while True:
    for key, mask in s.select(timeout=0.01):
        callback = key.data
        callback(key.fileobj, mask)