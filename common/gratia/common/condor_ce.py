
"""
Integrate Condor-CE with Gratia.

This module is a bit tricky because, if the batch system job finishes before
the routed job in Condor, we may not have a Condor-record to align with the
batch system job (and have to call condor_ce_q).
"""

import os
import re
import glob
import stat
import errno
import xml.dom.minidom

import gratia.common.config as config
import gratia.common.sandbox_mgmt as sandbox_mgmt
import gratia.common.file_utils as file_utils
import gratia.common.certinfo

from gratia.common.debug import DebugPrint, DebugPrintTraceback

Config = config.ConfigProxy()

hasProcessed = False

knownJobManagers = set(gratia.common.certinfo.jobManagers)

def gridJobIdToId(val):
    """
    Given a GridJobId from a Condor ClassAd, convert it to a batch system job
    ID.
    Implementation is based on PBS blahp, which uses something like:
        GridJobId = pbs pbs/20120603/1234.test.example.com
    and should return "1234".
    """
    return val.split("/")[-1].split(".")[0]


def add_unique_id(classad):
    if 'GlobalJobId' in classad:
        classad['UniqGlobalJobId'] = 'condor.%s' % classad['GlobalJobId']
        DebugPrint(6, "Unique ID: %s" % classad['UniqGlobalJobId'])
    return classad


classad_bool_re = re.compile("^(\w{1,255}) = (true|True|TRUE|false|False|FALSE)$")
classad_int_re = re.compile("^(\w{1,255}) = (-?\d{1,30})$")
classad_double_re = re.compile("(\w{1,255}) = (-?\d{1,30}\.?\d{1,30}?)")
classad_string_re = re.compile("^(\S+) = \"(.*)\"$")
classad_catchall_re = re.compile("^(\S+) = (.*)$")
def fdToClassad(fd):
    """
    Read Condor ClassAd's from a file descriptor, copying them into a python
    dictionary.
    Yields any classads on the stream.
    """
    classad = {}
    for line in fd.readlines():
        line = line.strip()
        m = classad_bool_re.match(line)
        if m:
            attr, val = m.groups()
            if val.lower().find("true") >= 0:
                classad[attr] = True
            else:
                classad[attr] = False
            continue
        m = classad_int_re.match(line)
        if m:
            attr, val = m.groups()
            classad[attr] = int(val)
            continue
        m = classad_double_re.match(line)
        if m:
            attr, val = m.groups()
            classad[attr] = float(val)
            continue
        m = classad_string_re.match(line)
        if m:
            attr, val = m.groups()
            classad[attr] = str(val)
            continue
        m = classad_catchall_re.match(line)
        if m:
            attr, val = m.groups()
            classad[attr] = str(val)
            continue
        if not line:
            yield add_unique_id(classad)
            classad = {}
            continue
        DebugPrint(2, "Invalid line in ClassAd: %s" % line)

    yield add_unique_id(classad)


# Example certinfo file:
#<xml version="1.0" encoding="UTF-8"?>
#<GratiaCertInfo>
#  <BatchManager>condor</BatchManager>
#  <UniqID>16217841211190762166.11840111202095132039</UniqID>
#  <LocalJobId>1067688</LocalJobId>
#  <DN>/C=IT/O=INFN/OU=Personal Certificate/L=Bari/CN=Simranjit Singh Chhibra</DN>
#  <VO>cms</VO>
#  <FQAN>/cms/Role=NULL/Capability=NULL</FQAN>
#</GratiaCertInfo>

def createCertinfoXML(classad):
    """
    From a dictionary object representing a Condor ClassAd, create the
    corresponding certinfo XML document.
    """
    # Sample: GridJobId = "batch pbs globus1.hyak.washington.edu_9619_globus1.hyak.washington.edu#660817.0#1455209943 pbs/20160211/3857720"
    #     Or: GridJobId = "condor fermicloud116.fnal.gov fermicloud116.fnal.gov:9619 128.0"
    job_info_str = classad.get("GridJobId", "")
    job_info = job_info_str.split()
    if len(job_info) == 4 and job_info[0] == "batch":
        bm = job_info[1]
        jobid = gridJobIdToId(job_info[3])
    elif len(job_info) == 4 and job_info[0] == "condor" \
                            and re.search(r'^\d+\.\d+$', job_info[3]):
        bm = job_info[0]
        jobid = gridJobIdToId(job_info[3])
    else:
        DebugPrint(3, "GridJobId was not parsed correctly: '%s'" % job_info_str)
        return None, None

    if bm not in knownJobManagers:
        bm = 'batch'

    dom = xml.dom.minidom.Document()
    batchManager = dom.createElement("BatchManager")
    batchManager.appendChild(dom.createTextNode(bm))
    localId = dom.createElement("LocalJobId")
    localId.appendChild(dom.createTextNode(jobid))

    # Sample: GlobalJobId = "brian-test.unl.edu#1612.0#1338568482"
    unique_id = classad.get("GlobalJobId", "")
    uniqID = dom.createElement("UniqID")
    uniqID.appendChild(dom.createTextNode(unique_id))

    # Sample: x509UserProxyVOName = "cms"
    voStr = classad.get("x509UserProxyVOName", "")
    vo = dom.createElement("VO")
    vo.appendChild(dom.createTextNode(voStr))

    # Sample: x509UserProxyFirstFQAN = "/cms/Role=NULL/Capability=NULL"
    fqanStr = classad.get("x509UserProxyFirstFQAN", "")
    fqan = dom.createElement("FQAN")
    fqan.appendChild(dom.createTextNode(fqanStr))

    # Sample: x509userproxysubject = "/C=TW/O=AP/OU=GRID/CN=Nitish Dhingra 142746"
    x509Str = classad.get("x509userproxysubject", "")
    x509 = dom.createElement("DN")
    x509.appendChild(dom.createTextNode(x509Str))

    info = dom.createElement("GratiaCertInfo")
    info.appendChild(dom.createTextNode("\n  "))
    info.appendChild(batchManager)
    info.appendChild(dom.createTextNode("\n  "))
    if unique_id:
        info.appendChild(uniqID)
        info.appendChild(dom.createTextNode("\n  "))
    if jobid:
        info.appendChild(localId)
        info.appendChild(dom.createTextNode("\n  "))
    if x509Str:
        info.appendChild(x509)
        info.appendChild(dom.createTextNode("\n  "))
    if voStr:
        info.appendChild(vo)
        info.appendChild(dom.createTextNode("\n  "))
    if fqanStr:
        info.appendChild(fqan)
        info.appendChild(dom.createTextNode("\n"))
    dom.appendChild(info)

    filename = "gratia_certinfo_%s_%s" % (bm, jobid)

    return filename, dom.toxml() + "\n"


def createCertinfoFile(classad, directory):
    """
    Create a certinfo file from a given classad dictionary.

    On IO errors, this will return false and log the issue.
    On success, or if the classad should be ignored, return true.
    """
    filename, xmldoc = createCertinfoXML(classad)
    # If we can't create an certinfo XML from it, it's not a routed job.
    if not filename:
        return True
    full_filename = os.path.join(directory, filename)

    full_filename = os.path.abspath(os.path.join(directory, full_filename))
    if not full_filename.startswith(directory):
        return False

    try:
        # Note the combination of flags: Gratia typically runs as root and
        # processes a world-writable sticky directory.  Hence, we need
        # O_EXCL.
        fd = os.open(full_filename, os.O_WRONLY | os.O_CREAT | os.O_TRUNC \
            | os.O_EXCL, stat.S_IRUSR | stat.S_IWUSR)
        os.write(fd, xmldoc)
        os.close(fd)
    except OSError, oe:
        # There are quite a few cases where we might try to write out a
        # certinfo file that exists (e.g., the condor_ce_q case).
        # Accordingly, we signal success in this case.
        if (oe.errno == errno.EEXIST) and \
                (os.stat(full_filename).st_uid == os.geteuid()):
            DebugPrint(4, "Unable write out certinfo file %s as it already " \
                "exists." % full_filename)
            return True
        DebugPrint(1, "Unable to write out certinfo file %s: %s " % \
            (full_filename, str(oe)))
        return False
    DebugPrint(3, "Successfully wrote certinfo file %s" % full_filename)
    return True


def classadToCertinfo(filename, output_dir):
    """
    Process the classad of the finished job into a certinfo file in the same
    directory.  On failure, do not throw an exception, but quarantine the
    classad file.
    On success, the classad history file is deleted.

    This function should not throw and does not return anything
    """
    DebugPrint(4, "Converting ClassAd %s to certinfo file." % filename)
    try:
        fd = open(filename)
    except IOError, ie:
        DebugPrint(1, "Unable to open ClassAd %s for certinfo conversion" \
            ": %s" % (filename, str(ie)))
        return

    for classad in fdToClassad(fd):

        if not createCertinfoFile(classad, output_dir):
            DebugPrint(0, "Failed to convert certinfo file %s; sending to " \
                "quarantine." % filename)
            sandbox_mgmt.QuarantineFile(filename, False)
            continue

        file_utils.RemoveFile(filename)


historyRe = re.compile("history\.[0-9]+\.[0-9]+")
def processHistoryDir():
    """
    Condor schedd will write one file per finished job into this directory.
    We must convert it from a Condor ClassAd to a certinfo file and rename it
    based on the routed job's name.
    """
    history_dir = Config.get_CondorCEHistoryFolder()
    output_dir = Config.get_DataFolder()
    if not history_dir:
        DebugPrint(3, "No Condor-CE history specified; will not process for" \
            " certinfo.")
    if not os.path.exists(history_dir):
        DebugPrint(3, "Condor-CE history directory %s does not exist." \
            % history_dir)
    for full_filename in glob.glob(os.path.join(history_dir, "history.*")):
        _, filename = os.path.split(full_filename)
        if not historyRe.match(filename):
            DebugPrint(3, "Ignoring history file %s as it does not match "
                "the regular expression" % filename)
            continue
        try:
            classadToCertinfo(full_filename, output_dir)
        except KeyboardInterrupt:
            raise
        except SystemExit:
            raise
        except Exception, e:
            DebugPrint(0, "Failure when trying to process Condor-CE history %s" \
                " into a certinfo file: %s" % (filename, str(e)))
            DebugPrintTraceback(e)


condor_q = """\
condor_ce_q -const 'RoutedJob =?= true && GridJobId =!= UNDEFINED \
        && GlobalJobId =!= UNDEFINED' \
    -format 'GlobalJobId=%s\t' GlobalJobId \
    -format 'x509UserProxyVOName=%s\t' x509UserProxyVOName \
    -format 'x509UserProxyFirstFQAN=%s\t' x509UserProxyFirstFQAN \
    -format 'x509userproxysubject=%s\t' x509userproxysubject \
    -format 'GridJobId=%s' GridJobId \
    -format '\n' junk \
"""
# Example output:
# GlobalJobId=brian-test.unl.edu#1655.0#1338817391	x509UserProxyVOName=cms	x509UserProxyFirstFQAN=/cms/Role=NULL/Capability=NULL	x509userproxysubject=/DC=org/DC=doegrids/OU=People/CN=Brian Bockelman 504307	GridJobId=pbs pbs/20120604/2635.brian-test.unl.edu

def queryAllJobs():
    """
    Quer the Condor-CE directly for the equivalent of the certinfo.
    Query is done for all jobs and kept in memory.
    """
    # If the history folder is not set, then we don't even bother
    # to query the Condor-CE.
    if not Config.get_CondorCEHistoryFolder():
        return {}

    job_info = {}
    devnull = open("/dev/null", "w")
    orig_stderr = os.dup(2)
    os.dup2(devnull.fileno(), 2)
    fd = os.popen(condor_q)
    os.dup2(orig_stderr, 2)
    for line in fd.readlines():
        line = line.strip()
        cur_job_info = {}
        # Anything before GridJobId should have trivial formatting, tab-delim
        info = line.split("GridJobId=")
        known_info = info[0].split("\t")
        for entry in known_info:
            pair = entry.split("=", 1)
            if not pair[0] or len(pair) != 2:
                continue
            cur_job_info[pair[0]] = pair[1]
        if len(info) == 2:
            cur_job_info["GridJobId"] = info[-1]
        if 'GlobalJobId' in cur_job_info:
            jobid = gridJobIdToId(cur_job_info['GridJobId'])
            job_info[jobid] = cur_job_info
    if fd.close():
        DebugPrint(3, "Condor-CE query failed; ignoring.")
        return {}
    else:
        return job_info


_queryCache = None
def queryJob(jobid):
    """
    Query the Condor-CE directly for the equivalent of the certinfo.

    This is only done in the case where we couldn't determine the info from
    the files on disk.  While we're at it, we pull the data for all jobs and
    subsequent lookups will perform admirably.
    """
    global _queryCache
    if _queryCache == None:
        directory = Config.get_DataFolder()
        job_info = queryAllJobs()
        for classad in job_info.values():
            # On failure, there is not much to do - ignore
            DebugPrint("Creating certinfo file for %s." % \
                classad['GlobalJobId'])
            createCertinfoFile(classad, directory)
        _queryCache = job_info
    info = _queryCache.get(jobid, {})
    certinfo = {}
    if 'x509UserProxyVOName' in info:
        certinfo["VO"] = info['x509UserProxyVOName']
    if 'x509userproxysubject' in info:
        certinfo['DN'] = info['x509userproxysubject']
    if 'x509UserProxyFirstFQAN' in info:
        certinfo['FQAN'] = info['x509UserProxyFirstFQAN']
    return certinfo

