import core.tasks
import os
import subprocess

def pid_is_running(pid):
    """
    Return pid if pid is still going.
    >>> import os
    >>> mypid = os.getpid()
    >>> mypid == pid_is_running(mypid)
    True
    >>> pid_is_running(1000000) is None
    True
    """
    p = subprocess.run(f'ps {pid}'.split(), capture_output=True, universal_newlines= True)
    out = p.stdout
    print(out)
    # 去掉ps命令返回的标题
    out =out.split()[4:]
    # 验证pid和程序名是否正确
    return True if out[0] == str(pid) and out[3] == 'main.py' else False


def write_pidfile_or_die(pidfile):
    if os.path.exists(pidfile):
        with open(pidfile, 'r') as f:
            pid = f.read()
        if pid_is_running(int(pid)):
            print("Sorry, found a pidfile! Process {0} is still running.".format(pid))
            raise SystemExit
    with open(pidfile, 'w') as f:
        f.write(f'{str(os.getpid())}\nmain.py')
    return pidfile


if __name__ == '__main__':
    if os.name == "posix":
        pass
    else:
        raise AssertionError("This code makes Unix-specific assumptions")
    assert os.name == "posix", "This code makes Unix-specific assumptions"
    # import time
    # write_pidfile_or_die('./tmp.pid')
    # time.sleep(10) # placeholder for the real work
    # print('process {0} finished work!'.format(os.getpid()))
    # os.remove('./tmp.pid')

# if __name__ == '__main__':
#     core.tasks.main()