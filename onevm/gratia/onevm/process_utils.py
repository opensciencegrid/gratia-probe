import popen2
try:
    import cStringIO
except ImportError:
    import io as cStringIO
import fcntl
import os
import time
import select

###############################################################################

class ExeError(RuntimeError):
    def __init__(self, msg):
        RuntimeError.__init__(self, msg)

###############################################################################

def iexe_cmd(cmd, stdin_data=None):
    """
    Fork a process and execute cmd - rewritten to use select to avoid filling
    up stderr and stdout queues.

    @type cmd: string
    @param cmd: Sting containing the entire command including all arguments
    @type stdin_data: string
    @param stdin_data: Data that will be fed to the command via stdin

    @return: Return code, stdout, stderr from running the command
    @rtype: tuple
    """

    output_lines = None
    error_lines = None
    exit_status = 0
    try:
        # XXX: no popen2 in python3
        child = popen2.Popen3(cmd, capturestderr=True)

        if stdin_data != None:
            child.tochild.write(stdin_data)

        child.tochild.close()

        stdout = child.fromchild
        stderr = child.childerr

        outfd = stdout.fileno()
        errfd = stderr.fileno()

        #outeof = erreof = 0
        outdata = cStringIO.StringIO()
        errdata = cStringIO.StringIO()

        fdlist = [outfd, errfd]
        for fd in fdlist: # make stdout/stderr nonblocking
            fl = fcntl.fcntl(fd, fcntl.F_GETFL)
            fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)

        while fdlist:
            time.sleep(.001) # prevent 100% CPU spin
            ready = select.select(fdlist, [], [])
            if outfd in ready[0]:
                outchunk = stdout.read()
                if outchunk == '':
                    fdlist.remove(outfd)
                else:
                    outdata.write(outchunk)

            if errfd in ready[0]:
                errchunk = stderr.read()
                if errchunk == '':
                    fdlist.remove(errfd)
                else:
                    errdata.write(errchunk)

        exit_status = child.wait()
        outdata.seek(0)
        errdata.seek(0)
        output_lines = outdata.readlines()
        error_lines = errdata.readlines()

    except Exception as ex:
        raise ExeError("Unexpected Error running '%s'\nStdout:%s\nStderr:%s\n"\
            "Exception OSError: %s" % (cmd, str(output_lines),
                                       str(error_lines), ex))

    return exit_status, output_lines, error_lines


def isList(var):
    if type(var) == type([]):
        return True
    return False

def representsInt(s):
    try:
        int(s)
        return True
    except ValueError:
        return False
