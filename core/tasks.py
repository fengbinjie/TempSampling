import core.async_serial as serial
import core.protocol as pr
import yaml
import threading
import argparse


__title__ = 'tempsampling'
__version__ = '0.1.0'
__build__ = 0x000100
__author__ = 'Binjie Feng'
__license__ = 'ISC'
__copyright__ = 'Copyright 2020 Binjie Feng'

NodeList = [] # 节点列表

class NodeInfo:
    def __init__(self):
        self.short_addr = None
        self.mac_addr = None
        self.led_file_path = None

    def get_led(self):
        return yaml.load(self.led_file_path,Loader=yaml.FullLoader)

SERIAL_NUM = 0
send_task_dict = {
    # profile_id, 两位，保留0x00~0x0f,前一位代表任务类型，后一位代表任务子类型（接收,发送,...)
        0x10: send_temp_sampling, # 节点地址的收发，节点退出
        0x20: recv_addr_list,     # 温度信息的收发
        0x30: led,                # led信息的收发
}
recv_task_dict = {
    0x11: te,
    0x21:
    0x31
}

def get_
def recived_data_process(command):
    first_4_bits = command & 0xf0
    second_4_bits = command & 0x0f
    if first_4_bits == 1:
        if second_4_bits == 2:
            # 地址列表收到
            pass
        elif second_4_bits == 3:
            # 节点退出
            pass

def sent_data_process(command,data):
    first_4_bits = command & 0xf0
    second_4_bits = command & 0x0f
    if first_4_bits == 1:
        if second_4_bits == 1:
            # 地址列表询问
            return b''
    if first_4_bits == 2:
        if second_4_bits == 1:
            # 温度信息询问
            return b''


def create_task(command):
    global SERIAL_NUM
    if command == 0x11:
        SERIAL_NUM += 1
        pr.complete_package(node_addr=0x0000, profile_id=0x11, serial_num=SERIAL_NUM, data=b'')
    elif command == 0x21:
        def temp_task(node_short_addr):
            SERIAL_NUM += 1

        return temp_task
    elif command == 0x31:
        def led_task(node):
            SERIAL_NUM += 1
            pr.complete_package(node_addr=node.short_addr, profile_id=0x31, serial_num=SERIAL_NUM, data=b'')
        return led_task
TEMP_SAMPLING_FLAG = False
lock = threading.Lock()

# todo:改写成上下文管理器，每次创建一个任务后都执行一次该函数
def serial_num_self_increasing():
    global SERIAL_NUM
    with lock:
        SERIAL_NUM += 1
# 循环采集温度任务
def temp_sampling():
    while TEMP_SAMPLING_FLAG:
        # 节点中途离线怎么办
        for node in NodeList:
            pr.complete_package(node_addr=node.short_addr, profile_id=0x21, serial_num=SERIAL_NUM, data=b'')
            serial_num_self_increasing()

# 获得zigbee节点列表
def get_nodes_info():
    pr.complete_package(node_addr=0x0000, profile_id=0x11, serial_num=SERIAL_NUM, data=b'')
    serial_num_self_increasing()
NODE_LED_MAPPING = {}
# is_live获得现存节点与led文件的映射 否则获得所有节点与led文件的映射
def get_live_nodes_led_path(is_live=True):
        # 检查led_node_mapping文件是否存在
        # 取出所有的值，yaml格式，键代表节点mac地址，值代表led文件地址
        # 其中是否存在现存节点
        # 以一个字典返回现存节点和文件地址
        pass


def init_task(task,interval,run_num=None):
    '''

    :param task: 是一个任务，是一个已经设置好node_addr/client_id/...的任务
    :param interval: 时间间隔，此参数必须在run_num=None时才生效
    :param run_num: 运行次数，None则为任务循环运行
    :return:
    '''
    while True:
        for node in NodeList:
            task(node)
    pass


def setup(task_list):
    '''

    :param task_list: 已经设置好时间间隔、运行次数的task列表
    :return:
    '''
    # 获得全部地址信息

    # 进程1循环执行温度采集

    # 节点加入退出判断

    # led写入，终止运行中的程序

    # 心跳


    pass
def main():
    parser = argparse.ArgumentParser(description=f'TempSampling {__version__} - TUXIHUOZAIGONGCHENG',
                                     prog='TempSampling')

    parser.add_argument('-p',
                        '--ports',
                        help='Show serial ports list',
                        dest='ports',
                        action='store_true'
                        )
    parser.add_argument('-m',
                        dest='mapping',
                        help='Show all files and node mapping',
                        action='store_true'
                        )
    parser.add_argument('--temp',
                        dest='server_start',
                        action='store_true',
                        help='Start Server'
                        )
    args = parser.parse_args()
    if args.ports:
        ports = serial.find_serial_port_list()
        print(ports if ports else "there is no port")
        return
    if args.mapping:
        pass
        # TODO:补充映射文件节点的逻辑
        return
    if args.server_start:
        pass
        # TODO开始循环采集温度任务
        global  TEMP_SAMPLING_FLAG
        TEMP_SAMPLING_FLAG = True
        temp_sampling()

