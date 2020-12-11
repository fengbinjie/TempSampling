import asyncio
import serial_asyncio
import core.serial_with_protocol as Serial
import struct
import json
import core.util as utils
import core.protocol as protocol

class Node:
    def __init__(self, mac_addr, led_file_path=None):
        self.mac_addr = mac_addr
        self.led_file_path = led_file_path

    # def get_led(self):
    #     return yaml.load(self.led_file_path, Loader=yaml.FullLoader)

def format_table(datasheet):
    """
    datasheet是一个列表，列表中的元素是列表，且长度相同，第一个元素是表的表头,其余都是数据
    二级列表中的每一个元素都是字符串
    :param datasheet:
    :return: none
    """
    # 表头
    table = utils.TableDisplay('No.', *datasheet[0])
    # 数据部分
    for index,row in enumerate(datasheet[1:],start=1):
        table.add_row(str(index), *row)
    return str(table)

def check(buf):
    xor_result = 0
    for v in buf:
        xor_result = xor_result ^ v
    return xor_result

def pack_check_num(value_bytes):
    # 打包校验码
    return struct.pack(f'<B', check(value_bytes))


class Tasks:
    nodes = {}

    def processed(self, line):
        cmd, arg, line = self.parse_line(line)
        try:
            func = getattr(self, 'do_' + cmd)
        except AttributeError:
            return self.default(cmd)
        return func(self, arg)

    def parse_line(self, line):
        line = line.strip()
        if not line:
            return None, None, line
        elif line[0] == '?':
            line = 'help ' + line[1:]
        elif line[0] == '!':
            if hasattr(self, 'do_shell'):
                line = 'shell ' + line[1:]
            else:
                return None, None, line
        i, n = 0, len(line)
        while i < n and line[i] in self.identchars: i = i + 1
        cmd, arg = line[:i], line[i:].strip()
        return cmd, arg, line

    @staticmethod
    def default():
        return f"there is no such a cmd,please check help"

    @classmethod
    def get_tasks(cls):
        tasks = [i for i in dir(cls) if i.startswith("do_")]
        return tasks


class RemoteTasks(Tasks):

    def __init__(self):
        super().__init__()
        self.seq_num = 0
        self.header_fixed_token = protocol.SERIAL_MSG_PROTOCOL['fixed_token']['default_value']
        self.sub_header_len = protocol.sub_header_len()
        self.counter = 0

    def do_list_nodes(self,seq_num):
        short_addr = 0x0000
        profile_id = 0xf0
        data = b''
        package = protocol.node_package(data,
                                        fixed_token=self.header_fixed_token,
                                        data_len=len(data) + self.sub_header_len,
                                        short_addr=short_addr,
                                        profile_id=profile_id,
                                        seq_num=seq_num,
                                        sub_seq_num=seq_num,
                                        )
        return package + pack_check_num(package)


    def process_list_nodes(self, receipt):
        # H:代表16位短地址，8B代表64位mac地址
        fmt = "H8B"
        # 该命令只有串口协议
        fmt_len = struct.calcsize(fmt)
        fmt = fmt * (len(receipt.data) // fmt_len)
        mixed_addr_tuple = struct.unpack(f'<{fmt}', receipt.data)

        receipt_data = []
        # 得到结果,并设置
        l_len = len(mixed_addr_tuple) // 9

        for index in range(l_len):
            # 短地址
            nwk_addr = mixed_addr_tuple[9 * index]
            # 长地址
            ext_addr = " ".join([str(v) for v in mixed_addr_tuple[index * 9 + 1:(index + 1) * 9]])
            # 有灯语
            receipt_data.append({
                "nwk_addr": nwk_addr,
                "ext_addr": ext_addr
                }
            )
            # led_sequence = node_led_mapping.get(ext_addr)
            # 生成节点对象
            receipt.data = receipt_data
            self.nodes[nwk_addr] = Node(ext_addr)

    def do_temp_start(self,seq_num):
        profile_id = 0x10
        data = b''
        big_p = b''
        for net in self.nodes:
            package = protocol.node_package(data,
                                            fixed_token=self.header_fixed_token,
                                            data_len=len(data) + self.sub_header_len,
                                            short_addr=net,
                                            profile_id=profile_id,
                                            seq_num=seq_num,
                                            sub_seq_num=seq_num,
                                            )
            package += pack_check_num(package)
            big_p += package
        self.counter = len(self.nodes)
        return big_p

    def process_temp_start(self,receipt):
        # 解包温度
        temperature = float(receipt.data)
        receipt.data = temperature
        self.counter -= 1
        if self.counter == 0:
            return "eof"

class LocalTasks(Tasks):

    def do_list_ports(self):
        ports = Serial.find_serial_port_list()
        if ports:
            datasheet = [("port\'s device", "port\'s description")]
            for port in ports:
                datasheet.append((port.device, port.description))
            return format_table(datasheet)
        else:
            print('there is no port')


class Output(asyncio.Protocol):
    self = None

    def __init__(self):
        super().__init__()
        self.shutdown = False
        self.next_write = None
        self.transport = None
        self.sock_output = None #todo 改成列表接收多个客户端连接
        Output.self = self
        self.tasks = RemoteTasks()
        self.waiting_future = None # 一个元祖 第一位为要等待任务结果序列号，第二位是处理该任务结果的回调函数
        self.seq_num = 0
        self.feedBackCount = 0
        self.msg_fragments = []
        self.remainder = 0
        self.eof = False

    def connection_made(self, transport):
        self.transport = transport
        print('port opened', transport)
        #data = b'\xcd\xab\x02\x00\x000\x7f\xcb\x7f'
        # self.transport.loop.call_soon(self.check_buffer)
        # transport.write(sent_data)  # Write serial data via transport
    def check_data(self, data):
        """
        该函数是检查数据是否完整，以及存储拼接断裂的数据
        :param data:
        :return:
        """
        if not self.remainder:
            length = data[2]
            self.remainder = length + 8 + 1 - len(data)
            if self.remainder == 0:
                return True, data
            else:
                self.msg_fragments.append(data)
        else:
            r = self.remainder - len(data)
            self.remainder = abs(r)
            if r > 0:
                self.msg_fragments.append(data)
            elif r == 0:
                self.msg_fragments.append(data)
                result = b''
                for i in self.msg_fragments:
                    result += i
                self.msg_fragments.clear()
                return True,result
            else:
                self.msg_fragments.append(data[0:r])
                result = b''
                for i in self.msg_fragments:
                    result += i
                self.msg_fragments.clear()
                self.msg_fragments.append(data[r:])
                return True,result
        return False,data

    def data_received(self, data):
        if self.shutdown:
            self.transport.close()

        f, d = self.check_data(data)
        print(f'time {self.transport.loop.time()}>data: received {d}')
        if f:
            # 当节点离线时没有数据发出也就无法调用该函数
            # 此处判断是否该回馈是否需要向客户端发送
            if check(d[:-1]) == d[-1]:
                # 创建回执
                if self.sock_output:
                    receipt = protocol.parse_package(d[:-1])
                    r = self.waiting_future[1](receipt) # 处理结果
                    # 给Future对象设置结果，sock等待future处将该结果发送给该客户端
                    if self.waiting_future and receipt.seq_num == self.waiting_future[0]:
                        response = {}
                        for attr in receipt.__slots__:
                            response[attr] = getattr(receipt,attr,None)
                        self.sock_output.notify_write(response)
                    # 当r存在代表该客户端的请求的所有结果都已发送完毕，向客户端发送结束符，结束此次任务
                    if r:
                        self.sock_output.notify_write("eof")

    def processed(self,data):
        try:
            # 获得任务，假如任务不存在返回默认任务
            func = getattr(self.tasks, "do_"+data["enquire"])
            call_back = getattr(self.tasks, "process_"+data["enquire"])
        except AttributeError:
            # 假如任务不存在发送默认提示函数
            self.sock_output.notify_write(self.tasks.default())
        else:
            # 任务存在,组装任务# 将任务发送给串口
            msg = func(seq_num=self.seq_num)
            self.notify_write(msg)
            # 设置要等待的future
            self.waiting_future = (self.seq_num,call_back)

    def notify_write(self,data):
        self.transport.write(data)

    def increase_seqnum(self):
        self.seq_num += 1
    def connection_lost(self, exc):
        global serial_transport
        serial_transport = None
        print('port closed')
        self.transport.loop.stop()

    def pause_writing(self):
        print('pause writing')
        print(self.transport.get_write_buffer_size())

    def resume_writing(self):
        print(self.transport.get_write_buffer_size())
        print('resume writing')

    def set_sock_transport(self, sock_transport):
        if sock_transport and isinstance(sock_transport,asyncio.Protocol):
            self.sock_output = sock_transport
        return True if self.sock_output else False

    def get_self_transport(self):
        return self.transport if self.transport else None

class SockOutput(asyncio.Protocol):
    def __init__(self):
        super().__init__()
        self.shutdown = False
        self.loop = asyncio.get_event_loop()
        self.tasks = LocalTasks()
        self.transport = None
        self.serial_output = None

    def connection_made(self, transport):
        self.transport = transport
        print('socket opened', transport)
        self.serial_output = Output.self
        if not self.serial_output:
            raise Exception("连接失效")
        else:
            # 给串口output设置sock_output
            if not self.serial_output.set_sock_transport(sock_transport=self):
                raise Exception("连接失效")
                #向客户端 发送错误提示信息
        # 获得连接成功后向客户端发送注册的任务函数列表
        feedback = {"feedback":[*RemoteTasks.get_tasks(),*LocalTasks.get_tasks()]}
        self.transport.write(json.dumps(feedback).encode())
        # loop.call_soon(self.check_buffer)
        #检查串口是否连接
        #没有连接，关闭自身由supervisor重启


    def preprocess(self, data):
        pass
    def postprocess(self, data):
        pass

    def notify_write(self,data):
        data = json.dumps(data).encode()
        self.transport.write(data)

    def notify_cancel(self):
        # 取消正在等待的命令
        self.serial_output.waiting_future = None

    def data_received(self, data):
        if self.shutdown:
            self.transport.close()
        data = json.loads(data.decode())
        # 是否是本地任务假如是直接执行获得结果
        func = getattr(self.tasks, 'do_'+data["enquire"], False)
        if func:
            result = func()
            self.notify_write(result)
        else: # 否则由串口output处理
            # 改用回调方法
            # 建立一个未来要接受的结果
            self.serial_output.processed(data)
            # 等待结果返回



    def connection_lost(self, exc):
        print('port closed')
        # 将serial_output的sock_output属性设置为空
        self.serial_output.sock_output = None
        super().connection_lost(None)


    def pause_writing(self):
        print('pause writing')
        print(self.transport.get_write_buffer_size())

    def resume_writing(self):
        print(self.transport.get_write_buffer_size())
        print('resume writing')

    def get_self_transport(self):
        return self.transport if self.transport else None

loop = asyncio.get_event_loop()
factory = loop.create_server(SockOutput, 'localhost', 10000)
coro = serial_asyncio.create_serial_connection(loop, Output, '/dev/ttyAMA0', baudrate=115200)
loop.create_task(coro)
loop.create_task(factory)
loop.run_forever()
print("should never come here")
loop.close()