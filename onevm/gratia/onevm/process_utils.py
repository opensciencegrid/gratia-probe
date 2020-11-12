from subproces import Popen, PIPE

###############################################################################

class ExeError(RuntimeError):
    def __init__(self, msg):
        RuntimeError.__init__(self, msg)

###############################################################################

def iexe_cmd(cmd, stdin_data=None):
    """
    Fork a process and execute cmd

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
        p = Popen(cmd, shell=True, stdin=PIPE, stdout=PIPE, stderr=PIPE)
        out, err = p.communicate(stdin_data)

        exit_status = p.returncode
        output_lines = out.splitlines()
        error_lines = err.splitlines()

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
