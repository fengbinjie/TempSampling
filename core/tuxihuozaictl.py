import cmd
import xmlrpc.client

class Controller(cmd.Cmd):

    def __init__(self, completekey='tab'):
        super().__init__(completekey)
        self.intro = "welcome"
        self.prompt = 'tuxihuozaictl' + '>'
        self.list_args = ['nodes','ports']
        self.led_args = ['write','all']
        self.temp_args = ['start','stop']
        self.server_info = ''

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

    def do_list(self, arg):
        if arg in self.list_args:
            if arg == 'nodes':
                print('Show all nodes in zigbee Currently')
            elif arg == 'ports':
                print('Show serial ports list')
        else:
            self.help_list()

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

