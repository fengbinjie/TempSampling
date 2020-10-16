import contextlib
import time
import serial
import serial.tools.list_ports
import core.protocol as protocol
import struct
import queue

STATENUM = protocol.protocol.header_fmt_size
v = protocol.BASIC_PROTOCOL_PROPERTY["fixed_token"]["default_value"]
fmt = f'{protocol.ENDIAN}{protocol.BASIC_PROTOCOL_PROPERTY["fixed_token"]["fmt"]}'
fixed_state = struct.pack(fmt, v)

firstState = fixed_state[0]
secondState = fixed_state[1]

# 状态机

class ReadWrite:
    def __init__(self, url, baud_rate, interval):
        self.com = serial.Serial(url, baud_rate)
        self.receiveProgressStop = False
        self.sendProgressStop = False
        self.feedBackCount = 0
        self.sendCount = 0
        self.read_interval = interval
        self.read_buf = queue.Queue()
        # self.serialNumList = []
        # self.currentSentPacket = None
        # self.lostPacketList = []
        # self.delayPacketList = []

    def get_noFeedBackCount(self):
        return self.sendCount - self.feedBackCount

    def get_feedBackCount(self):
        return self.feedBackCount

    def get_sendCount(self):
        return self.sendCount

    def recv_data_process(self):
        ba = bytearray()
        temp_data_len = 0
        len_token = 0
        while not self.receiveProgressStop:
            ba.clear()
            state = 0b00000001
            while self.com.inWaiting():
                # TODO: 去掉协议
                # TODO: 创建一个类似zigbee中mtOSALSerialData_t的类
                x = self.com.read(1)
                ch = ord(x)
                if state & 0b00000001:
                    # 标志位1
                    if 0xcd == ch:
                        state <<= 1
                        ba.append(ch)
                elif state & 0b00000010:
                    # 标志位2
                    if 0xab == ch:
                        state <<= 1
                        ba.append(ch)
                elif state & 0b00000100:
                    # 得到长度
                    state <<= 1
                    len_token = ch
                    ba.append(ch)
                    temp_data_len = 0
                elif state & 0b00001000:
                    # 写入数据
                    ba.append(ch)
                    temp_data_len += 1
                    if temp_data_len == len_token + 4:
                        state <<= 1
                elif state & 0b00010000:
                    # 验证校验码正确
                    if ord(pack_check_num(ba)) == ch:
                        self.feedBackCount += 1
                        # TODO:转化为多字段的元祖，而不是现有的包
                        fields = protocol.parse_package(bytes(ba))
                        yield fields
                        # self.read_buf.put(fields)
                    else:
                        break
                else:
                    state = 0b00000001
            time.sleep(self.read_interval)

    def pop_data(self):
        return self.read_buf.get()

    def send_data(self, node_addr, profile_id, serial_num, data=b''):

        if self.com.is_open:
            # 打包
            package = protocol.complete_package(node_addr, profile_id, serial_num, data)
            # 加上校验值
            package = package + pack_check_num(package)
            try:
                send_len = self.com.write(package)
            except Exception as why:
                raise why
            else:
                self.sendCount += 1
                return send_len

    def close(self):
        self.receiveProgressStop = False
        self.sendProgressStop = False
        # error_filename = generate_filename('error')
        # lag_filename = generate_filename('lag')
        # with open_file(error_filename, 'w') as f:
        #     for info in self.lostPacketList:
        #         f.write(info)
        #
        # with open_file(lag_filename, 'w') as f:
        #     for info in self.delayPacketList:
        #         f.write(info)
        if self.com.is_open:
            try:
                self.com.close()
            except Exception as why:
                raise why


def detect_serial_port():
    port_list = find_serial_port_list()
    if port_list:
        for port in port_list:
            # TODO:输出格式化
            pass
    return port_list


def find_serial_port_list():
    return [port.device for port in sorted(serial.tools.list_ports.comports())]


@contextlib.contextmanager
def open_file(path, mode='r'):
    file_handler = open(path, mode)
    try:
        yield file_handler
    except IOError as why:
        print('File is not accessible')
    finally:
        file_handler.close()
        return


def generate_filename(fragment):
    return fragment + generate_timestamp()


def generate_timestamp():
    return str(int(time.time()))


def pack_check_num(value_bytes):
    # 打包校验码
    return struct.pack(f'<B', check(value_bytes))


def check(buf):
    xor_result = 0
    for v in buf:
        xor_result = xor_result ^ v
    return xor_result


if __name__ == '__main__':
    import threading
    rw = ReadWrite("COM8", 115200, 0.1)
    num = 0
    t1 = threading.Thread(target=rw.recv_data_process, args=())
    t1.setDaemon(True)
    t1.start()
    while True:
        rw.send_data(node_addr=0x4285, profile_id=0x10, serial_num=127)
        time.sleep(1)
        print(num, rw.read_buf.get())
        num += 1



