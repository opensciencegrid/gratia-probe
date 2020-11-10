
import os
import errno

from gratia.common.config import ConfigProxy

Config = ConfigProxy()

##
## Mkdir
##
## Author - Trent Mick (other recipes)
##
## A more friendly mkdir() than Python's standard os.mkdir().
## Limitations: it doesn't take the optional 'mode' argument
## yet.
##      
## http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/82465
def Mkdir(newdir):
    """works the way a good mkdir should :)
        - already exists, silently complete
        - regular file in the way, raise an exception
        - parent directory(ies) does not exist, make them as well
    """
        
    if os.path.isdir(newdir):
        pass
    elif os.path.isfile(newdir):
        raise OSError("a file with the same name as the desired dir, '%s', already exists." % newdir)
    else:   
        (head, tail) = os.path.split(newdir)
        if head and not os.path.isdir(head):
            Mkdir(head)

        # Mkdir can not use DebugPrint since it is used
        # while trying to create the log file!
        # print "Mkdir %s" % repr(newdir)

        if tail:
            os.mkdir(newdir)


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

