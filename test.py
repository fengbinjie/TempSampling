import serial
import selectors
import asyncio
import threading


s = selectors.DefaultSelector()
s1 = serial.Serial('/dev/pts/1',115200)
s1.write(b'hello world')
def process(com,mask):
    data = b''
    while com.inWaiting():
        data += com.read()
    if data:
        print(data)

s.register(s1,selectors.EVENT_READ,process)

while True:
    for key, mask in s.select(timeout=0.01):
        callback = key.data
        callback(key.fileobj, mask)
# 发送消息问询然后获得当前时间
# 获得间隔时间 interval
# 得到下次问询的时间 = 当前时间+间隔时间
# 然后获得回应有消息可读
# 获得当前时间，与预设时间比较
# 分两种情况
# 1.到了下次问询时间仍旧有消息未收到
# 2.到了下次问询时间消息全部收到
# 查看预设时间
# 在预设时间预设时间收到消息