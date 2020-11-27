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


class Output(asyncio.Protocol):
    def connection_made(self, transport):
        self.transport = transport
        print('port opened', transport)

        transport.serial.rts = False  # You can manipulate Serial object via transport
        #data = b'\xcd\xab\x02\x00\x000\x7f\xcb\x7f'
        data = b'\xcd\xab\x02\x85B\x10\x7f\xcb\x7f'
        transport.write(data+pack_check_num(data))  # Write serial data via transport

    def data_received(self, data):
        print('data received', data)
        self.transport.close()

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
coro = serial_asyncio.create_serial_connection(loop, Output, 'COM8', baudrate=115200)
loop.run_until_complete(coro)
loop.run_forever()
loop.close()