from collections import OrderedDict
import struct
ENDIAN = '<'
fixed_fields = OrderedDict([('fixed_token', {'default_value': 0xabcd, 'fmt': 'H'})])
frame_control_fields = OrderedDict([('data_len', {'fmt': 'B'}),
                                    ('profile_id', {'fmt': 'B'}),
                                    ('short_addr', {'fmt': 'H'}),
                                    ('seq_num', {'fmt': 'H'})])
SERIAL_MSG_PROTOCOL = {**fixed_fields, **frame_control_fields}

AIR_MSG_PROTOCOL = OrderedDict([('sub_seq_num', {'fmt': 'H'})])


def sub_header_len(endian=ENDIAN):
    fmt_str = ''.join([v.get('fmt') for v in AIR_MSG_PROTOCOL.values()])
    return struct.calcsize(endian+fmt_str)


def get_fixed_token_property(endian=ENDIAN):
    # 返回fixed_token_property字典中的fixed_token项中的default_value、选定字节顺序后的fmt值以及fmt值在选定字节顺序后的长度
    v = fixed_fields['fixed_token']['default_value']
    fmt = f"{endian}{fixed_fields['fixed_token']['fmt']}"
    l_fmt = struct.calcsize(fmt)
    return v, fmt, l_fmt


def unfixed_header_fmt(with_endian, endian=ENDIAN):
    fmt_str = frame_control_fields['short_addr']['fmt'] + \
              frame_control_fields['profile_id']['fmt'] + \
              frame_control_fields['seq_num']['fmt']

    return endian + fmt_str if with_endian else fmt_str


def create_class_header(header_name, header_type):
    """
    head_type = BASIC_PROTOCOL_PROPERTY时 _fields = (fixed_token,data_len,node_addr,profile_id,serial_num)
    head_type = SUB_PROTOCOL_PROPERTY时(sub_serial_num)
    :param header_name:
    :param header_type:
    :return:
    """
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(cls, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        self.header_fmt = ''
        for value in header_type.values():
            self.header_fmt = self.header_fmt + value.get('fmt')
        self.endian = ENDIAN
        self.header_fmt_size = struct.calcsize(f'{self.endian}{self.header_fmt}')

    def pack(self, **kwargs):
        """
        关键字参数的参数名必须有已经在__slots__存在的合法字段
        :param self:
        :param kwargs:
        :return:
        """
        # 验证关键字参数参数名是否和__slots__中的字段一一对应，假如缺少某一参数就报错
        try:
            to_be_packaged = [kwargs[arg] for arg in self._fields]
        except Exception as why:
            print(f"缺少字段")
            print(why)
        # 打包头、数据
        values_bytes = struct.pack(f'{self.endian}{self.header_fmt}', *to_be_packaged)

        return values_bytes

    def unpack(self, receipt, package):
        complete_fmt = self.endian + self.header_fmt
        for index, value in enumerate(struct.unpack_from(complete_fmt, package)):
            # 赋值属性
            setattr(receipt, self._fields[index], value)
        return package[self.header_fmt_size:]

    return type(header_name, (), {
        '_instance': None,
        '_fields': tuple([k for k in header_type.keys()]),
        '__new__': __new__,
        '__init__': __init__,
        'pack': pack,
        'unpack': unpack
    })


class Receipt:
    __slots__ = tuple([*SERIAL_MSG_PROTOCOL.keys(), *AIR_MSG_PROTOCOL.keys(), 'data'])
    pass


serial_msg_protocol = create_class_header('serial_msg_protocol', SERIAL_MSG_PROTOCOL)()
air_msg_protocol = create_class_header('air_msg_protocol', AIR_MSG_PROTOCOL)()


def node_package(data, **kwargs):
    if not isinstance(data, bytes):
        raise Exception("data is not a bytes")
    package = b''
    # 添加串口消息头
    serial_msg_header = serial_msg_protocol.pack(**kwargs)
    # 添加空中消息头和数据组成完整的包
    package = serial_msg_header + air_msg_protocol.pack(**kwargs) + data
    return package


def coordinate_package(data, **kwargs):
    if not isinstance(data, bytes):
        raise Exception("data is not a bytes")
    # 此处参数的赋值顺序会影响包实例的打包值顺序
    package = b''
    # 添加串口消息头
    serial_msg_header = serial_msg_protocol.pack(**kwargs)
    # 添加空中消息头和数据组成完整的包
    package = serial_msg_header + data
    return package

def parse_package(package):
    if not isinstance(package, bytes):
        raise Exception("package is not a bytes")
    receipt = Receipt()
    surplus_package = serial_msg_protocol.unpack(receipt, package)
    # 判断是协调器消息还是节点消息
    # 协调器消息profileId从0xf0开始增长
    if receipt.profile_id < 0xf0:
        surplus_package = air_msg_protocol.unpack(receipt, surplus_package)
    receipt.data = surplus_package
    return receipt

