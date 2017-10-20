# Implement file based locking on Windows.
# Simply exit with 1 if lock file exists (no retry).

from contextlib import contextmanager
import os
import sys
from win32api import GetLastError
from win32event import CreateMutex, ReleaseMutex
from winerror import ERROR_ALREADY_EXISTS

from remote import remotedir

lockname = os.path.join(remotedir, 'test.lock')
mutexname = '__test_lock__'


@contextmanager
def synchronized():
    try:
        mutex = CreateMutex(None, True, mutexname)
        if GetLastError() == ERROR_ALREADY_EXISTS:
            sys.stderr.write(
                "Could not acquire mutex. Is another test process running?")
            sys.exit(1)
        yield
    finally:
        if mutex is not None:
            ReleaseMutex(mutex)


def acquire():
    with synchronized():
        if os.path.exists(lockname):
            sys.stderr.write(
                "Lock file exists. Is another test process running?")
            sys.exit(1)
        open(lockname, 'w').close()


def release():
    with synchronized():
        os.unlink(lockname)


if __name__ == '__main__':
    commands = {'acquire': acquire, 'release': release}
    if len(sys.argv) != 2 or sys.argv[1] not in commands:
        sys.stderr.write('Usage: python %s acquire|release' % sys.argv[0])
        sys.exit(1)
    commands[sys.argv[1]]()
