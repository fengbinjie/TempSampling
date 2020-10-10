import argparse
import logging
import os
import struct
import threading

import yaml

import core
import core.async_serial as serial
import core.protocol as pr

__title__ = 'tempsampling'
__version__ = '0.1.0'
__build__ = 0x000100
__author__ = 'Binjie Feng'
__license__ = 'ISC'
__copyright__ = 'Copyright 2020 Binjie Feng'

NodeList = []  # 节点列表
SERIAL_NUM = 0
logger = logging.getLogger('asyncio')


DEFAULT_COM = None
if os.name is 'nt':
    DEFAULT_COM = yaml.load(os.path.join(core.PROJECT_DIR,'/setting'))['default_nt_com']
elif os.name is 'posix':
    DEFAULT_COM = yaml.load(os.path.join(core.PROJECT_DIR,'/setting'))['default_posix_com']
else:
    raise Exception('unsupported system')
active_serial = serial.ComReadWrite(DEFAULT_COM,115200)
class Node:
    def __init__(self, short_addr, mac_addr):
        self.short_addr = None
        self.mac_addr = None
        self.led_file_path = None

    def get_led(self):
        return yaml.load(self.led_file_path, Loader=yaml.FullLoader)


def acquire_temperature(reverse_package, reverse_sub_package, data):
    temperature = data / 10
    logger.info("EndDevice {0:10} | temp{1:5} |count{2:5}".format(
        hex(reverse_package.node_addr),
        temperature
    ))


def confirm_led_setting(reverse_package, reverse_sub_package, data):

    logger.info(f"{reverse_package.node_addr}LED已设置{data}")


def new_node_join(reverse_package, reverse_sub_package, data):
    #H:代表16位短地址，8B代表64位mac地址
    fmt = "H8B"
    # 该命令只有串口协议
    mixed_addr_tuple = struct.unpack(f'{pr.sub_protocol.endian}{fmt}', data)
    ext_addr = ' '.join([str(i) for i in mixed_addr_tuple[1:9]])
    nwk_addr = mixed_addr_tuple[-1]
    NodeList.append(Node(nwk_addr,ext_addr))
    logger.warning(f"节点加入 {nwk_addr} | {ext_addr}")


def get_node_list(reverse_package, reverse_sub_package, data):
    # H:代表16位短地址，8B代表64位mac地址
    fmt = "H8B"
    # 该命令只有串口协议
    fmt_len = struct.calcsize(fmt)
    fmt = fmt * (reverse_sub_package.data_len // fmt_len)
    mixed_addr_tuple = struct.unpack(f'{pr.sub_protocol.endian}{fmt}', data)

    l_len = len(mixed_addr_tuple) // 9
    mixed_addr_list = {}
    for index in range(l_len):
        nwk_addr = mixed_addr_tuple[9 * index]
        ext_addr = ' '.join([str(i) for i in mixed_addr_tuple[index * 9 + 1:(index + 1) * 9]])
        mixed_addr_list[nwk_addr] = ext_addr
        NodeList.append(Node(nwk_addr, ext_addr))

temp_recv_cluster ={
    0x08: acquire_temperature
}
led_recv_cluster = {
    0x08: confirm_led_setting
}
nodes_recv_cluster={
    0x08: new_node_join,
    0x09: get_node_list
}
recv_clusters={
    0x10: temp_recv_cluster,
    0x20: led_recv_cluster,
    0x30: nodes_recv_cluster
}

TEMP_SAMPLING_FLAG = False


def is_temp_receipt(profile_id):
    return True if profile_id ^ 0x10 else False


def determine_command(profile_id):
    # 确定使用哪个命令处理集
    sub_cluster = recv_clusters[profile_id ^ 0xf0]
    # 确定使用哪个命令处理
    return sub_cluster[profile_id ^ 0x0f]

def recv_process(package):
    # 解析包
    reverse_package, reverse_sub_package, data = pr.parse_package(package)
    # 确定使用哪个命令处理
    data_process_func = determine_command(reverse_package.profile_id)
    # 具体处理
    data_process_func(reverse_package, reverse_sub_package, data)


# todo:改写成上下文管理器，每次创建一个任务后都执行一次该函数
lock = threading.Lock()
def serial_num_self_increasing():
    global SERIAL_NUM
    with lock:
        SERIAL_NUM += 1

def led_node_mapping_exist():
    if os.path.exists(os.path.join(core.PROJECT_DIR, '/led_node_mapping.yml')):
        return True
    else:
        return False


def load_led_node_mapping():
    if led_node_mapping_exist():
        return yaml.load(os.path.join(core.PROJECT_DIR, '/led_node_mapping.yml'), yaml.FullLoader)
    else:
        raise Exception('No led_node_mapping.yml')


def check_led_exist(node_mac_addr):
    if node_mac_addr:
        led_dict = led_node_mapping_exist()
        if node_mac_addr in led_dict.keys() and os.path.exists(led_dict[node_mac_addr]):
            return True
    return False


# TODO:改成生成器
def temp_sampling():
    # 节点中途离线怎么办
    package_list = None
    for node in NodeList:
        pr.complete_package(node_addr=node.short_addr, profile_id=0x21, serial_num=SERIAL_NUM, data=b'')
        serial_num_self_increasing()
    return package_list

def cycle_sampling():
    while TEMP_SAMPLING_FLAG:
        for package in temp_sampling():
            active_serial.send_data_process(package)


# 询问zigbee节点列表
def get_nodes_info():
    package = pr.complete_package(node_addr=0x0000, profile_id=0x11, serial_num=SERIAL_NUM, data=b'')
    serial_num_self_increasing()
    return package


NODE_LED_MAPPING = {}
# is_live获得现存节点与led文件的映射 否则获得所有节点与led文件的映射


def get_live_nodes_led_path(is_alive=True):
    # 检查led_node_mapping文件是否存在
    led_dict = load_led_node_mapping()
    led_dict_keys = led_dict.keys()
    # 取出所有的值，yaml格式，键代表节点mac地址，值代表led文件地址
    if is_alive:
        current_live_led_dict = {}
        for node in NodeList:
            # 其中是否存在现存节点
            if node.mac_addr in led_dict_keys:
                # 以一个字典返回现存节点和文件地址
                current_live_led_dict.update(led_dict.popitem())
        return current_live_led_dict
    else:
        return led_dict


def set_tempsampling_flag():
    global TEMP_SAMPLING_FLAG
    TEMP_SAMPLING_FLAG = True


def remove_tempsampling_flag():
    global TEMP_SAMPLING_FLAG
    TEMP_SAMPLING_FLAG = False


def main():
    parser = argparse.ArgumentParser(description=f'TempSampling {__version__} - TUXIHUOZAIGONGCHENG',
                                     prog='TempSampling')
    sub_parser =parser.add_subparsers()
    #todo:help属性增加
    port_parser = sub_parser.add_parser('port')
    led_parser = sub_parser.add_parser('led')
    temp_parser = sub_parser.add_parser('temp')
    # 获得所有串口
    port_parser.add_argument('-l',
                             '--list',
                             help='Show serial ports list',
                             dest='ports',
                             action='store_true'
                             )
    # 选择指定串口通信
    port_parser.add_subparsers('-s',
                               '--select',
                               help='select this com to communicate',
                               dest='select_port')
    # 获得当前所有节点的灯语映射
    led_parser.add_argument('-c',
                            dest='current',
                            help='Show current node-led mapping',
                            action='store_true'
                            )
    # 获得保存的所有节点和灯语的映射
    led_parser.add_argument('-a',
                            dest='all',
                            help='Show all node-led mapping',
                            action='store_true'
                            )
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

    args = parser.parse_args()
    led_args = led_parser.parse_args()
    port_args = port_parser.parse_args()
    temp_args = temp_parser.parse_args()
    # 温度采集任务开始
    if temp_args.temp_start:
        # TODO:开始循环采集温度任务
        set_tempsampling_flag()
        temp_sampling()
        return
    # 停止采集任务
    if temp_args.temp_stop:
        remove_tempsampling_flag()
        return
    # 列出当前所有串口
    if port_args.ports:
        ports = serial.find_serial_port_list()
        print(ports if ports else "there is no port")
        return
    # 选择指定串口去通信
    if port_args.select_port:
        port = port_args.select_port
        # TODO:选择指定串口去通信

    if led_args.current:
        led_node_mapping = get_live_nodes_led_path()
        # TODO:格式化输出
        # TODO:补充当前映射文件节点的逻辑
        print(led_node_mapping)
        return
    if led_args.all:
        led_node_mapping = get_live_nodes_led_path(is_alive=False)
        # TODO:格式化输出
        print(led_node_mapping)
        # TODO:补充全部映射文件节点的逻辑
