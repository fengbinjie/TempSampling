from collections import OrderedDict
import struct
ENDIAN = '<'
fixed_token_property = OrderedDict([('fixed_token', {'default_value': 0xabcd, 'fmt': 'H'})])
content_property = OrderedDict([('data_len', {'fmt': 'B'}),
                                       ('node_addr', {'fmt': 'H'}),
                                       ('profile_id', {'fmt': 'B'}),
                                       ('serial_num', {'fmt': 'B'})])
BASIC_PROTOCOL_PROPERTY = {**fixed_token_property, **content_property}

sub_fixed_token_property = OrderedDict([('fixed_token', {'default_value': 0xcb, 'fmt': 'B'})])
sub_content_property = OrderedDict([('serial_num', {'fmt': 'B'})])
SUB_PROTOCOL_PROPERTY = {**sub_fixed_token_property, **sub_content_property}

content_fields_list = ['data_len', 'node_addr', 'profile_id', 'serial_num', 'sub_fixed_token', 'sub_serial_num']


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


class ProtocolParamAttribute:
    __slots__ = ('fmt', 'default_value')

    def __init__(self, fmt):
        self.fmt = fmt

    def set_default_value(self, default_value):
        self.default_value = default_value


def create_class_protocol(protocol_name, protocol_fields):
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            # print(cls.__name__)
            # print(help(super(cls, cls)))
            # print(super(object, cls))
            # 笔记： super()方法在类的方法中使用可以省略参数而在函数外面必须填写参数
            # 笔记： super(cls,cls）调用父类的正确方法而不是super(object,cls)
            cls._instance = super(cls, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        self.header = OrderedDict()
        for field, property in protocol_fields.items():
            parameter = ProtocolParamAttribute(property.get('fmt'))
            default_value = property.get('default_value')
            if default_value:
                parameter.set_default_value(default_value)
            setattr(self, field, parameter)

            self.header[field] = parameter

        self.header_fmt = ''.join(c.fmt for c in self.header.values())
        self.endian = ENDIAN
        self.header_fmt_size = struct.calcsize(f'{self.endian}{self.header_fmt}')

    @classmethod
    def get_protocol(cls):
        return cls._instance if cls._instance else cls()
    return type(protocol_name, (), {
        '_instance': None,
        '__new__': __new__,
        '__init__': __init__,
        'get_protocol': get_protocol
    })


def create_class_package(package_name, protocol_type):

    def pack(cls, data, **kwargs):
        """
        关键字参数的参数名必须有已经在__slots__存在的合法字段
        :param cls:
        :param data:
        :param kwargs:
        :return:
        """
        # 验证关键字参数参数名是否和__slots__中的字段一一对应，假如缺少某一参数就报错
        try:
            to_be_packaged = [kwargs[arg] for arg in cls.__slots__]
        except Exception as why:
            print(f"缺少字段")
            print(why)

        complete_fmt = protocol_type.endian + protocol_type.header_fmt + f'{len(data)}s'
        # 打包头、数据
        values_bytes = struct.pack(complete_fmt, *to_be_packaged, data)

        return values_bytes

    def unpack(self, package):
        complete_fmt = protocol_type.endian + protocol_type.header_fmt
        for index, parameter in enumerate(struct.unpack_from(complete_fmt, package)):
            # 赋值属性
            setattr(self, self.__slots__[index], parameter)

    return type(package_name, (), {'__slots__': tuple(v for v in protocol_type.header.keys()),
                                   'pack': pack,
                                   'unpack': unpack}
                )


def create_class_fields(fields_name, protocol_type):
    def fields_init(self, package):
        # 解析得到包各个字段，然后顺序生成__slots中包含的的所有实例属性，并将字段的值赋值给实例属性
        # 字段顺序和slots中字段顺序一致
        package_fmt = protocol_type.endian + protocol_type.header_fmt
        # 按顺序
        for index, parameter in enumerate(struct.unpack(package_fmt, package)):
            # 赋值属性
            setattr(self, self.__slots__[index], parameter)
    return type(fields_name,(),{'__slots__': tuple(v for v in protocol_type.header.keys()),
                                       '__init__': fields_init}
                )


class Receipt:
    package_content_fmt = get_content_fmt(with_endian=True)
    package_content_fmt_len = struct.calcsize(package_content_fmt)
    attr = ['data_len','node_addr','profile_id','serial_num']

    def __init__(self, package_content):
        if not isinstance(package_content, bytes):
            raise Exception("package is not a bytes")
        for index, parameter in enumerate(struct.unpack_from(self.package_content_fmt, package_content)):
            # 赋值属性
            setattr(self, Receipt.attr[index], parameter)
        #TODO:在zigbee中由协调器发送过来消息填充一些ZigBee协议的字节
        self.sub_receipt = SubReceipt(package_content[Receipt.package_content_fmt_len:])


# 创建子协议类、该类为协议模板且是单例
SubProtocol = create_class_protocol('SubProtocol', SUB_PROTOCOL_PROPERTY)
# 创建协议类、该类为协议模板且是单例
Protocol = create_class_protocol('Protocol', BASIC_PROTOCOL_PROPERTY)

protocol = Protocol.get_protocol()
sub_protocol = SubProtocol.get_protocol()
# 创建包类,根据模板来创建，字段来自协议类
Package = create_class_package('Package', protocol)
# 创建子包类，根据模板来创建，字段来自子协议类
SubPackage = create_class_package('SubPackage', sub_protocol)



def complete_package(node_addr, profile_id, serial_num, data):
    if not isinstance(data, bytes):
        raise Exception("data is not a bytes")
    # 此处参数的赋值顺序会影响包实例的打包值顺序
    sub_package = SubPackage().pack(data=data, fixed_token=sub_protocol.fixed_token.default_value,
                                serial_num=serial_num)

    package = Package().pack(data=sub_package,fixed_token=protocol.fixed_token.default_value,
                      data_len=len(sub_package),
                      node_addr=node_addr,
                      profile_id=profile_id,
                      serial_num=serial_num)

    return package

def parse_package(package):
    if not isinstance(package, bytes):
        raise Exception("package is not a bytes")
    p = Package()
    p.unpack(package)
    sp = None
    data = b''
    # 假如只是来自协调器的包因为没有zigbee消息头所以不需要处理
    if p.node_addr is 0x0000:
        data = package[protocol.header_fmt_size:]
    else:
        if p.data_len > 0:
            sp = SubPackage()
            sp.unpack(package[protocol.header_fmt_size:])
            if p.data_len-sub_protocol.header_fmt_size > 0:
                data = package[protocol.header_fmt_size+sub_protocol.header_fmt_size:]
    return p, sp, data
