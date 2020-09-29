from collections import OrderedDict
import struct
class ProtocolParamAttribute:
    def __init__(self, index, fmt, value):
        self.index, self.fmt, self.value = index, fmt, value


class Sub_Protocol:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        self.fixed_token = ProtocolParamAttribute(1,'B',0xcb)
        self.LEN = ProtocolParamAttribute(2,'B',None)
        self.client_id = ProtocolParamAttribute(3,'B',None)
        self.dest_addr = ProtocolParamAttribute(4,'H',None)
        self.profile_id = ProtocolParamAttribute(5,'B',None)
        self.serial_num = ProtocolParamAttribute(6,'B',None)
        self.header = OrderedDict()
        for var, value in self.__dict__.items():
            if isinstance(value, ProtocolParamAttribute):
                self.header[var] = value

        self.header_fmt = ''.join([v.fmt for v in self.header.values()])
        self.header_fmt_size = sum({'B': 1, 'H': 2, 'I': 4}[c.fmt] for c in self.header.values())
        self.endian = '<'
        self.data = None

    def _set_header(self,LEN,client_id,dest_addr,profile_id,serial_num):
        kwargs = locals()
        kwargs.pop('self')
        for var_name, var_value in kwargs.items():
            self.header[var_name].value = var_value

    def _get_header_content(self):
        return [v.value for v in self.header.values()]

    def produce_sub_package(self, LEN, client_id, dest_addr, profile_id, serial_num, DATA):
        self._set_header(LEN, client_id,dest_addr,profile_id,serial_num)
        complete_fmt = self.endian + self.header_fmt + f'{LEN}s'
        # 打包头、数据
        values_bytes = struct.pack(complete_fmt, *(self._get_header_content()), DATA)

        return values_bytes

    def unpack_bytes(self, acquired_bytes):
        fixed_token,\
        LEN, \
        client_id, \
        dest_addr, \
        profile_id,\
        serial_number = struct.unpack_from(self.endian+self.header_fmt, acquired_bytes)
        data = struct.unpack_from(f'{self.endian}{LEN}s', acquired_bytes, offset=self.header_fmt_size)
        return data

    @classmethod
    def get_sub_protocol(cls):
        return cls._instance if cls._instance else cls()


class _Protocol:
    # TODO: 该类应该可以动态生成
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        self.fixed_token = ProtocolParamAttribute(1, 'H', 0xabcd)
        self.reservered_token = ProtocolParamAttribute(2, 'H', 0x0000)
        self.D_LEN = ProtocolParamAttribute(3, 'B', None)
        self.device_type = ProtocolParamAttribute(4, 'B', None)
        self.profile_id = ProtocolParamAttribute(5, 'H', None)
        self.serial_number = ProtocolParamAttribute(6, 'B', None)
        self.client_id = ProtocolParamAttribute(7, 'B', None)

        # 将所有协议头格式存在header_content顺序字典中
        self.header = OrderedDict()
        for var, value in self.__dict__.items():
            if isinstance(value, ProtocolParamAttribute):
                self.header[var] = value

        self.header_fmt = ''.join(c.fmt for c in self.header.values())
        self.header_fmt_size = sum({'B': 1, 'H': 2, 'I': 4}[c.fmt] for c in self.header.values())
        self.endian = '<'

    @staticmethod
    def _get_protocol_from_file(path):
        with open_file(path) as f:
            try:
                protocol_dict = yaml.load(f)
            except yaml.YAMLError as why:
                print("error format")
            else:
                return protocol_dict

    @classmethod
    def get_protocol(cls):
        return cls._instance if cls._instance else cls()

def check(buf):
    xor_result = 0
    for v in buf:
        xor_result = xor_result ^ v
    return xor_result

sub_protocol = Sub_Protocol.get_sub_protocol()
protocol = _Protocol.get_protocol()




def package_init(self, **kwargs):
    print(self.__slot__)
    print(kwargs)
    for parameter, value in kwargs.items():
        if parameter in self.__slot__:
            setattr(self, parameter, value)
        else:
            raise Exception("invalid keyword arguments")

    self.package_value_list = kwargs.values()

def package_produce(self, DATA):
    complete_fmt = protocol.endian + protocol.header_fmt + f'{self.D_LEN}s'
    # 打包头、数据
    values_bytes = struct.pack(complete_fmt, *self.package_value_list, DATA)
    # 打包校验码
    check_byte = struct.pack(f'{protocol.endian}B', check(values_bytes))

    return values_bytes + check_byte

def package_parse(self):
    pass


Package = type('Package', (object,), {'__slot__': tuple(v for v in protocol.header.keys()),
                                      '__init__': package_init,
                                      'produce': package_produce,
                                      'parse': package_parse}
               )

def sub_package_produce(self, DATA):
    complete_fmt = sub_protocol.endian + sub_protocol.header_fmt + f'{self.LEN}s'
    # 打包头、数据
    values_bytes = struct.pack(complete_fmt, *self.package_value_list, DATA)
    # 打包校验码
    return values_bytes

def sub_package_parse(self):
    pass

Sub_Package = type('Sub_Package', (object,),{'__slot__': tuple(v for v in sub_protocol.header.keys()),
                                             '__init__': package_init,
                                             'produce': sub_package_produce,
                                             'parse': sub_package_parse}
                   )

def complete_package(device_type,profile_id,serial_num,client_id,dest_addr,Data):
    if not isinstance(Data, bytes):
        raise Exception("arguements is not a bytes")

    sub_package = sub_protocol.produce_sub_package(len(Data), client_id, dest_addr, profile_id, serial_num, Data)
    package = protocol.produce_package(len(sub_package), device_type, profile_id, serial_num, client_id, sub_package)
    return package

def parse_package(package):
    protocol.get_header_content(package)
    pass