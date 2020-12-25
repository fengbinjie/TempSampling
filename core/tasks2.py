import serial.tools.list_ports
import core.util as utils
import core.protocol as protocol
import struct

class Node:
    def __init__(self, mac_addr, led_file_path=None):
        self.mac_addr = mac_addr
        self.led_file_path = led_file_path

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

#任务自动的向
class Task:
    nodes = {}
    header = protocol.SERIAL_MSG_PROTOCOL['fixed_token']['default_value']
    header_len = protocol.sub_header_len()
    def __init__(self, _serial,_socket,**kwargs):
        self._serial = _serial
        self._socket = _socket
        self.times = 1     # 执行次数，None无限次，其余都是非负数整型
        self.interval = 2  # 任务执行时间间隔
        self.fail_handler = None
        self.task_id = None
        self.cur_seq_num = None
        self.aim = False
        self.finished = False
        self.response = {
            "task": self.__class__.__name__[:-5],
            "source": self._socket.server_info,
            "dest": self._socket.peer_info,
            "date": None,
            "data": None,
            "eof": True
        }
        if kwargs:
            for args, value in kwargs.items():
                setattr(self,args,value)

    def start(self):
        self.serial_write()

    def fill_response(self, data, eof=True):
        import time
        assert isinstance(data, dict)
        self.response["data"] = data
        self.response["date"] = time.asctime()
        self.response["eof"] = eof

    def writable(self):
        if self.times is not None:
            if self.times == 0:
                return False
        return True

    def serial_write(self):
        if self.times:
            self.times -= 1
        seq_num = self._serial.get_seq_num()
        # 目的是本网关的任务，result = None
        result = self.produce(seq_num)
        if result: # 目的地是节点和协调器的任务
            self.fail_handler = self._serial.transport.loop.call_later(3, self.fail)
            self._serial.notify_write(result)
            print(f'time> {self._serial.transport.loop.time()} {result}')
            # 将该任务存入任务序列号映射中，等待收到回执。根据序列号查找对应的任务来处理回执
            self._serial.task_seqnum_mapping[seq_num] = self
            self.cur_seq_num = seq_num # 只有需要写入串口的任务才会赋予cur_seq_num
        else:
            # 目的地是本网关的任务，直接处理发送回客户端
            self.socket_write(None)


    def socket_write(self, receipt):
        result = self.process(receipt)
        if self._socket:
            self.fill_response(data=result,eof=self.finished)
            self._socket.notify_write(self.response)
        if self.finished:
            # 从任务列表中移除
            self._serial.task_list.remove(self)

    def process(self,receipt):
        # 取消检查函数
        if self.fail_handler:
            self.fail_handler.cancel()
        result = self.parse(receipt)
        if self.aim and self.writable():
            self._serial.transport.loop.call_later(self.interval,self.serial_write)
        else:
            self.finished = True
        return result

    def produce(self, seq_num):
        #返回空字符串代表该任务无需转交到网关处完成，本地就可以完成
        raise NotImplementedError

    def parse(self,receipt):
        raise NotImplementedError

    def fail(self):
        if self.writable():
            i = self.interval - 1
            if i <= 0:
                self.serial_write()
            else:
                self._serial.transport.loop.call_later(i, self.serial_write)
        else:
            # 在任务和流水号映射中删除当前失败命令的流水号
            self.finished = True
            self._serial.task_list.remove(self)
            self.process_fail()
        # 在任务和流水号映射中删除当前失败命令的流水号
        self._serial.task_seqnum_mapping.pop(self.cur_seq_num)

    def process_fail(self):
        raise NotImplementedError

class list_ports_task(Task):
    def __init__(self, _serial,_socket,**kwargs):
        super().__init__(_serial,_socket,**kwargs)
        self.task_id = None

    def produce(self, seq_num):
        return

    def parse(self,receipt):
        self.aim = True
        ports = [port for port in sorted(serial.tools.list_ports.comports())]
        if ports:
            datasheet = [("port\'s device", "port\'s description")]
            for port in ports:
                datasheet.append((port.device, port.description))
            return format_table(datasheet)
        else:
            return 'there is no port'


    def process_fail(self):
        print("list_ports_task任务结束")
        return

class list_nodes_task(Task):
    def __init__(self, _serial,_socket,**kwargs):
        super().__init__(_serial,_socket,**kwargs)
        self.task_id = 0xf0
        self.data = b''

    def produce(self, seq_num):
        short_addr = 0x0000
        package = protocol.node_package(self.data,
                                        fixed_token=self.header,
                                        data_len=len(self.data) +self.header_len,
                                        short_addr=short_addr,
                                        profile_id=self.task_id,
                                        seq_num=seq_num,
                                        sub_seq_num=seq_num,
                                        )
        return package + protocol.pack_check_num(package)

    def parse(self,receipt):
        self.aim = True
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
            })
            # led_sequence = node_led_mapping.get(ext_addr)
            # 生成节点对象
            receipt.data = receipt_data
            self.nodes[nwk_addr] = Node(ext_addr)
        # nodes = dict()
        # for short_addr, mac_addr in self.nodes:
        #     nodes[short_addr] = mac_addr
        return {'result':receipt_data}

    def process_fail(self):
        print("list_nodes_task任务失败")
        return


class temp_start_task(Task):
    # todo：当没有节点时如何处理？
    def __init__(self, _serial, _socket, **kwargs):
        super().__init__(_serial, _socket, **kwargs)
        self.times = None
        self.profile_id = 0x10
        self.data = b''
        self.expected_receipt_num = 0
        self.received_receipt_num = 0

    def produce(self,seq_num):
        big_p = b''
        if self.nodes:
            for short_addr in self.nodes:
                package = protocol.node_package(self.data,
                                                fixed_token=self.header,
                                                data_len=len(self.data) + self.header_len,
                                                short_addr=short_addr,
                                                profile_id=self.profile_id,
                                                seq_num=seq_num,
                                                sub_seq_num=seq_num,
                                                )
                package += protocol.pack_check_num(package)
                big_p += package
            self.expected_receipt_num = len(self.nodes)
        return big_p

    def parse(self,receipt):
        # 解包温度
        self.received_receipt_num += 1
        if self.received_receipt_num == self.expected_receipt_num:
            self.aim = True
        temperature = float(receipt.data)
        receipt.data = temperature
        return {'result':temperature}

    def process_fail(self):
        self._socket.notify_write({"result":"temp_start_task任务失败"})
        return

class temp_stop_task(Task):
    def __init__(self, args=''):
        super().__init__()

class temp_pause_task(Task):
    def __init__(self, args=''):
        super().__init__()

class temp_resume_task(Task):
    def __init__(self, args=''):
        super().__init__()

class led_clear_task(Task):
    def __init__(self, args=''):
        super().__init__()

class led_set_task(Task):
    def __init__(self, args=''):
        super().__init__()

class led_get_task(Task):
    def __init__(self, args=''):
        super().__init__()

if __name__ == "__main__":
    print(isinstance(led_get_task(),led_get_task))
    print(led_get_task,'\n',led_get_task())
