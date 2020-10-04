from collections import OrderedDict
import struct
import core

_BASIC_PROTOCOL_PROPERTY = OrderedDict([('fixed_token', {'default_value': 0xabcd, 'fmt': 'H'}),
                         ('node_addr', {'fmt': 'H'}),
                         ('data_len', {'fmt': 'B'}),
                         ('profile_id', {'fmt': 'B'}),
                         ('serial_num', {'fmt': 'B'}),
                         ('client_id', {'fmt': 'B'})])\
    if core.MECHANISM else OrderedDict([('fixed_token', {'default_value': 0xabcd, 'fmt': 'H'}),
                         ('node_addr', {'fmt': 'H'}),
                         ('data_len', {'fmt': 'B'}),
                         ('profile_id', {'fmt': 'B'}),
                         ('serial_num', {'fmt': 'B'})])
_SUB_PROTOCOL_PROPERTY = OrderedDict([('fixed_token', {'default_value': 0xcb, 'fmt': 'B'}),
                       ('data_len', {'fmt': 'B'}),
                       ('profile_id', {'fmt': 'B'}),
                       ('serial_num', {'fmt': 'B'}),
                       ('client_id', {'fmt': 'B'})]) if core.MECHANISM else \
    OrderedDict([('fixed_token', {'default_value': 0xcb, 'fmt': 'B'}),
                       ('data_len', {'fmt': 'B'}),
                       ('profile_id', {'fmt': 'B'}),
                       ('serial_num', {'fmt': 'B'})])


class ProtocolParamAttribute:
    __slots__ = ('fmt', 'default_value')

    def __init__(self, fmt):
        self.fmt = fmt

    def set_default_value(self, default_value):
        self.default_value = default_value


def create_class_protocol(protocol_name, protocol_fields):
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            print(cls.__name__)
            print(help(super(cls, cls)))
            print(super(object, cls))
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
        self.header_fmt_size = struct.calcsize(''.join([c.fmt for c in self.header.values()]))
        self.endian = '<'

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

    def package_init(self, **kwargs):
        # 赋值顺序不影响值列表顺序打包顺序、因此关键词参数顺序不固定，但key必须与__slots__一致
        for parameter, value in kwargs.items():
            if parameter in self.__slots__:
                setattr(self, parameter, value)
            else:
                raise Exception("invalid keyword arguments")

    def package_value_list(self):
        # 改用self.__slots__来取值,由于self.__slots的顺序固定，因此值列表顺序确定，打包顺序确定
        return [getattr(self, arg) for arg in self.__slots__]


    def package_produce(self, data):
        complete_fmt = protocol_type.endian + protocol_type.header_fmt + f'{self.data_len}s'
        # 打包头、数据
        values_bytes = struct.pack(complete_fmt, *self.package_value_list(), data)

        return values_bytes

    def package_parse(self):
        pass

    return type(package_name, (), {'__slots__': tuple(v for v in protocol_type.header.keys()),
                                      '__init__': package_init,
                                      'produce': package_produce,
                                      'parse': package_parse,
                               'package_value_list': package_value_list}
               )


def create_class_fields(fields_name, protocol_type):
    def fields_init(self, package):
        # 解析得到包各个字段，然后顺序生成__slots中包含的的所有实例属性，并将字段的值赋值给实例属性
        # 字段顺序和slots中字段顺序一致
        package_fmt = protocol_type.endian + protocol_type.header_fmt
        # 按顺序
        for index, parameter in enumerate(struct.unpack_from(package_fmt, package)):
            # 赋值属性
            setattr(self, self.__slots__[index], parameter)
    return type(fields_name,(object,),{'__slots__': tuple(v for v in protocol_type.header.keys()),
                                                   '__init__': fields_init}
                      )


# 创建子协议类、该类为协议模板且是单例
SubProtocol = create_class_protocol('SubProtocol', _SUB_PROTOCOL_PROPERTY)
# 创建协议类、该类为协议模板且是单例
Protocol = create_class_protocol('Protocol', _BASIC_PROTOCOL_PROPERTY)

protocol = Protocol.get_protocol()
sub_protocol = SubProtocol.get_protocol()
# 创建包类,根据模板来创建，字段来自协议类
Package = create_class_package('Package', protocol)
# 创建子包类，根据模板来创建，字段来自子协议类
SubPackage = create_class_package('SubPackage', sub_protocol)
# 创建字段类,包含的字段为协议类中的字段
Fields = create_class_fields('Fields', protocol)
# 创建子字段类，包含的字段为子协议类中的字段
SubFields = create_class_fields('SubFields', sub_protocol)

if core.MECHANISM:
    def complete_package(node_addr, profile_id, serial_num, client_id, data):
        if not isinstance(data, bytes):
            raise Exception("data is not a bytes")
        # 此处参数的赋值顺序会影响包实例的打包值顺序
        sub_package = SubPackage(fixed_token=sub_protocol.fixed_token.default_value,
                                 data_len=len(data),
                                 profile_id=profile_id,
                                 serial_num=serial_num,
                                 client_id=client_id).produce(data)

        package = Package(fixed_token=protocol.fixed_token.default_value,
                          node_addr=node_addr,
                          data_len=len(sub_package),
                          profile_id=profile_id,
                          serial_num=serial_num,
                          client_id=client_id).produce(sub_package)

        #check_num = pack_check_num(package)
        #TODO: check应该在串口发送前计算
        return package
else:
    def complete_package(node_addr, profile_id, serial_num, data):
        if not isinstance(data, bytes):
            raise Exception("data is not a bytes")
        # 此处参数的赋值顺序会影响包实例的打包值顺序
        sub_package = SubPackage(fixed_token=sub_protocol.fixed_token.default_value,
                                 data_len=len(data),
                                 profile_id=profile_id,
                                 serial_num=serial_num).produce(data)

        package = Package(fixed_token=protocol.fixed_token.default_value,
                          node_addr=node_addr,
                          data_len=len(sub_package),
                          profile_id=profile_id,
                          serial_num=serial_num).produce(sub_package)

        # check_num = pack_check_num(package)
        # TODO: check应该在串口发送前计算
        return package


def parse_package(package):
    if not isinstance(package,bytes):
        raise Exception("package is not a bytes")
    reverse_package = Fields(package)
    reverse_sub_package = None
    data = b''
    if reverse_package.data_len > 0:
        reverse_sub_package = SubFields(package[protocol.header_fmt_size:])
        if reverse_sub_package.data_len > 0:
            data = package[protocol.header_fmt_size+sub_protocol.header_fmt_size:]
    return reverse_package, reverse_sub_package, data


def check(buf):
    xor_result = 0
    for v in buf:
        xor_result = xor_result ^ v
    return xor_result


def pack_check_num(value_bytes):
    # 打包校验码
    return struct.pack(f'{protocol.endian}B', check(value_bytes))