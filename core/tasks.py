import argparse
import logging
import os
import struct
import threading
import time
import yaml

import core
import core.serial_with_protocol as Serial
import core.util as util
from functools import wraps
__title__ = 'tempsampling'
__version__ = '0.1.0'
__build__ = 0x000100
__author__ = 'Binjie Feng'
__license__ = 'ISC'
__copyright__ = 'Copyright 2020 Binjie Feng'

# 节点字典 key 是节点短地址,value是Node类
Nodes = {}
# 节点和灯语文件的映射 ，key是节点的mac地址，value是灯语文件的位置
# 假如不存在任何映射则赋值为空字典
node_led_mapping = util.get_setting(os.path.join(core.PROJECT_DIR, "led_node_mapping.yml")) or {}

logger = logging.getLogger('asyncio')


def get_serial():
    setting_dict = util.get_setting(os.path.join(core.PROJECT_DIR, 'setting.yml'))
    if os.name is 'nt':
        default_com = setting_dict['default_nt_com']
    elif os.name is 'posix':
        default_com = setting_dict['default_posix_com']
    else:
        raise Exception('unsupported system')
    default_baudrate = setting_dict['default_baudrate']
    return Serial.ReadWrite(default_com, default_baudrate, 0.01)


class Node:
    def __init__(self, mac_addr, led_file_path=None):
        self.mac_addr = mac_addr
        self.led_file_path = led_file_path

    def get_led(self):
        return yaml.load(self.led_file_path, Loader=yaml.FullLoader)


def acquire_temperature(receipt):
    # 解包温度
    temperature = struct.unpack('<H', receipt. data)[0] / 10
    print(f"{time.time()}EndDevice {receipt.node_addr} | temp{temperature}")
    # logger.info(f"EndDevice {reverse_package.node_addr} | temp{temperature}")


def confirm_led_setting(receipt):
    print(receipt.data)
    return receipt.node_addr
    # logger.info(f"{reverse_package.node_addr}LED已设置{data}")


def new_node_join(receipt):
    # H:代表16位短地址，8B代表64位mac地址
    fmt = "H8B"
    # 该命令只有串口协议
    mixed_addr_tuple = struct.unpack(f'<{fmt}', receipt)
    ext_addr = ' '.join([str(i) for i in mixed_addr_tuple[1:9]])
    nwk_addr = mixed_addr_tuple[-1]
    Nodes[nwk_addr] = Node(ext_addr)
    logger.warning(f"节点加入 {nwk_addr} | {ext_addr}")


def set_nodes(receipt):
    # H:代表16位短地址，8B代表64位mac地址
    fmt = "H8B"
    # 该命令只有串口协议
    fmt_len = struct.calcsize(fmt)
    fmt = fmt * (len(receipt.data) // fmt_len)
    mixed_addr_tuple = struct.unpack(f'<{fmt}', receipt.data)

    l_len = len(mixed_addr_tuple) // 9

    for index in range(l_len):
        # 短地址
        nwk_addr = mixed_addr_tuple[9 * index]
        # 长地址
        ext_addr = " ".join([str(v) for v in mixed_addr_tuple[index * 9 + 1:(index + 1) * 9]])
        # 有灯语
        led_sequence = node_led_mapping.get(ext_addr)
        # 生成节点对象
        Nodes[nwk_addr] = Node(ext_addr, led_sequence)


TEMP_SAMPLING_FLAG = False


def serial_num_increasing(func):
    @wraps(func)
    def wrapped_function(*args, **kwargs):
        global SERIAL_NUM
        SERIAL_NUM += 1
        return func(*args, **kwargs)
    return wrapped_function



def write_led_sequences():
    # 得到串口
    serial = get_serial()
    # 接收数据线程
    c1 = serial.recv_data_process()
    node_list = []
    send_done = False
    # 内置函数处理数据
    def process_recv():
        while len(node_list) > 0 or not send_done:
            node_addr = confirm_led_setting(next(c1))
            node_list.remove(node_addr)

    recv_thread = threading.Thread(target=process_recv, args=())
    recv_thread.start()
    for short_addr, node in Nodes.items():
        if node.led_file_path:
            # 获得灯语设置
            lamp_signal = util.get_setting(node.led_file_path)
            data = [step_property for flash_step in lamp_signal for step_property in flash_step]
            data_bytes = struct.pack(f'<{len(data)}H', *data)
            serial.send_data(short_addr, 0x20, data=data_bytes)
            node_list.append(short_addr)
    send_done = True

def check_led_exist(node_mac_addr):
    if node_mac_addr:
        led_dict = led_node_mapping_exist()
        if node_mac_addr in led_dict.keys() and os.path.exists(led_dict[node_mac_addr]):
            return True
    return False

def setup(send_func, recv_func):
    # 得到串口
    serial = get_serial()
    # 接收数据线程
    c1 = serial.recv_data_process()

    def recv_process():
        while True:
            recv_func(next(c1))
    recv_thread = threading.Thread(target=recv_process, args=())
    recv_thread.setDaemon(True)
    recv_thread.start()
    send_func()

# TODO:改成生成器
def cycle_sampling():
    # 得到串口
    serial = get_serial()
    # 接收数据线程
    c1 = serial.recv_data_process()
    def process_temp():
        while True:
            acquire_temperature(next(c1))

    def setup():
        while True:
            # 获得现存短地址列表
            node_short_addr_list = Nodes.keys()
            if node_short_addr_list:
                for node_short_addr in node_short_addr_list:
                    if TEMP_SAMPLING_FLAG:
                        serial.send_data(node_short_addr, 0x10)
                    else:
                        # 退出整理
                        exit()
                    time.sleep(2)
            else:
                print("there is no node")
                time.sleep(5)
    recv_thread = threading.Thread(target=process_temp,args=())
    recv_thread.setDaemon(True)
    recv_thread.start()
    setup()



# 询问zigbee节点列表
def get_nodes_info():
    rw = get_serial()
    # 获得数据接收生成器
    c1 = rw.recv_data_process()
    # 询问节点列表
    rw.send_data(node_addr=0x0000, profile_id=0x30)
    # 得到结果,并设置
    set_nodes(next(c1))


def get_all_nodes_led_mappings():
    for node in Nodes.values():
        # 其中是否存在现存节点
        # 以一个字典返回现存节点和文件地址
        node_led_mapping.setdefault(node.mac_addr, node.led_file_path)
    return node_led_mapping


def set_tempsampling_flag():
    global TEMP_SAMPLING_FLAG
    TEMP_SAMPLING_FLAG = True


def remove_tempsampling_flag():
    global TEMP_SAMPLING_FLAG
    TEMP_SAMPLING_FLAG = False

def detect_serial_ports():
    port_list = Serial.find_serial_port_list()
    fmt_ports_str = ''
    if port_list:
        for port in port_list:
            # TODO:输出格式化
            fmt_ports_str += f'|\t{port.device}\t|\t{port.description}\t|\n'
    return fmt_ports_str

def main():
    def args_func(args):
        if args.nodes:
            get_nodes_info()
            for short_addr, node in Nodes.items():
                print(hex(short_addr), node.mac_addr)

    def port_args_func(args):
        # 列出当前所有串口
        if args.ports:
            ports = detect_serial_ports()
            print(ports if ports else 'there is no port')

        # 选择指定串口去通信
        if args.select_port:
            if os.name is 'nt':
                util.write_setting(file=os.path.join(core.PROJECT_DIR,"setting.yml"), default_nt_com=args.select_port)
            elif os.name is 'posix':
                util.write_setting(file=os.path.join(core.PROJECT_DIR,"setting.yml"),default_posix_com=args.select_port)
            else:
                raise Exception('unsupported system')

    def led_args_func(args):
        if args.all:
            # 获得所有节点
            get_nodes_info()
            # 获得所有节点长地址和灯语的映射（包括在线的和未在线但被记录在led_node_mapping.yml文件中的）
            led_node_mapping = get_all_nodes_led_mappings()
            # TODO:格式化输出
            print(led_node_mapping)
            exit()
        if args.write:
            # 设置某个节点的灯语
            # 获得当前节点
            get_nodes_info()
            # 设置灯语后必须重启才能生效
            write_led_sequences()

    def temp_args_func(args):
        # 温度采集任务开始
        if args.temp_start:
            get_nodes_info()
            set_tempsampling_flag()
            cycle_sampling()
        # ToDo:停止采集任务,用shell来关闭，直接这样写无法关闭
        if args.temp_stop:
            if args.temp_stop:
                remove_tempsampling_flag()


    parser = argparse.ArgumentParser(description=f'TempSampling {__version__} - TUXIHUOZAIGONGCHENG',
                                     prog='TempSampling')
    parser.add_argument('--list',
                        help='Show all nodes in zigbee Currently',
                        dest='nodes',
                        action='store_true')
    parser.set_defaults(func=args_func)

    sub_parsers = parser.add_subparsers(help='sub-command help')
    #todo:help属性增加
    port_parser = sub_parsers.add_parser('port', help='port')
    # 获得所有串口
    port_parser.add_argument('-l',
                             '--list',
                             help='Show serial ports list',
                             dest='ports',
                             action='store_true'
                             )
    # 选择指定串口通信
    port_parser.add_argument('-s',
                             '--select',
                             help='select this com to communicate',
                             dest='select_port')
    port_parser.set_defaults(func=port_args_func)

    led_parser = sub_parsers.add_parser('led', help='led')
    # 获得当前所有节点的灯语映射
    led_parser.add_argument('-w',
                            dest='write',
                            help='write led sequence to node\'s rom',
                            action='store_true'
                            )
    # 获得保存的所有节点和灯语的映射
    led_parser.add_argument('-a',
                            dest='all',
                            help='Show all node-led mapping',
                            action='store_true'
                            )
    led_parser.set_defaults(func=led_args_func)

    temp_parser = sub_parsers.add_parser('temp', help='temp')
    temp_parser.add_argument('--start',
                             dest='temp_start',
                             action='store_true',
                             help='Start Server'
                             )
    temp_parser.add_argument('--stop',
                             dest='temp_stop',
                             action='store_true',
                             help='stop Server'
                             )
    temp_parser.set_defaults(func=temp_args_func)

    args = parser.parse_args()
    args.func(args)




if __name__ == '__main__':
    main()