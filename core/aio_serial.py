import asyncio
import serial_asyncio
import struct


def pack_check_num(value_bytes):
    # 打包校验码
    return struct.pack(f'<B', check(value_bytes))


def check(buf):
    xor_result = 0
    for v in buf:
        xor_result = xor_result ^ v
    return xor_result

sent_data = b'\xcd\xab\x02\x85B\x10\x7f\xcb\x7f'
class Output(asyncio.Protocol):
    def __init__(self):
        super().__init__()
        self.shutdown = False

    def connection_made(self, transport):
        self.transport = transport
        print('port opened', transport)
        #data = b'\xcd\xab\x02\x00\x000\x7f\xcb\x7f'

        transport.write(sent_data)  # Write serial data via transport

    def data_received(self, data):
        if self.shutdown:
            self.transport.close()
        print(f'time { self.transport.loop.time() }>data: received {data}')
        self.transport.loop.call_later(1,self.transport.write, sent_data)
        self.shutdown = True

    def connection_lost(self, exc):
        print('port closed')
        self.transport.loop.stop()

    def pause_writing(self):
        print('pause writing')
        print(self.transport.get_write_buffer_size())

    def resume_writing(self):
        print(self.transport.get_write_buffer_size())
        print('resume writing')


loop = asyncio.get_event_loop()
coro = serial_asyncio.create_serial_connection(loop, Output, '/dev/pts/1', baudrate=115200)
loop.run_until_complete(coro)
print("should be never come here")
loop.close()