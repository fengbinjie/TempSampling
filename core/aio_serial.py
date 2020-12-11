import asyncio
import serial_asyncio
import core.serial_with_protocol as Serial
import struct
import json
import core.util as utils
import core.protocol as protocol


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

def set_nodes(receipt):
    # H:代表16位短地址，8B代表64位mac地址
    fmt = "H8B"
    # 该命令只有串口协议
    fmt_len = struct.calcsize(fmt)
    fmt = fmt * (len(receipt.data) // fmt_len)
    mixed_addr_tuple = struct.unpack(f'<{fmt}', receipt.data)

    receipt.data = mixed_addr_tuple


class Tasks:

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
        return f"there is no such a cmd"


class RemoteTasks(Tasks):
    register_func_list = ['list_nodes']
    def __init__(self):
        super().__init__()
        self.seq_num = 0
        self.header_fixed_token = protocol.SERIAL_MSG_PROTOCOL['fixed_token']['default_value']
        self.sub_header_len = protocol.sub_header_len()

    def list_nodes(self,seq_num):
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
        # 得到结果,并设置

class LocalTasks(Tasks):
    register_func_list = ['list_ports']

    def list_ports(self):
        ports = Serial.find_serial_port_list()
        if ports:
            datasheet = [("port\'s device", "port\'s description")]
            for port in ports:
                datasheet.append((port.device, port.description))
            return format_table(datasheet)
        else:
            print('there is no port')


def process(command):
    pass

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
        self.waiting_future = None
        self.result_process = None
        self.seq_num = 0
        self.feedBackCount = 0

    def connection_made(self, transport):
        self.transport = transport
        print('port opened', transport)
        #data = b'\xcd\xab\x02\x00\x000\x7f\xcb\x7f'
        # self.transport.loop.call_soon(self.check_buffer)
        # transport.write(sent_data)  # Write serial data via transport

    def data_received(self, data):
        if self.shutdown:
            self.transport.close()
        # 当节点离线时没有数据发出也就无法调用该函数
        print(f'time { self.transport.loop.time() }>data: received {data}')
        # 此处判断是否该回馈是否需要向客户端发送
        if check(data[:-1]) == data[-1]:
            # 创建回执
            if self.sock_output:
                receipt = protocol.parse_package(data[:-1])
                self.result_process[1](receipt)
                # 给Future对象设置结果，sock等待future处将该结果发送给该客户端
                if self.waiting_future is not None and receipt.seq_num == self.waiting_future:
                    response = {}
                    for attr in receipt.__slots__:
                        response[attr] = getattr(receipt,attr,None)
                    self.sock_output.notify_write(response)
                self.feedBackCount += 1

    def processed(self,data):
        try:
            # 获得任务，假如任务不存在返回默认任务
            func = getattr(self.tasks, data["enquire"])
        except AttributeError:
            # 假如任务不存在发送默认提示函数
            self.sock_output.notify_write(self.tasks.default())
        else:
            # 任务存在,组装任务# 将任务发送给串口
            self.notify_write(func(seq_num=self.seq_num))
            # 设置要等待的future
            self.waiting_future = self.seq_num

    def notify_write(self,data):
        self.result_process = (self.seq_num,set_nodes)
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
        feedback = {"feedback":[*RemoteTasks.register_func_list,*LocalTasks.register_func_list]}
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
        func = getattr(self.tasks, data["enquire"], False)
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