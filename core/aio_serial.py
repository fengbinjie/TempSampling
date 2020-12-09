import asyncio
import serial_asyncio
import core.serial_with_protocol as Serial
import struct
import json
import core.util as utils

def format_table(datasheet):
    """
    datasheet是一个列表，列表中的元素是列表，且长度相同，第一个元素是表的表头,其余都是数据
    二级列表中的每一个元素都是字符串
    :param datasheet:
    :return: none
    """
    # 表头
    table = utils.TableDisplay('No.', *datasheet[0])
    no = 1
    # 数据部分
    for row in datasheet[1:]:
        table.add_row(str(no), *row)
        no += 1
    return str(table)


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
    def default(cmd):
        return f"there is no {cmd}"


class RemoteTasks(Tasks):
    register_func_list = []

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
        self.sock_transport = None
        Output.self = self

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

        # 需要发送到串口的任务在此处回馈给客户端
        if self.sock_transport:
            self.sock_transport.write(data)


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
        if sock_transport and isinstance(sock_transport,asyncio.Transport):
            self.sock_transport = sock_transport
        return True if self.sock_transport else False

    def get_self_transport(self):
        return self.transport if self.transport else None

class SockOutput(asyncio.Protocol):
    def __init__(self):
        super().__init__()
        self.shutdown = False
        self.loop = asyncio.get_event_loop()
        self.r_tasks = RemoteTasks()
        self.l_tasks = LocalTasks()
        self.transport = None
        self.serial_transport = None

    def connection_made(self, transport):
        self.transport = transport
        print('socket opened', transport)
        self.serial_transport = Output.self.get_self_transport()
        if not self.serial_transport:
            raise Exception("连接失效")
        else:
            if not Output.self.set_sock_transport(self.transport):
                raise Exception("连接失效")
                #向客户端 发送错误提示信息
        # 获得连接成功后向客户端发送注册的任务函数列表
        feedback = {"feedback":[*self.l_tasks.register_func_list,*self.r_tasks.register_func_list]}
        self.transport.write(json.dumps(feedback).encode())
        # loop.call_soon(self.check_buffer)
        #检查串口是否连接
        #没有连接，关闭自身由supervisor重启

    def processed(self, data):
        data = json.loads(data.decode())
        need = False
        if data["enquire"] in self.l_tasks.register_func_list:
            func = getattr(self.l_tasks, data["enquire"])
        elif data["enquire"] in self.r_tasks.register_func_list:
            func = getattr(self.r_tasks, data["enquire"])
            need = True
        else:
            result = Tasks.default(*data["enquire"])
            return result, need
        if data["args"]:
            result = func(data["args"])
        else:
           result = func()
        return result, need

    def preprocess(self, data):
        pass
    def postprocess(self, data):
        pass

    def data_received(self, data):
        if self.shutdown:
            self.transport.close()
        result, need = self.processed(data) or "没有结果"
        # 判断是否需要向串口写
        if self.serial_transport and need:
            self.serial_transport.write(result)
            # # 等待结果返回
            # future = self.loop.create_future()
            # self.loop.create_task()
            # await future
            # result = future.result()
        # 无需发送串口直接在此处回馈给客户端
        else:
            self.transport.write(result.encode())

    def connection_lost(self, exc):
        global sock_transport
        print('port closed')
        sock_transport = None
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
coro = serial_asyncio.create_serial_connection(loop, Output, '/dev/pts/1', baudrate=115200)
loop.create_task(coro)
loop.create_task(factory)
loop.run_forever()
print("should never come here")
loop.close()