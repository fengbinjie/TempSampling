import asyncio
import serial_asyncio
import core.serial_with_protocol as Serial
import json
import core.tasks2 as tasks
import core.util as util
import core.protocol as protocol

class Output(asyncio.Protocol):
    self = None

    def __init__(self):
        super().__init__()
        self.shutdown = False
        self.transport = None
        self.sock_output = None #todo 改成列表接收多个客户端连接
        Output.self = self
        self.seq_num = 0
        self.msg_fragments = []
        self.task_list = []
        self.task_seqnum_mapping = {}
        self.remainder = 0
        self.sent_msg_buffer = list()

    def get_seq_num(self):
        self.seq_num += 1
        return self.seq_num


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
            if util.check(d[:-1]) == d[-1]:
                # 创建回执
                receipt = protocol.parse_package(d[:-1])
                task = self.task_seqnum_mapping.pop(receipt.seq_num, None)
                # 找到相应的处理函数
                if task:
                    if self.sock_output:
                        task.socket_write(receipt)
                    else:
                        result = task.process(receipt)
                        print(result)


    def writable(self):
        if self.sent_msg_buffer:
            return True
        else:
            return False

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
        # feedback = {"feedback":[*RemoteTasks.get_tasks(),*LocalTasks.get_tasks()]}
        # self.transport.write(json.dumps(feedback).encode())
        # loop.call_soon(self.check_buffer)
        #检查串口是否连接
        #没有连接，关闭自身由supervisor重启


    def preprocess(self, data):
        pass
    def postprocess(self, data):
        pass

    def notify_write(self, response):
        response = json.dumps(response).encode()
        self.transport.write(response)

    def data_received(self, require):
        if self.shutdown:
            self.transport.close()
        require = json.loads(require.decode())
        # 获取任务
        task = getattr(tasks, f'{require["command"]}_{require["sub_command"]}_task', None)
        # 获取任务的参数
        args = require["args"]
        if task:
            # 解析参数
            pass
            # 替换或取消已存在的任务。暂定为取消
            for existed_task_obj in self.serial_output.task_list:
                if isinstance(existed_task_obj,task):
                    self.notify_write("该任务正在运行")
                    return
            new_task = task(self.serial_output,self)
            self.serial_output.task_list.append(new_task)
            new_task.start(**args)



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