from collections import OrderedDict
import struct


class ProtocolParamAttribute:
    __slots__ = ('index', 'fmt', 'default_value')

    def __init__(self, index, fmt):
        self.index, self.fmt, self.default_value = index, fmt, None

    def set_default_value(self, default_value):
        self.default_value = default_value


class Sub_Protocol:
    _instance = None
    __slots__ = ('fixed_token', 'data_len', 'client_id', 'serial_num', 'profile_id', 'header', 'header_fmt',
                 'header_fmt_size', 'endian')

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        self.fixed_token = ProtocolParamAttribute(1, 'B')
        self.data_len = ProtocolParamAttribute(2, 'B')
        self.profile_id = ProtocolParamAttribute(3, 'B')
        self.serial_num = ProtocolParamAttribute(4, 'B')
        self.client_id = ProtocolParamAttribute(5, 'B')
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
        self.header_fmt_size = sum({'B': 1, 'H': 2, 'I': 4}[c.fmt] for c in self.header.values())
        self.endian = '<'


    @classmethod
    def get_sub_protocol(cls):
        return cls._instance if cls._instance else cls()


class _Protocol:
    # TODO: 该类应该可以动态生成
    _instance = None
    __slots__ = ('fixed_token', 'node_addr', 'data_len', 'profile_id', 'serial_num', 'client_id', 'header',
                 'header_fmt', 'header_fmt_size', 'endian')

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        self.fixed_token = ProtocolParamAttribute(1, 'H')
        self.node_addr = ProtocolParamAttribute(2, 'H')
        self.data_len = ProtocolParamAttribute(3, 'B')
        self.profile_id = ProtocolParamAttribute(4, 'B')
        self.serial_num = ProtocolParamAttribute(5, 'B')
        self.client_id = ProtocolParamAttribute(6, 'B')

        self.fixed_token.set_default_value(0xabcd)

        # 将所有协议头格式存在header_content顺序字典中
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
        self.header_fmt_size = sum({'B': 1, 'H': 2, 'I': 4}[c.fmt] for c in self.header.values())
        self.endian = '<'

    @classmethod
    def get_protocol(cls):
        return cls._instance if cls._instance else cls()




def get_package_methods(protocol):

    def package_init(self, **kwargs):
        for parameter, value in kwargs.items():
            if parameter in self.__slot__:
                setattr(self, parameter, value)
            else:
                raise Exception("invalid keyword arguments")

        self.package_value_list = kwargs.values()

    def package_produce(self, data):
        complete_fmt = protocol.endian + protocol.header_fmt + f'{self.data_len}s'
        # 打包头、数据
        values_bytes = struct.pack(complete_fmt, *self.package_value_list, data)

        return values_bytes

    def package_parse(self):
        pass

    return package_init, package_produce, package_parse


protocol = _Protocol.get_protocol()
package_init, package_produce, package_parse = get_package_methods(protocol)
Package = type('Package', (object,), {'__slot__': tuple(v for v in protocol.header.keys()),
                                      '__init__': package_init,
                                      'produce': package_produce,
                                      'parse': package_parse}
               )

sub_protocol = Sub_Protocol.get_sub_protocol()
package_init, package_produce, package_parse = get_package_methods(sub_protocol)
Sub_Package = type('Sub_Package', (object,), {'__slot__': tuple(v for v in sub_protocol.header.keys()),
                                              '__init__': package_init,
                                              'produce': package_produce,
                                              'parse': package_parse}
                   )


def complete_package(node_addr, profile_id, serial_num, client_id, data):
    if not isinstance(data, bytes):
        raise Exception("arguments is not a bytes")
    # 此处参数的赋值顺序会影响包实例的打包值顺序
    sub_package = Sub_Package(fixed_token=sub_protocol.fixed_token.default_value,
                              data_len=len(data),
                              profile_id=profile_id,
                              serial_num=serial_num,
                              client_id=client_id).produce(data)

    package = Package(fixed_token=protocol.fixed_token.default_value,
                      node_addr=0,
                      data_len=len(sub_package),
                      profile_id=profile_id,
                      serial_num=serial_num,
                      client_id=client_id).produce(sub_package)

    check_num = pack_check_num(package)
    return package+check_num


def check(buf):
    xor_result = 0
    for v in buf:
        xor_result = xor_result ^ v
    return xor_result


def pack_check_num(value_bytes):
    # 打包校验码
    return struct.pack(f'{protocol.endian}B', check(value_bytes))