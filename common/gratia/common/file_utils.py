
import os
import errno

from gratia.common.config import ConfigProxy

Config = ConfigProxy()


def RemoveFile(filename):

    # Remove the file, ignore error if the file is already gone.

    result = True
    try:
        os.remove(filename)
    except os.error as err:
        if err.errno == errno.ENOENT:
            result = False
        else:
            raise err
    return result


def RemoveDir(dirname):

   # Remove the file, ignore error if the file is already gone.

    try:
        os.rmdir(dirname)
    except os.error as err:
        if err.errno == errno.ENOENT:
            pass
        else:
            raise err

