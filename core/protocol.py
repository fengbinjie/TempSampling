from collections import OrderedDict
import struct

_BASIC_PROTOCOL_PROPERTY = OrderedDict([('fixed_token', 'H'),
                         ('node_addr', 'H'),
                         ('data_len', 'B'),
                         ('profile_id', 'B'),
                         ('serial_num', 'B'),
                         ('client_id', 'B')])

_SUB_PROTOCOL_PROPERTY = OrderedDict([('fixed_token', 'B'),
                       ('data_len', 'B'),
                       ('profile_id', 'B'),
                       ('serial_num', 'B'),
                       ('client_id', 'B')])


class ProtocolParamAttribute:
    __slots__ = ('index', 'fmt', 'default_value')

    def __init__(self, index, fmt):
        self.index, self.fmt, self.default_value = index, fmt, None

    def set_default_value(self, default_value):
        self.default_value = default_value


class SubProtocol:
    _instance = None
    # TODO:使用某种有次序存储形式，由此来反射生成元祖
    __slots__ = ('fixed_token', 'data_len', 'profile_id', 'serial_num','client_id', 'header', 'header_fmt',
                 'header_fmt_size', 'endian')

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        self.fixed_token = ProtocolParamAttribute('B')
        self.data_len = ProtocolParamAttribute('B')
        self.profile_id = ProtocolParamAttribute('B')
        self.serial_num = ProtocolParamAttribute('B')
        self.client_id = ProtocolParamAttribute('B')
        self.fixed_token.set_default_value(0xcb)
        self.header = OrderedDict()

        for var in self.__slots__:
            try:
                value = getattr(self, var)
            except:
                pass
            else:
                if isinstance(value, ProtocolParamAttribute):
                    self.header[var] = value

        self.header_fmt = ''.join(c.fmt for c in self.header.values())
        self.header_fmt_size = struct.calcsize(''.join([c.fmt for c in self.header.values()]))
        self.endian = '<'


    @classmethod
    def get_sub_protocol(cls):
        return cls._instance if cls._instance else cls()


class Protocol:
    # TODO: 该类应该可以动态生成
    _instance = None
    __slots__ = ('fixed_token', 'node_addr', 'data_len', 'profile_id', 'serial_num', 'client_id', 'header',
                 'header_fmt', 'header_fmt_size', 'endian')

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        self.fixed_token = ProtocolParamAttribute('H')
        self.node_addr = ProtocolParamAttribute('H')
        self.data_len = ProtocolParamAttribute('B')
        self.profile_id = ProtocolParamAttribute('B')
        self.serial_num = ProtocolParamAttribute('B')
        self.client_id = ProtocolParamAttribute('B')

        self.fixed_token.set_default_value(0xabcd)

        # 将所有协议头格式存在header_content顺序字典中
        self.header = OrderedDict()
        # TODO: 对header中的项按照ProtocolParamAttribute.index顺序进行排序
        for var in self.__slots__:
            try:
                value = getattr(self, var)
            except:
                pass
            else:
                if isinstance(value, ProtocolParamAttribute):
                    self.header[var] = value


        self.header_fmt = ''.join(c.fmt for c in self.header.values())
        # 协议头数据格式尺寸
        self.header_fmt_size = struct.calcsize(''.join([c.fmt for c in self.header.values()]))
        self.endian = '<'

    @classmethod
    def get_protocol(cls):
        return cls._instance if cls._instance else cls()




def get_package_methods(protocol):

    def package_init(self, **kwargs):
        #TODO:改用self.__slots__来赋值
        for parameter, value in kwargs.items():
            if parameter in self.__slot__:
                setattr(self, parameter, value)
            else:
                raise Exception("invalid keyword arguments")
        # 赋值顺序影响列表顺序，从而影响打包顺序
        self.package_value_list = kwargs.values()

    def package_produce(self, data):
        complete_fmt = protocol.endian + protocol.header_fmt + f'{self.data_len}s'
        # 打包头、数据
        values_bytes = struct.pack(complete_fmt, *self.package_value_list, data)

        return values_bytes

    def package_parse(self):
        pass

    return package_init, package_produce, package_parse


protocol = Protocol.get_protocol()
package_init, package_produce, package_parse = get_package_methods(protocol)
Package = type('Package', (object,), {'__slot__': tuple(v for v in protocol.header.keys()),
                                      '__init__': package_init,
                                      'produce': package_produce,
                                      'parse': package_parse}
               )

sub_protocol = SubProtocol.get_sub_protocol()
package_init, package_produce, package_parse = get_package_methods(sub_protocol)
SubPackage = type('SubPackage', (object,), {'__slot__': tuple(v for v in sub_protocol.header.keys()),
                                              '__init__': package_init,
                                              'produce': package_produce,
                                              'parse': package_parse}
                  )


def get_fields_method(protocol):
    def fields_init(self, package):
        package_fmt = protocol.endian + protocol.header_fmt
        for index, parameter in enumerate(struct.unpack_from(package_fmt, package)):
            setattr(self, self.__slots__[index], parameter)
    return fields_init


fields_init = get_fields_method(protocol)
ReversePackage = type('ReversePackage',(object,),{'__slots__': tuple(v for v in protocol.header.keys()),
                                                   '__init__': fields_init}
                      )

fields_init = get_fields_method(sub_protocol)
ReverseSubPackage = type('ReverseSubPackage',(object,),{'__slots__': tuple(v for v in sub_protocol.header.keys()),
                                                        '__init__': fields_init}
                         )

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


def parse_package(package):
    if not isinstance(package,bytes):
        raise Exception("package is not a bytes")
    reverse_package = ReversePackage(package)
    reverse_sub_package = None
    data = b''
    if reverse_package.data_len > 0:
        reverse_sub_package = ReverseSubPackage(package[protocol.header_fmt_size:])
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