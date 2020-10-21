from collections import OrderedDict
import struct
ENDIAN = '<'
fixed_token_property = OrderedDict([('fixed_token', {'default_value': 0xabcd, 'fmt': 'H'})])
content_property = OrderedDict([('data_len', {'fmt': 'B'}),
                                       ('node_addr', {'fmt': 'H'}),
                                       ('profile_id', {'fmt': 'B'}),
                                       ('serial_num', {'fmt': 'B'})])
BASIC_PROTOCOL_PROPERTY = {**fixed_token_property, **content_property}

sub_fixed_token_property = OrderedDict([('sub_fixed_token', {'default_value': 0xcb, 'fmt': 'B'})])
sub_content_property = OrderedDict([('sub_serial_num', {'fmt': 'B'})])
SUB_PROTOCOL_PROPERTY = {**sub_fixed_token_property, **sub_content_property}




def get_fixed_token_property(endian=ENDIAN):
    # 返回fixed_token_property字典中的fixed_token项中的default_value、选定字节顺序后的fmt值以及fmt值在选定字节顺序后的长度
    v = fixed_token_property['fixed_token']['default_value']
    fmt = f"{endian}{fixed_token_property['fixed_token']['fmt']}"
    l_fmt = struct.calcsize(fmt)
    return v, fmt, l_fmt


def subprotocol_fmt(with_endian, endian=ENDIAN):
    fmt_str = ''.join([v['fmt'] for k, v in SUB_PROTOCOL_PROPERTY.items()])
    return endian+fmt_str if with_endian else fmt_str


def get_content_fmt(with_endian, endian=ENDIAN):
    # 获得content_property值中完整content_fmt
    fmt_str = "".join([value["fmt"] for value in content_property.values()])
    # 返回content_fmt_str
    return endian+fmt_str if with_endian else fmt_str

def get_content_fmt2(with_endian,endian=ENDIAN):
    fmt_str = content_property['node_addr']['fmt'] + \
              content_property['profile_id']['fmt'] + \
              content_property['serial_num']['fmt']

    return endian + fmt_str if with_endian else fmt_str


def create_class_header(header_name, header_type):
    """
    head_type = BASIC_PROTOCOL_PROPERTY时 _fields = (fixed_token,data_len,node_addr,profile_id,serial_num)
    head_type = SUB_PROTOCOL_PROPERTY时(sub_fixed_token,sub_serial_num)
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
    __slots__ = tuple([*BASIC_PROTOCOL_PROPERTY.keys(), *SUB_PROTOCOL_PROPERTY.keys(), 'data'])
    pass


HeaderStr = [BASIC_PROTOCOL_PROPERTY, SUB_PROTOCOL_PROPERTY]
HeaderInstance = [create_class_header(f'Header{index}', i)() for index, i in enumerate(HeaderStr)]


def complete_package(data, **kwargs):
    if not isinstance(data, bytes):
        raise Exception("data is not a bytes")
    # 此处参数的赋值顺序会影响包实例的打包值顺序
    package = b''

    for header in HeaderInstance:
        header_bytes = header.pack(**kwargs)
        package = package + header_bytes
    package = package + data
    return package

def parse_package(package):
    if not isinstance(package, bytes):
        raise Exception("package is not a bytes")
    receipt = Receipt()
    for header in HeaderInstance:
        package = header.unpack(receipt, package)
    receipt.data = package
    return receipt

