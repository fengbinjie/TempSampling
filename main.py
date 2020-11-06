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
    p = subprocess.run(f'tasklist /fi "PID eq {pid}" /fO TABLE /NH'.split(), capture_output=True)
    print(p.stdout)
    return True if out.split()[1] == str(pid) else False


def write_pidfile_or_die(pidfile):
    if os.path.exists(pidfile):
        with open(pidfile, 'r') as f:
            pid = f.read()
        if pid_is_running(int(pid)):
            print("Sorry, found a pidfile! Process {0} is still running.".format(pid))
            raise SystemExit
    with open(pidfile, 'w') as f:
        f.write(str(os.getpid()))
    return pidfile


if __name__ == '__main__':
    import time

    p = subprocess.run(f'tasklist'.split(), capture_output=True,universal_newlines=True)
    print(p.stdout)
    # write_pidfile_or_die('./tmp.pid')
    # time.sleep(10) # placeholder for the real work
    # print('process {0} finished work!'.format(os.getpid()))
    # os.remove('./tmp.pid')

# if __name__ == '__main__':
#     core.tasks.main()