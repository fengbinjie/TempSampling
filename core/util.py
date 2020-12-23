import yaml

def check(buf):
    xor_result = 0
    for v in buf:
        xor_result = xor_result ^ v
    return xor_result

def get_setting(file):
    """
    以yaml格式解析yaml文件
    :param file:
    :return: 字典形式的属性集合
    """
    try:
        with open(file) as f:
            setting_dict = yaml.load(f, Loader=yaml.FullLoader)
    except FileNotFoundError as why:
        print(why)
        exit()
    else:
        return setting_dict


def write_setting(file, **kwargs):
    """
    将参数中的键值对写入setting.yml文件
    :param file:
    :param kwargs:
    :return:
    """
    setting_dict = get_setting(file)
    setting_dict_keys = setting_dict.keys()
    for k, v in kwargs.items():
        # 如果setting存在被给属性且属性值的类型和参数中给的值的类型相同则写入
        if k in setting_dict_keys and isinstance(v, type(setting_dict[k])):
            setting_dict[k] = v
        else:
            raise Exception("不存在该属性或值错误")
    # 将字典以yaml的格式写入
    with open(file, mode='w') as f:
        yaml.dump(setting_dict, f)

class TableDisplay:
    """
    """
    def __init__(self, *headers):
        for header in headers:
            if not isinstance(header, str):
                raise Exception("传入参数不是所要求的的字符串")
        self.headers = headers
        self.headers_num = len(headers)
        self.table = ''
        self.table_width = 0
        # 行高
        self.row_height = 1
        # 每一列的最宽数据宽度
        self.max_col_content_widths = [self.get_str_print_len(item) for item in headers]
        # 存储每次添加的值[list...list]
        self.values_list = []

    def add_row(self, *items_value):
        # 检查数目是否正确
        if len(items_value) is not self.headers_num:
            raise Exception('传入参数值数量错误')
        # 检查项目值是否正确
        for index, value in enumerate(items_value):
            if not isinstance(value, str):
                raise Exception(f'传入参数值{value}不是字符串')
            # 循环，假如新的数据宽度大于旧的，就更新新列宽
            origin_width = self.max_col_content_widths[index]
            new_width = self.get_str_print_len(value)
            if new_width > origin_width:
                self.max_col_content_widths[index] = new_width
        self.values_list.append(items_value)  # 添加到值列表中

    def update_table_width(self):
        # 每一列两边至少留出2个空格的大小

        # 表格宽度 = 每一列列宽之和
        self.table_width = sum(self.max_col_widths)

    def update_col_widths(self):
        # 列宽 = 2*2+最宽数据宽度
        self.max_col_widths = [content_width + 2 * 2 for content_width in self.max_col_content_widths]

    def set_row_height(self, height):
        # 设定每行的行高
        self.row_height = height if height > 0 else 1

    def new_line(self):
        # 换行
        self.table = self.table + self.row_height * '\n'

    def generate_row(self, data_list):
        row = '|'
        for index, data in enumerate(data_list):
            # 获得最佳插入值位置
            col_width = self.max_col_widths[index]
            op_location = (col_width - self.get_str_print_len(data)) // 2
            # 形成行
            row = row + op_location * ' ' + data + (col_width - op_location - self.get_str_print_len(data)) * ' ' + '|'
        return row

    def table_border(self):
        border = ''
        # 线的组成
        meta = '- '
        # 格子与格子之间线的分隔
        separator = '+'
        # 生成 类似+- - - - - +- - - - - +- - - - - +的字符串
        for width in self.max_col_widths:
            # 生成- - - - - 字符串
            grid_border = meta * (width // 2) if width % 2 == 0 else meta * (width // 2) + '-'
            border += separator + grid_border
        border += separator
        return border

    def generate_header(self):
        """
        根据给定的表头生成
        +- - - - - +- - - - - +- - - - - +
        |  field1  |  field2  |  field3  |
        +- - - - - +- - - - - +- - - - - +
        如下的表头
        :return: 表头字串
        """
        table_border = self.table_border()
        # 生成 |  field1  |  field2  |  field3  |
        header = table_border + '\n' + self.generate_row(self.headers)
        header = header + '\n' + table_border
        return header

    def get_str_print_len(self, strs):
        length = 0
        for _char in strs:
            #假如是中文长度+2
            length += 2 if '\u4e00' <= _char <= '\u9fa5' else 1
        return length

    def __str__(self):
        # 更新每一列的最大宽度
        self.update_col_widths()
        # 更新表格宽度
        self.update_table_width()
        # 写表头
        self.table = self.generate_header()
        # 值存在继续写值
        # 找到每个格子最中间的位置填写值
        for row_data_list in self.values_list:
            # 换行
            self.new_line()
            self.table = self.table + self.generate_row(row_data_list)
        # 返回列表字符串
        self.new_line()
        # 底部边界
        self.table += self.table_border()
        return self.table


if __name__ == '__main__':

    table = TableDisplay('field1', 'field2eafe冯斌杰', 'field3分半')
    table.add_row('1', 'feng冯斌杰诶', 'binjie')
    table.add_row('2封闭呢', 'fea', 'feafea')
    print(table)
    # import timeit
    # t = timeit.Timer('str(table)','from __main__ import table')
    # print(t.repeat(4, 1000))
