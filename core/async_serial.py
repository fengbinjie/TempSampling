import contextlib
import time
import serial
import serial.tools.list_ports


class Com:
    def __init__(self):
        self.com = serial.Serial()
        self.receiveProgressStop = False
        self.sendProgressStop = False
        self.noFeedBackCount = 0
        self.feedBackCount = 0
        self.sendCount = 0

    def get_noFeedBackCount(self):
        return self.sendCount - self.feedBackCount

    def get_feedBackCount(self):
        return self.feedBackCount

    def get_sendCount(self):
        return self.sendCount

    def receive_data(self, length_set=1):
        while not self.receiveProgressStop:
            length = length_set if length_set else max(1, min(2048, self.com.in_waiting))
            try:
                _bytes = self.com.read(length)
            except Exception as why:
                raise why
            else:
                self.feedBackCount += 1
                return _bytes

    def send_data(self, data):
        if self.com.is_open and data != -1:
            return
        try:
            self.com.write(data)
        except Exception as why:
            raise why
        else:
            self.sendCount += 1

    def close(self):
        self.receiveProgressStop = True
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
    return sorted(serial.tools.list_ports.comports())


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

class myaio_serial:
    def __init__(self):
        self.reader = None
        self.writer = None
        self.async_recv_msg_buf = None
        self.async_send_msg_buf = None

    async def initial(self, url, baudrate, async_recv_msg_buf, async_send_msg_buf):
        self.reader, self.writer = await serial_asyncio.open_serial_connection(url=url, baudrate=baudrate)
        self.async_recv_msg_buf = async_recv_msg_buf
        self.async_send_msg_buf = async_send_msg_buf

    async def send(self):
        while True:
            # 每当发送队列中有消息时就将其发送
            msg = await self.async_send_msg_buf.get()
            # 取出消息添加校验码
            msg = msg + pack_check_num(msg)
            self.writer.write(msg)

    async def recv(self):
        protocol = {'sop_state': 0x00,
                     'check_state1': 0x01,
                     'check_state2': 0x02,
                     'keep_state1': 0x03,
                     'keep_state2': 0x04,
                     'len_state': 0x05,
                     'data_state': 0x06,
                     'fcs_state': 0x07,
                    }
        state = 0x00
        ab_mark = 171
        cd_mark = 205
        temp_data_len = 0
        len_token = 0
        # 每当有消息进入时就接收直到收到停止符号并将整条消息存入
        while True:
            ba = bytearray()
            while True:
                x = await self.reader.read(1)
                ch = ord(x)
                if state == protocol['sop_state']:
                    state = protocol['check_state1']
                if state == protocol['check_state1']:
                    if cd_mark == ch:
                        state = protocol['check_state2']
                        ba.append(ch)
                    else:
                        state = protocol['sop_state']
                elif state == protocol['check_state2']:
                    if ab_mark == ch:
                        state = protocol['keep_state1']
                        ba.append(ch)
                    else:
                        state = protocol['sop_state']
                elif state == protocol['keep_state1']:
                    state = protocol['keep_state2']
                    ba.append(ch)
                elif state == protocol['keep_state2']:
                    state = protocol['len_state']
                    ba.append(ch)
                elif state == protocol['len_state']:
                    len_token = ch
                    ba.append(ch)
                    state = protocol['data_state']
                    temp_data_len = 0
                elif state == protocol['data_state']:
                    ba.append(ch)
                    temp_data_len += 1
                    if temp_data_len == len_token + 7:
                        state = protocol['fcs_state']
                elif state == protocol['fcs_state']:  # 校验码验证
                    if not ch == pack_check_num(ba):
                        # 失败清除数据，校验码不添加进包中
                        ba.clear()
                    break
            state = 0x00
            await self.process(ba)

class ComReadWrite:
    def __init__(self, url, baudrate):
        self.com = Com(url=url, baudrate=115200)
        self.current_sent_package = None
        self.expected_package_lv1 = None
        self.expected_package_lv2 = None
        self.expected_package_lv3 = None
        self.lost_package_list = []
        self.timeout_recv_package_list_1 = []
        self.timeout_recv_package_list_2 = []
        self.recv_data_process_flag = False
        self.send_data_process_flag = False
        self.next_send = 0

    def receive_data_with_protocol(self):
        ba = bytearray()
        state = 0b00000001
        temp_data_len = 0
        len_token = 0
        while self.com.com.inWaiting():
            # TODO: 去掉协议
            x = self.com.receive_data()
            ch = ord(x)
            if state & 0b00000001 and 0xcd == ch:
                state <<= 1
                ba.append(ch)
            elif state & 0b00000010 and 0xab == ch:
                state <<= 1
                ba.append(ch)
            elif state & 0b00000100:
                state <<= 1
                ba.append(ch)
            elif state & 0b00001000:
                state <<= 1
                ba.append(ch)
            elif state & 0b00010000:
                state <<= 1
                len_token = ch
                ba.append(ch)
                temp_data_len = 0
            elif state & 0b00100000:
                ba.append(ch)
                temp_data_len += 1
                if temp_data_len == len_token + 7:
                    state <<= 0b01000000
            elif state & 0b01000000:
                ba.append(ch)
            else:
                state = 0b00000001
        return bytes(ba)

    def _send_data(self, data):
        self.com.send_data(data)

    def recv_data_process(self):
        if self.recv_data_process_flag:
            data = self.receive_data_with_protocol()
            serial_num = data.serial_getserialnum()

            if serial_num == self.expected_package_lv1:
                self.expected_package_lv1 = None
            elif serial_num == self.expected_package_lv2:
                self.expected_package_lv2 = None
                self.timeout_recv_package_list_1.append(serial_num)
            elif serial_num == self.expected_package_lv3:
                self.expected_package_lv3 = None
                self.timeout_recv_package_list_2.append(serial_num)
            else:
                pass

    def send_data_process(self, package):
        if self.send_data_process_flag:
            serial_num = package.get_seiralnum()
            self.current_sent_package = serial_num

            if self.expected_package_lv3:
                self.lost_package_list.append(self.expected_package_lv3)
            if self.expected_package_lv2:
                self.expected_package_lv3 = self.expected_package_lv2
            if self.expected_package_lv1:
                self.expected_package_lv2 = self.expected_package_lv1

            self._send_data(package)
            self.expected_package_lv1 = serial_num
            self.recv_data_process_flag = True

    def close(self):
        self.recv_data_process_flag = False
        self.send_data_process_flag = False
        error_filename = generate_filename('error')
        lag_filename = generate_filename('lag')
        with open_file(error_filename, 'w') as f:
            for info in self.lost_package_info:
                f.write(info)

        with open_file(lag_filename, 'w') as f:
            for info in self.lag_package_info:
                f.write(info)


def generate_filename(fragment):
    return fragment + generate_timestamp()


def generate_timestamp():
    return str(int(time.time()))


def setup():
    com_process = ComReadWrite()





if __name__ == '__main__':
    main()
