import cmd
import socket
import json
import time
import inspect

class Controller(cmd.Cmd):

    def __init__(self, completekey='tab'):
        # try:
        #     self.proxy = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        #     self.proxy.connect(('localhost', 10000))
        # except:
        #     #todo:修改具体异常
        #     raise Exception

        super().__init__(completekey)
        self.intro = "welcome"
        self.prompt = 'tuxihuozaictl' + '>'
        self.list_args = ['nodes','ports']
        self.led_args = ['write','all']
        self.temp_args = ['start','stop']
        server_info = ('localhost', 10000)
        self.proxy = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.proxy.connect(server_info)
        except:
            raise Exception("tuxihuozaiserver未启动")
        else:
            self.inspect_server()

    def inspect_server(self):
        response = self.proxy.recv(1024)
        response = json.loads(response.decode())
        funcs = response["feedback"]
        self.funcs = funcs

    def emptyline(self):
        # 输入空行时，任何事都不做
        return

    def default(self, line):
        self.output(f'*** Unknown syntax: {line}')

    def do_temp(self,arg):
        if arg in self.temp_args:
            if arg == 'start':
                print('start to sampling temp')
            elif arg == 'stop':
                print('stop sampling temp')
        else:
            self.help_temp()

    def do_led(self,arg):
        if arg in self.list_args:
            if arg == 'write':
                print('write led sequence to node\'s rom')
            elif arg == 'all':
                print('Show all node-led mapping')
        else:
            self.help_list()

    def parse_args(self,args):
        return args.split()

    def do_list(self, args):
        name = self.get_func_name()[3:] # 去掉do_部分
        args = self.parse_args(args)
        name = f'{name}_{args[0]}'
        enquire = json.dumps({"enquire": name,"args": args[1:]})
        if args[0] in self.list_args:
            self.proxy.send(enquire.encode())
            try:
                print(self.proxy.recv(1024).decode())
            except KeyboardInterrupt:
                pass
        else:
            self.help_list()

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

if __name__ == '__main__':
    Controller().cmdloop()

