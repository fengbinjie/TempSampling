import logging.config
import os
import yaml
import logging.handlers
import core

LOGGING_FILE_DIR = os.path.join(core.PROJECT_DIR, 'log')
if not os.path.exists(LOGGING_FILE_DIR):
    os.mkdir(LOGGING_FILE_DIR)

LOGGING_FILE_PATH = 'log_setting.yml'

default_dict_conf = {
        'version': 1,
        'formatters': {
            'time_formatter': {
                "format": "%(asctime)s - %(name)s - %(pathname)s - %(lineno)d - %(levelname)s - %(message)s"
            }
        },
        'handlers': {
            'fileHandler': {
                'class': 'logging.handlers.RotatingFileHandler',
                'formatter': 'time_formatter',
                'level': 'DEBUG',
                'filename': os.path.join(LOGGING_FILE_DIR, 'server_log'),
                'maxBytes': 1000000000,
                'backupCount': 3
            },
            'consoleHandler': {
                'class': 'logging.StreamHandler',
                'formatter': 'time_formatter',
                'level': 'DEBUG',
                'stream': 'ext://sys.stdout'
            }
        },
        'root': {
            'level': 'DEBUG',
            'handlers': ['consoleHandler', 'fileHandler']
        },
        'asyncio': {
            'level': 'DEBUG',
            'handlers': ['fileHandler']
        }
    }
try:
    dict_conf = yaml.load(LOGGING_FILE_PATH)
    logging.config.dictConfig(dict_conf)
except:
    #print("配置文件不存在或错误")
    # 写入默认配置
    yaml.dump(default_dict_conf, LOGGING_FILE_PATH, 'w')
    #print("恢复默认")
    logging.config.dictConfig(default_dict_conf)
