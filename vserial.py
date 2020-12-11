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
        com.write(b"\xcd\xab\x02\xf0\x00\x00\x00\x00\x00\x00\x94")

s.register(s2,selectors.EVENT_READ,process)

while True:
    for key, mask in s.select(timeout=0.01):
        callback = key.data
        callback(key.fileobj, mask)