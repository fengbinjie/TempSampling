import cmd
import socketserver
class ctr(cmd.Cmd):
    def __init__(self):
        super().__init__()
        self.prompt = 'test>> '
        self.intro = 'test for cmd'

    def emptyline(self):
        return

    def do_exe(self,arg):
        if arg:
            print(type(arg))
            print(str(arg))

    def complete_exe(self, text, line, begidx, endidx):
        print(text,line,begidx,endidx)


    def do_EOF(self,arg):
        return True
if __name__ == '__main__':
    x = ctr()
    x.cmdloop()
