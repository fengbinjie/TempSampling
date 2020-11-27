import cmd
import xmlrpc.client

class Controller(cmd.Cmd):

    def __init__(self, options, completekey='tab', stdin=None, stdout=None):
        self.options = options
        self.prompt = self.options.prompt + '>'
        cmd.Cmd.__init__(completekey,stdin,stdout)
        try:
            self.proxy = xmlrpc.client.ServerProxy("http://localhost:8000/")
        except:
            exit()


    def emptyline(self):
        # 输入空行时，任何事都不做
        return

    def default(self, line):
        self.output(f'*** Unknown syntax: {line}')

    # def exec_cmdloop(self, args, ):
    #     pass
    # def cmdloop(self, intro=None):
    #     pass
    def output(self, message):
        if isinstance(message, str):
            message = message.encode('utf-8')
        self.stdout.write(message + '\n')

    # def do_start(self):
    #     self.proxy.start()
    def do_mul(self, *args):
        self.proxy.mul(*args)

    def do_list_ports(self):
        self.proxy.list_ports()


if __name__ == '__main__':
    print(delims)

