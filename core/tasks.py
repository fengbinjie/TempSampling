import argparse
import logging
import logging.config
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

try:
    dict_conf = util.get_setting(os.path.join(core.PROJECT_DIR, "log_setting.yml"))
    logging.config.dictConfig(dict_conf)
except Exception as why:
    print(why, "\n配置文件不存在或配置错误")
    exit()
# todo:写上下文管理器函数，出现错误就退出
logger = logging.getLogger('test')


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
    temperature = float(receipt.data)
    logger.info(f"EndDevice {receipt.short_addr} | temp{temperature}")


def confirm_led_setting(receipt):
    result = struct.unpack('<B', receipt.data)[0]
    result = True if result == 1 else False
    logger.info(f"{receipt.short_addr}LED已设置{result}")
    return receipt.short_addr



def new_node_join(receipt):
    # H:代表16位短地址，8B代表64位mac地址
    fmt = "H8B"
    # 该命令只有串口协议
    mixed_addr_tuple = struct.unpack(f'<{fmt}', receipt.data)
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


def log_result(func):
    @wraps(func)
    def wrapped_function(receipt):
        logger.info(f'{receipt.node_addr} | {receipt.data} | {receipt.serial_num}')
        return func(receipt)
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
        # 当列表长度大于0或还没发送完时
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
            serial.send_to_node(short_addr, 0x20, data=data_bytes)
            node_list.append(short_addr)
    send_done = True

def check_led_exist(node_mac_addr):
    if node_mac_addr:
        led_dict = led_node_mapping_exist()
        if node_mac_addr in led_dict.keys() and os.path.exists(led_dict[node_mac_addr]):
            return True
    return False
    # todo:节点中途掉电，重新上电时，服务器收到消息，向节点询问是否已经设置了led,如果没有则再发送led灯语，否则节点发送确认已经设置信号回来

def nodes_live():
    # 得到串口
    serial = get_serial()
    # 接收数据线程
    c1 = serial.recv_data_process()
    node_list = []
    send_done = False
    def process_temp():
        # 消息未发送完毕或消息未全部接收完毕
        while len(node_list) > 0 or not send_done:
            # 此处会一直等待消息，直到程序退出或有消息进来
            try:
                # 未接受过数据
                receipt = next(c1)
            except StopIteration:
                break
            else:
                node_list.remove(receipt.short_addr)
    def setup():
        # 获得现存短地址列表
        node_short_addr_list = Nodes.keys()
        if node_short_addr_list:
            for node_short_addr in node_short_addr_list:
                serial.send_to_node(node_short_addr, 0x30)
                node_list.append(node_short_addr)

    recv_thread = threading.Thread(target=process_temp, args=())
    recv_thread.setDaemon(False)
    recv_thread.start()
    setup()
    send_done = True
    # 定时2秒，在2秒钟之内接收
    time.sleep(2)
    serial.receiveProgressStop = True
    for node in node_list:
        Nodes.pop(node)

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
                        serial.send_to_node(node_short_addr, 0x10)
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
    rw.send_to_coordinate(short_addr=0x0000, profile_id=0xf0)
    # 得到结果,并设置
    set_nodes(next(c1))
    # todo:协调器出现问题时（会卡在recv_data_process函数中）设置一个定时器关闭


def get_all_nodes_led_mappings():
    all_node_led_mappings = []

    for node in Nodes.values():
        # 其中是否存在现存节点,是就把节点从node_led_mapping中删除
        if node.mac_addr in node_led_mapping:
            node_led_mapping.pop(node.mac_addr)
        # 添加在线节点
        all_node_led_mappings.append(('Y', node.mac_addr, node.led_file_path))
    # 添加不在线的节点
    for k in node_led_mapping:
        all_node_led_mappings.append(('N', k, node_led_mapping[k]))
    return all_node_led_mappings


def set_tempsampling_flag():
    global TEMP_SAMPLING_FLAG
    TEMP_SAMPLING_FLAG = True


def remove_tempsampling_flag():
    global TEMP_SAMPLING_FLAG
    TEMP_SAMPLING_FLAG = False


def print_table(datasheet):
    """
    datasheet是一个列表，列表中的元素是列表，且长度相同，第一个元素是表的表头,其余都是数据
    二级列表中的每一个元素都是字符串
    :param datasheet:
    :return: none
    """
    # 表头
    table = util.TableDisplay('No.', *datasheet[0])
    no = 1
    # 数据部分
    for row in datasheet[1:]:
        table.add_row(str(no), *row)
        no += 1
    print(table)


def main():
    def args_func(args):
        if args.nodes:
            get_nodes_info()
            nodes_live()
            datasheet = [('network address', 'extend address')]
            for short_addr, node in Nodes.items():
                datasheet.append(('0x{:x}'.format(short_addr), node.mac_addr))
            print_table(datasheet)



    def port_args_func(args):
        # 列出当前所有串口
        if args.ports:
            ports = Serial.find_serial_port_list()
            if ports:
                datasheet = [("port\'s device", "port\'s description")]
                for port in ports:
                    datasheet.append((port.device, port.description))
                print_table(datasheet)
            else:
                print('there is no port')

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
            datasheet = [('on line', 'node', 'dir'), *led_node_mapping]
            print_table(datasheet)
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

    port_parser = sub_parsers.add_parser('port', help='port 相关操作')
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