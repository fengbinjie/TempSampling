import argparse
import logging
import os
import struct
import threading
import time
import yaml

import core
import core.serial_with_protocol as serial

__title__ = 'tempsampling'
__version__ = '0.1.0'
__build__ = 0x000100
__author__ = 'Binjie Feng'
__license__ = 'ISC'
__copyright__ = 'Copyright 2020 Binjie Feng'

# 节点字典 key 是节点短地址,value是Node类
Nodes = {}
SERIAL_NUM = 0
logger = logging.getLogger('asyncio')

def get_setting():
    """
    以yaml格式解析setting文件
    :return: 字典形式的属性集合
    """
    try:
        with open(os.path.join(core.PROJECT_DIR, 'setting.yml')) as f:
            setting_dict = yaml.load(f, Loader=yaml.FullLoader)
    except FileNotFoundError as why:
        print(why)
        exit()
    else:
        return setting_dict

def get_serial():
    setting_dict = get_setting()
    if os.name is 'nt':
        default_com = setting_dict['default_nt_com']
    elif os.name is 'posix':
        default_com = setting_dict['default_posix_com']
    else:
        raise Exception('unsupported system')
    default_baudrate = setting_dict['default_baudrate']
    return serial.ReadWrite(default_com, default_baudrate, 0.01)


def write_setting(**kwargs):
    """
    将参数中的键值对写入setting.yml文件
    :param kwargs:
    :return:
    """
    setting_dict = get_setting()
    setting_dict_keys = setting_dict.keys()
    for k, v in kwargs.items():
        # 如果setting存在被给属性且属性值的类型和参数中给的值的类型相同则写入
        if k in setting_dict_keys and isinstance(v, type(setting_dict[k])):
            setting_dict[k] = v
        else:
            raise Exception("不存在该属性或值错误")
    # 将字典以yaml的格式写入
    with open(os.path.join(core.PROJECT_DIR, 'setting.yml'), mode='w') as f:
        yaml.dump(setting_dict, f)

class Node:
    def __init__(self, mac_addr):
        self.mac_addr = mac_addr
        self.led_file_path = None

    def get_led(self):
        return yaml.load(self.led_file_path, Loader=yaml.FullLoader)


def acquire_temperature(reverse_package, reverse_sub_package, data):
    # 解包温度
    temperature = struct.unpack('<H', data)[0] / 10
    print(f"EndDevice {reverse_package.node_addr} | temp{temperature}")
    # logger.info(f"EndDevice {reverse_package.node_addr} | temp{temperature}")


def confirm_led_setting(reverse_package, reverse_sub_package, data):

    logger.info(f"{reverse_package.node_addr}LED已设置{data}")


def new_node_join(reverse_package, reverse_sub_package, data):
    # H:代表16位短地址，8B代表64位mac地址
    fmt = "H8B"
    # 该命令只有串口协议
    mixed_addr_tuple = struct.unpack(f'<{fmt}', data)
    ext_addr = ' '.join([str(i) for i in mixed_addr_tuple[1:9]])
    nwk_addr = mixed_addr_tuple[-1]
    Nodes[nwk_addr] = Node(ext_addr)
    logger.warning(f"节点加入 {nwk_addr} | {ext_addr}")


def set_nodes(reverse_package, reverse_sub_package, data):
    # H:代表16位短地址，8B代表64位mac地址
    fmt = "H8B"
    # 该命令只有串口协议
    fmt_len = struct.calcsize(fmt)
    fmt = fmt * (len(data) // fmt_len)
    mixed_addr_tuple = struct.unpack(f'<{fmt}', data)

    l_len = len(mixed_addr_tuple) // 9
    for index in range(l_len):
        nwk_addr = mixed_addr_tuple[9 * index]
        ext_addr = mixed_addr_tuple[index * 9 + 1:(index + 1) * 9]
        Nodes[nwk_addr] = Node(ext_addr)


temp_recv_cluster ={
    0x08: acquire_temperature
}
led_recv_cluster = {
    0x08: confirm_led_setting
}
nodes_recv_cluster={
    0x08: new_node_join,
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

# def recv_process(package):
#     # 解析包
#     reverse_package, reverse_sub_package, data = pr.parse_package(package)
#     # 确定使用哪个命令处理
#     data_process_func = determine_command(reverse_package.profile_id)
#     # 具体处理
#     data_process_func(reverse_package, reverse_sub_package, data)


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
def cycle_sampling():
    # 得到串口
    serial = get_serial()
    # 接收数据线程
    c1 = serial.recv_data_process()
    def process_temp():
        while True:
            data = next(c1)
            acquire_temperature(*data)

    recv_thread = threading.Thread(target=process_temp,args=())
    recv_thread.setDaemon(True)
    recv_thread.start()
    while True:
        # 获得现存短地址列表
        node_short_addr_list = Nodes.keys()
        if node_short_addr_list:
            for node_short_addr in node_short_addr_list:
                if TEMP_SAMPLING_FLAG:
                    serial.send_data(node_short_addr, 0x10, SERIAL_NUM)
                else:
                    # 退出整理
                    exit()
                time.sleep(1)
        else:
            print("there is no node")
            time.sleep(5)


# 询问zigbee节点列表
def get_nodes_info():
    rw = get_serial()
    # 获得数据接收生成器
    c1 = rw.recv_data_process()
    # 询问节点列表
    rw.send_data(node_addr=0x0000, profile_id=0x30, serial_num=127)
    # 得到结果,并设置
    set_nodes(*next(c1))




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
    def args_func(args):
        if args.nodes:
            get_nodes_info()
            for short_addr, node in Nodes.items():
                print(hex(short_addr), node.mac_addr)

    def port_args_func(args):
        # 列出当前所有串口
        if args.ports:
            ports = serial.find_serial_port_list()
            print(ports if ports else 'there is no port')

        # 选择指定串口去通信
        if args.select_port:
            if os.name is 'nt':
                write_setting(default_nt_com=args.select_port)
            elif os.name is 'posix':
                write_setting(default_posix_com=args.select_port)
            else:
                raise Exception('unsupported system')



    def led_args_func(args):
        if args.current:
            led_node_mapping = get_live_nodes_led_path()
            # TODO:格式化输出
            # TODO:补充当前映射文件节点的逻辑
            print(led_node_mapping)
        if args.all:
            led_node_mapping = get_live_nodes_led_path(is_alive=False)
            # TODO:格式化输出
            print(led_node_mapping)
            # TODO:补充全部映射文件节点的逻辑

    def temp_args_func(args):
        # 温度采集任务开始
        if args.temp_start:
            # TODO:开始循环采集温度任务
            get_nodes_info()
            set_tempsampling_flag()
            cycle_sampling()
        # 停止采集任务
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