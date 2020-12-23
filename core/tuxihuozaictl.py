import argparse
import cmd
import inspect
import json
import logging
import socket
import sys
import os
import yaml

import core

default_log_config = {

}
default_config_path = core.PROJECT_DIR+'/tuxihuozaictl.yml'
default_config = {

}
class CustomizeArgumentParser(argparse.ArgumentParser):

    def suppress_help(self):
        pass
    # ===============
    # Exiting methods
    # ===============
    # 重写该方法是为了调用-h或--help时客户端不会被退出
    def exit(self, status=0, message=None):
        if message:
            self._print_message(message, sys.stderr)
        # 永不退出
        # _sys.exit(status)

    # costomize error method to raise ArgumentError instead of exit
    def error(self, message):
        """error(message: string)

        Prints a usage message incorporating the message to stderr and
        exits.

        If you override this in a subclass, it should not return -- it
        should either exit or raise an exception.
        """
        self.print_usage(sys.stderr)
        message = f'{self.prog}: error: {message}\n'
        if message:
            self._print_message(message, sys.stderr)
        raise AttributeError

class Controller(cmd.Cmd):

    def __init__(self, completekey='tab'):
        # 获得配置好的日志器
        try:
            logging.basicConfig(**default_log_config)
        except ValueError as why:
            logging.critical("日志器配置错误\nwhy")
            self.close()
            exit() # 关闭资源
        else:
            self.logger = logging.getLogger()
        # 获得客户端配置
        if not os.path.exists(default_config_path):
            # 配置文件不存在，在默认地址写入默认文件
            with open(file=default_config_path,mode='x') as f:
                try:
                    yaml.dump(default_config,f)
                except Exception as why:
                    self.logger.critical("默认客户端配置错误")
                    self.close()
                    exit()
            self.config = default_config
        else:
            # 配置文件存在，就读取配置文件
            with open(default_config_path, 'r') as f:
                try:
                    self.config = yaml.load(f,Loader=yaml.FullLoader)
                except Exception as why:
                    self.logger.critical("客户端配置文件项目错误")
                    self.close()
                    exit()

        # 连接到服务器
        server_ip, port = self.config["address"], self.config["port"]
        self.proxy = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.proxy.settimeout(1800)
        try:
            self.proxy.connect((server_ip, port))
        except Exception as why:
            self.logger.critical(f"目标位置 {server_ip}:{port} 的tuxihuozaiserver无法连接")
            self.close()
            exit()
        else:
            pass
            # 检视服务器
            # self.proxy.status = True
            #self.inspect_server()

        # 启动交互
        super().__init__(completekey)
        self.intro = "welcome"
        self.prompt = 'tuxihuozaictl' + '>'
        # 子命令
        self.led_args = ('set', 'clear','get')
        self.list_args = ('nodes', 'ports')
        self.temp_args = ('start', 'stop','pause','resume')


    def inspect_server(self):
        response = self.recv(1024)
        response = json.loads(response.decode())
        funcs = response["feedback"]
        self.funcs = funcs

    def emptyline(self):
        # 输入空行时，任何事都不做
        return

    def default(self, line):
        print(f'*** Unknown syntax: {line}')

    def send(self,data):
        """

        :param data:
        :return: 三种返回值，返回True代表将结束客户端
        返回False代表将结束当前任务
        返回整型值代表发送的数据长度
        """
        try:
            length = self.proxy.send(data)
        except socket.timeout as why:
            # todo 在屏幕上打印这个错误且不退出,返回None
            self.logger.warning(f"接收过程中出现错误，接收操作超时\n{why}")
            return False
        except socket.error as why:
            self.logger.critical(f"发送过程中出现错误，连接被服务器关闭\n{why}")
            return True
        else:
            return length

    def recv(self,length=4096):
        """

                :param length:
                :return: 三种返回值，返回True代表将结束客户端
                返回False代表将结束当前任务
                返回整型值代表发送的数据长度
                """
        try:
            result = self.proxy.recv(length)
        except socket.timeout as why:
            # todo 在屏幕上打印这个错误且不退出,返回None
            self.logger.warning(f"接收过程中出现错误，接收操作超时\n{why}")
            return False  # 结束当前任务
        except socket.error as why:
            self.logger.critical(f"接收过程中出现错误，连接被服务器关闭\n{why}")
            return True  # 结束客户端
        else:
            return result

    def do_temp(self,args):
        # 温度相关命令
        self.logger.info(f"执行temp {args['sub_command']} 命令")
        name = 'temp'
        enquire = json.dumps({"enquire": name, "args": args})
        self.send(enquire.encode())
        try:
            while True:
                result = self.recv()
                # 有一个错误
                if isinstance(result, bool):
                    return result
                # 没有错误
                r = json.loads(result)
                # 接收到结束符才结束
                if r == "eof":
                    break
                print(r)
        except KeyboardInterrupt:
            # todo:配置日志器要既打印到屏幕也打印到日志文件中
            self.logger.warning(f"中断执行temp {args['sub_command']} 命令")

    def parse_led_args(self,args):
        if args:
            def led_from_file(file):
                try:
                    with open(file, mode='r', encoding="utf-8") as f:
                        content = yaml.load(f,yaml.FullLoader)
                except:
                    raise
                else:
                    return content

            led_parser = CustomizeArgumentParser(prog="led")
            led_sub_parser = led_parser.add_subparsers(help="temp subcommand help")

            led_set_parser = led_sub_parser.add_parser('set')
            led_set_parser.add_argument('node', dest="node")
            led_set_parser.add_argument('file', dest="file",type=led_from_file)

            led_clear_parser = led_sub_parser.add_parser('clear')
            clear_mutual_parser = led_clear_parser.add_mutually_exclusive_group(require=True)
            clear_mutual_parser.add_argument('-n', dest="node")
            clear_mutual_parser.add_argument('-a', dest="all",action="store_true")

            led_get_parser = led_sub_parser.add_parser('get')
            get_mutual_parser = led_get_parser.add_mutually_exclusive_group(require=True)
            get_mutual_parser.add_argument('-n', dest="node")
            get_mutual_parser.add_argument('-a', dest="all", action="store_true")


            try:
                args_list = args.split()
                args = led_parser.parse_args(args_list)
            except:
                raise
            else:
                self.suppress_help_out(args_list)
                args_dict = {"sub_command": args_list[0]}
                args_dict.update(vars(args))
                return args_dict
        else:
            self.help_led()
            raise AttributeError

    def do_led(self, args):
        self.logger.info(f"执行led {args['sub_command']}命令")
        name = 'led'
        enquire = json.dumps({"enquire": name, "args": args})
        self.send(enquire.encode())
        try:
            result = self.recv()
            print(json.loads(result))
        except KeyboardInterrupt:
            # todo:配置日志器要既打印到屏幕也打印到日志文件中
            self.logger.warning(f"中断执行led {args['sub_command']} 命令")

    def parse_temp_args(self,args):
        if args:
            temp_parser = CustomizeArgumentParser(prog="temp")
            temp_sub_parsers = temp_parser.add_subparsers(help = "temp subcommand help")
            temp_start_parser = temp_sub_parsers.add_parser('start')
            temp_start_parser.add_argument('-i',dest="interval")
            temp_start_parser.add_argument('-t',dest="time")
            temp_stop_parser = temp_sub_parsers.add_parser('stop')
            temp_pause_parser = temp_sub_parsers.add_parser('pause')
            temp_resume_parser = temp_sub_parsers.add_parser('resume')

            try:
                args_list = args.split()
                args = temp_parser.parse_args(args_list)
            except:
                raise
            else:
                self.suppress_help_out(args_list)
                # 解析成功说明子命令一定没错
                args_dict = {"sub_command":args_list[0]}
                args_dict.update(vars(args))
                return args_dict
        else:
            self.help_temp()
            raise AttributeError

    def parse_list_args(self,args):
        if args:
            list_parser = CustomizeArgumentParser(prog="led")
            list_sub_parsers = list_parser.add_subparsers(help="temp sub_command help")
            list_sub_parsers.add_parser('ports')
            list_sub_parsers.add_parser('nodes')
            try:
                args_list = args.split()
                args = list_parser.parse_args(args_list)
            except:
                raise
            else:
                self.suppress_help_out(args_list)
                args_dict = {"sub_command":args_list[0]}
                args_dict["args"] = vars(args)
                return args_dict
        else:
            self.help_list()

    def suppress_help_out(self,arg_list):
        if '-h' in arg_list or '--help' in arg_list:
            raise AttributeError

    def do_list(self, args):
        #todo:多次执行list_nodes出现json错误
        self.logger.info(f"执行list {args['sub_command']} 命令")
        # 解析命令
        name = 'list'
        args["command"] =name
        enquire = json.dumps(args)
        self.send(enquire.encode())
        try:
            result = self.recv()
        except KeyboardInterrupt:
            # todo:配置日志器要既打印到屏幕也打印到日志文件中
            self.logger.warning(f"中断执行temp {args['sub_command']} 命令")
            # 有一个错误
        else:
            # if isinstance(result,bool):
            #     return result
            # 没有错误
            if result:
                # 处理函数
                print(json.loads(result))
            else: # 服务器退出
                # 退出
                self.logger.critical("服务器退出")
                return True




    def do_exit(self, args):
        # 手动退出
        # 返回值程序循环退出
        return True

    def get_func_name(self):
        return inspect.stack()[1][3]

    def help_list(self):
        print('help: Show all nodes in zigbee Currently')

    def help_led(self):
        print("help: led")

    def help_temp(self):
        print("help: temp")

    def completedefault(self, text, line, begidx, endidx):
        # 确定命令存在
        command = line.split()[0]
        try:
            getattr(self, 'do_' + command)
        except AttributeError:
            return [] # 没有该命令返回空
        # 补全参数或打印全部参数
        try:
            completions = getattr(self,command+'_args')
        except AttributeError:
            # 没有参数返回空
            return []
        if text:
            completions = [f for f in completions if f.startswith(text)]
        return completions

    def onecmd(self, line):
        """Interpret the argument as though it had been typed in response
        to the prompt.

        This may be overridden, but should not normally need to be;
        see the precmd() and postcmd() methods for useful execution hooks.
        The return value is a flag indicating whether interpretation of
        commands by the interpreter should stop.

        """
        cmd, args, line = self.parseline(line)
        if not line:
            return self.emptyline()
        if cmd is None:
            return self.default(line)
        self.lastcmd = line
        if line == 'EOF' :
            self.lastcmd = ''
        if cmd == '':
            return self.default(line)
        else:
            # 解析函数，目前只有exit命令没有参数解析器ArgumentParser
            parse_func = getattr(self, 'parse_' + cmd + '_args', None)
            try: # 假如解析函数存在，但参数为空字符串则报错,解析失败也报错
                _args = parse_func(args) if parse_func else args
            except AttributeError:
                return
            else:
                try:
                    # 执行函数
                    func = getattr(self, 'do_' + cmd)
                except AttributeError:
                    return self.default(line)
                else:
                    return func(_args)

    def postloop(self):
        """
        #客户端已经运行起来时出现异常调用该函数来关闭
        :return:
        """
        self.close()

    def close(self):
        """
        关闭资源
        :return:
        """
        if self.proxy and (not self.proxy._closed):
            self.proxy.close()
        if getattr(self,"logger",None):
            self.logger.info("执行exit\n客户端关闭")
        else:
            logging.info("执行exit\n客户端关闭")

if __name__ == '__main__':
    Controller().cmdloop()

