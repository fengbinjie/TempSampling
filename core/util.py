import yaml


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