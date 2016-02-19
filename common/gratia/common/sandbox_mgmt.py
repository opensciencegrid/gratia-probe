
import re
import os
import sys
import glob
import time
import string
import shutil
import tarfile

from gratia.common.config import ConfigProxy
from gratia.common.file_utils import Mkdir, RemoveFile
from gratia.common.utils import niceNum
from gratia.common.debug import DebugPrint, DebugPrintTraceback, LogFileName
import gratia.common.global_state as global_state

Config = ConfigProxy()

outstandingRecord = {}
hasMoreOutstandingRecord = False
backupDirList = []
outstandingStagedRecordCount = 0
outstandingStagedTarCount = 0
outstandingRecordCount = 0
__maxFilesToReprocess__ = 100000

def QuarantineFile(filename, isempty):

   # If we have trouble with a file, let's quarantine it
   # If the quarantine reason is 'only' that the file is empty,
   # list the file as such.

    dirname = os.path.dirname(filename)
    pardirname = os.path.dirname(dirname)
    if os.path.basename(dirname) != 'outbox':
        toppath = dirname
    else:
        if os.path.basename(pardirname) == 'staged':
            toppath = os.path.dirname(pardirname)
        else:
            toppath = pardirname
    quarantine = os.path.join(toppath, 'quarantine')
    Mkdir(quarantine)
    DebugPrint(0, 'Putting a quarantine file in: ' + quarantine)
    DebugPrint(3, 'Putting a file in quarantine: ' + os.path.basename(filename))
    if isempty:
        try:
            emptyfiles = open(os.path.join(quarantine, 'emptyfile'), 'a')
            emptyfiles.write(filename + '\n')
            emptyfiles.close()
        except:
            DebugPrint(
                0,
                'failed to record that file was empty: ',
                filename,
                '--',
                sys.exc_info(),
                '--',
                sys.exc_info()[0],
                '++',
                sys.exc_info()[1],
                )
    else:
        dest = os.path.join(quarantine, os.path.basename(filename))
        try:
            shutil.copy2(filename, dest)
        except IOError, ie:
            DebugPrint(1, "Unable to copy file %s to dest %s due to error: %s; ignoring" % (filename,dest,ie.strerror))
            return
    RemoveRecordFile(filename)


def RemoveRecordFile(filename):
    # Remove a record file and reduce the oustanding record count

    global outstandingRecordCount
    global outstandingStagedRecordCount

    if RemoveFile(filename):
        # Decrease the count only if the file was really removed

        dirname = os.path.dirname(filename)
        if os.path.basename(dirname) == 'outbox' and os.path.basename(os.path.dirname(dirname)) == 'staged':
            DebugPrint(3, 'Remove the staged record: ' + filename)
            outstandingStagedRecordCount += -1
        else:
            outstandingRecordCount += -1
            DebugPrint(3, 'Remove the record: ' + filename)


def RemoveOldFiles(nDays=31, globexp=None, req_maxsize=0):

    if not globexp:
        return

    # Get the list of all files in the log directory

    files = glob.glob(globexp)
    if not files:
        return

    DebugPrint(3, ' Will check the files: ', files)

    cutoff = time.time() - nDays * 24 * 3600

    totalsize = 0

    date_file_list = []
    for oldfile in files:
        if not os.path.isfile(oldfile):
            continue
        lastmod_date = os.path.getmtime(oldfile)
        if lastmod_date < cutoff:
            DebugPrint(2, 'Will remove: ' + oldfile)
            RemoveFile(oldfile)
        else:
            size = os.path.getsize(oldfile)
            totalsize += size
            date_file_tuple = (lastmod_date, size, oldfile)
            date_file_list.append(date_file_tuple)

    if len(date_file_list) == 0:

       # No more files.

        return

    dirname = os.path.dirname(date_file_list[0][2])
    statfs = os.statvfs(dirname)
    disksize = statfs.f_blocks
    freespace = statfs.f_bfree
    ourblocks = totalsize / statfs.f_frsize
    percent = ourblocks * 100.0 / disksize

    if percent < 1:
        DebugPrint(1, dirname + ' uses ' + niceNum(percent, 1e-3) + '% and there is ' + niceNum(freespace * 100
                   / disksize) + '% free')
    else:
        DebugPrint(1, dirname + ' uses ' + niceNum(percent, 0.10000000000000001) + '% and there is '
                   + niceNum(freespace * 100 / disksize) + '% free')

    minfree = 0.10000000000000001 * disksize  # We want the disk to be no fuller than 95%
    # We want the directory to not be artificially reduced below 5% because other things are filling up the disk.
    minuse = 0.05 * disksize  
    calc_maxsize = req_maxsize
    if freespace < minfree:

       # The disk is quite full

        if ourblocks > minuse:

          # We already use more than 5%, let's see how much we can delete to get under 95% full but not under 5% of
          # our own use

            target = minfree - freespace  # We would like to remove than much

            if ourblocks - target < minuse:

             # But it would take us under 5%, so do what we can

                calc_maxsize = minuse
            else:
                calc_maxsize = ourblocks - target

            if 0 < req_maxsize and req_maxsize < calc_maxsize * statfs.f_frsize:
                calc_maxsize = req_maxsize
            else:
                DebugPrint(4,
                           "DEBUG: The disk is quite full and this directory is 'large' attempting to reduce from "
                            + niceNum(totalsize / 1000000) + 'Mb to ' + niceNum(calc_maxsize / 1000000) + 'Mb.')
                calc_maxsize = calc_maxsize * statfs.f_frsize

    if calc_maxsize > 0 and totalsize > calc_maxsize:
        DebugPrint(1, 'Cleaning up directory due to space overflow: ' + niceNum(totalsize / 1e6,
                   0.10000000000000001), 'Mb for a limit of ', niceNum(calc_maxsize / 1e6,
                   0.10000000000000001), ' Mb.')
        calc_maxsize = 0.8 * calc_maxsize
        date_file_list.sort()

       # To get the newest first (for debugging purpose only)
       # date_file_list.reverse()

        currentLogFile = LogFileName()
        for file_tuple in date_file_list:
            DebugPrint(2, 'Will remove: ' + file_tuple[2])
            RemoveFile(file_tuple[2])
            totalsize = totalsize - file_tuple[1]
            if currentLogFile == file_tuple[2]:

             # We delete the current log file! Let's record this explicitly!

                DebugPrint(0, 'EMERGENCY DELETION AND TRUNCATION OF LOG FILES.')
                DebugPrint(0, 'Current log file was too large: ' + niceNum(file_tuple[1] / 1000000) + 'Mb.')
                DebugPrint(0, 'All prior information has been lost.')
            if totalsize < calc_maxsize:
                return


def RemoveOldLogs(nDays=31):
    logDir = Config.get_LogFolder()
    DebugPrint(1, 'Removing log files older than ', nDays, ' days from ', logDir)
    RemoveOldFiles(nDays, os.path.join(logDir, '*.log'))


def RemoveOldJobData(nDays=31):
    dataDir = Config.get_DataFolder()
    DebugPrint(1, 'Removing incomplete data files older than ', nDays, ' days from ', dataDir)
    RemoveOldFiles(nDays, os.path.join(dataDir, 'gratia_certinfo_*'))
    RemoveOldFiles(nDays, os.path.join(dataDir, 'gratia_condor_log*'))
    RemoveOldFiles(nDays, os.path.join(dataDir, 'gram_condor_log*'))


def RemoveOldQuarantine(nDays=31, maxSize=200):

    # Default to 31 days or 200Mb whichever is lower.
    quarantine=os.path.join(os.path.join(Config.get_DataFolder(),"quarantine"))
    if os.path.exists(quarantine):
        DebugPrint(1, 'Removing quarantines data files older than ', nDays, ' days from ', quarantine)
        RemoveOldFiles(nDays, os.path.join(quarantine, '*'), maxSize)
        #quarantine files are under subdirectory 
        subpath=os.listdir(quarantine)
        for dir_quar in subpath:
            if not os.path.isdir(os.path.join(quarantine,dir_quar)):
                continue
            DebugPrint(1, 'Removing quarantines data files older than ', nDays, ' days from ', os.path.join(quarantine,dir_quar))
            RemoveOldFiles(nDays, os.path.join(quarantine,dir_quar, '*'), maxSize)
    fragment = Config.getFilenameFragment()
    for current_dir in backupDirList:
        gratiapath = os.path.join(current_dir, 'gratiafiles')
        subpath = os.path.join(gratiapath, 'subdir.' + fragment)
        quarantine = os.path.join(subpath, 'quarantine')
        if os.path.exists(quarantine):
            DebugPrint(1, 'Removing quarantines data files older than ', nDays, ' days from ', quarantine)
            RemoveOldFiles(nDays, os.path.join(quarantine, '*'), maxSize)


def DirListAdd(value):
    '''Utility method to add directory to the list of directories'''

    if len(value) > 0 and value != 'None':
        backupDirList.append(value)


def InitDirList():
    '''Initialize the list of backup directories'''

    Mkdir(Config.get_WorkingFolder())

    DirListAdd(Config.get_WorkingFolder())
    DebugPrint(1, 'List of backup directories: ', backupDirList)


def AddOutstandingRecord(filename):
    '''Add the file to the outstanding list, unless it is'''

    if not (global_state.bundle_size > 1 and global_state.CurrentBundle.hasFile(filename)):
        outstandingRecord[filename] = 1


def ListOutstandingRecord(dirname, isstaged):
    """
    Put in OustandingRecord the name of the file in dir, if any
    Return true if reach the maximum number of files
    """

    global outstandingStagedRecordCount
    global outstandingRecordCount

    if not os.path.exists(dirname):
        return False

    files = os.listdir(dirname)
    nfiles = len(files)
    DebugPrint(4, 'DEBUG: ListOutstanding for ' + dirname + ' adding ' + str(nfiles))
    if isstaged:
        outstandingStagedRecordCount += nfiles
    else:
        outstandingRecordCount += nfiles
    for f in files:
        AddOutstandingRecord(os.path.join(dirname, f))
        if len(outstandingRecord) >= __maxFilesToReprocess__:
            return True
    return False


def SearchOutstandingRecord():
    '''Search the list of backup directories for'''

    global hasMoreOutstandingRecord
    global outstandingRecordCount
    global outstandingStagedTarCount
    global outstandingStagedRecordCount

    outstandingRecord.clear()
    outstandingRecordCount = 0
    outstandingStagedTarCount = 0
    outstandingStagedRecordCount = 0

    fragment = Config.getFilenameFragment()

    DebugPrint(4, 'DEBUG: Starting SearchOutstandingRecord')
    for current_dir in backupDirList:
        DebugPrint(4, 'DEBUG: SearchOutstandingRecord ' + current_dir)
        DebugPrint(4, 'DEBUG: Middle of SearchOutstandingRecord outbox:' + str(outstandingRecordCount)
                   + ' staged outbox:' + str(outstandingStagedRecordCount) + ' tarfiles:'
                   + str(outstandingStagedTarCount))

        gratiapath = os.path.join(current_dir, 'gratiafiles')
        subpath = os.path.join(gratiapath, 'subdir.' + fragment)
        outbox = os.path.join(subpath, 'outbox')
        staged = os.path.join(subpath, 'staged')
        stagedoutbox = os.path.join(subpath, 'staged', 'outbox')

        # For backward compatibility still look for the records in the top level
        # gratiafiles directories.

        path = os.path.join(gratiapath, 'r*.' + Config.get_GratiaExtension())
        files = glob.glob(path) + glob.glob(path + '__*')
        DebugPrint(4, 'DEBUG: Search add ' + str(len(files)) + ' for ' + path)
        outstandingRecordCount += len(files)
        for f in files:

            # Legacy reprocess files or ones with the correct fragment

            if re.search(r'/?r(?:[0-9]+)?\.?[0-9]+(?:\.' + fragment + r')?\.' + Config.get_GratiaExtension()
                         + r'(?:__.{10})?$', f):
                AddOutstandingRecord(f)
                if len(outstandingRecord) >= __maxFilesToReprocess__:
                    break

        # Record the number of tar file already on disk.

        stagedfiles = glob.glob(os.path.join(staged, 'store', 'tz.*'))
        outstandingStagedTarCount += len(stagedfiles)

        if len(outstandingRecord) >= __maxFilesToReprocess__:
            break

        # Now look for the record in the probe specific subdirectory.

        if ListOutstandingRecord(outbox, False):
            break
        prevOutstandingStagedRecordCount = outstandingStagedRecordCount
        if ListOutstandingRecord(stagedoutbox, True):
            break

        # If total number of outstanding files is less than the number of files already in the bundle,
        # Let's decompress one of the tar file (if any)

        needmorefiles = outstandingStagedRecordCount == 0 or \
            outstandingRecordCount + outstandingStagedRecordCount <= global_state.CurrentBundle.nFiles
        if needmorefiles and len(stagedfiles) > 0:

            # the staged/outbox is low on files and we have some staged tar files

            in_stagedoutbox = outstandingStagedRecordCount - prevOutstandingStagedRecordCount
            if in_stagedoutbox != 0 and global_state.CurrentBundle.nFiles > 0:
                # This staged outbox is not empty, so let's first empty it.
                # NOTE: import statement is here to break circular dependency between bundle and sandbox_mgmt
                responseString, _ = __import__("gratia.common.bundle").common.bundle.ProcessBundle(global_state.CurrentBundle)
                DebugPrint(0, responseString)
                DebugPrint(0, '***********************************************************')
                if global_state.CurrentBundle.nItems > 0:
                    # The upload did not work, there is no need to proceed with the record collection
                    break

            # The staged outbox is empty, we can safely untar the file without risking over-writing
            # a files.
            stagedfile = stagedfiles[0]
            if UncompressOutbox(stagedfile, stagedoutbox):
                RemoveFile(stagedfile)
            else:
                Mkdir(os.path.join(staged, 'quarantine'))
                os.rename(stagedfile, os.path.join(staged, 'quarantine', os.path.basename(stagedfile)))

            outstandingStagedTarCount += -1
            outstandingStagedRecordCount = prevOutstandingStagedRecordCount
            if ListOutstandingRecord(stagedoutbox, True):
                break

    # Mark that we probably have more outstanding record to look at.

    hasMoreOutstandingRecord = outstandingStagedTarCount > 0 or len(outstandingRecord) >= __maxFilesToReprocess__

    DebugPrint(4, 'DEBUG: List of Outstanding records: ', outstandingRecord.keys())
    DebugPrint(4, 'DEBUG: After SearchOutstandingRecord outbox:' + str(outstandingRecordCount)
               + ' staged outbox:' + str(outstandingStagedRecordCount) + ' tarfiles:'
               + str(outstandingStagedTarCount))


def GenerateFilename(prefix, current_dir):
    '''Generate a filename of the for current_dir/prefix.$pid.ConfigFragment.gratia.xml__Unique'''
    filename = prefix + str(global_state.RecordPid) + '.' + Config.get_GratiaExtension() \
        + '__XXXXXXXXXX'
    filename = os.path.join(current_dir, filename)
    mktemp_pipe = os.popen('mktemp -q "' + filename + '"')
    if mktemp_pipe != None:
        filename = mktemp_pipe.readline()
        mktemp_pipe.close()
        filename = string.strip(filename)
        if filename != r'':
            return filename

    raise IOError

def UncompressOutbox(staging_name, target_dir):

    # Compress the probe_dir/outbox and stored the resulting tar.gz file
    # in probe_dir/staged

    # staged_dir = os.path.join(probe_dir,"staged")
    # outbox = os.path.join(probe_dir,"outbox")

    DebugPrint(1, 'Uncompressing: ' + staging_name)
    try:
        tar = tarfile.open(staging_name, 'r')
    except KeyboardInterrupt:
        raise
    except SystemExit:
        raise
    except Exception, e:
        DebugPrint(0, 'Warning: Exception caught while opening tar file: ' + staging_name + ':')
        DebugPrint(0, 'Caught exception: ', e)
        DebugPrintTraceback()
        return False

    try:
        for tarinfo in tar:
            DebugPrint(1, 'Extracting: ' + tarinfo.name)
            tar.extract(tarinfo, target_dir)
    except KeyboardInterrupt:
        raise   
    except SystemExit:
        raise   
    except Exception, e:
        DebugPrint(0, 'Warning: Exception caught while extracting from tar file: ' + staging_name + ':')
        DebugPrint(0, 'Caught exception: ', e)
        DebugPrintTraceback()
        return False

    try:
        tar.close()
    except KeyboardInterrupt:
        raise   
    except SystemExit:
        raise   
    except Exception, e:
        DebugPrint(0, 'Warning: Exception caught while closing tar file: ' + staging_name + ':')
        DebugPrint(0, 'Caught exception: ', e)
        DebugPrintTraceback()
        return False

    return True


def CompressOutbox(probe_dir, outbox, outfiles):

    # Compress the probe_dir/outbox and stored the resulting tar.gz file
    # in probe_dir/staged

    global outstandingStagedTarCount

    staged_store = os.path.join(probe_dir, 'staged', 'store')
    Mkdir(staged_store)

    staging_name = GenerateFilename('tz.', staged_store)
    DebugPrint(1, 'Compressing outbox in tar.bz2 file: ' + staging_name)

    try:
        tar = tarfile.open(staging_name, 'w:bz2')
    except KeyboardInterrupt:
        raise   
    except SystemExit:
        raise   
    except Exception, e:
        DebugPrint(0, 'Warning: Exception caught while opening tar.bz2 file: ' + staging_name + ':')
        DebugPrint(0, 'Caught exception: ', e)
        DebugPrintTraceback()
        return False

    try:
        for f in outfiles:

            # Reduce the size of the file name in the archive

            arcfile = f.replace(Config.getFilenameFragment(), r'')
            arcfile = arcfile.replace('..', '.')
            tar.add(os.path.join(outbox, f), arcfile)
    except KeyboardInterrupt:
        raise   
    except SystemExit:
        raise   
    except Exception, e:
        DebugPrint(0, 'Warning: Exception caught while adding ' + f + ' from ' + outbox + ' to tar.bz2 file: '
                   + staging_name + ':')
        DebugPrint(0, 'Caught exception: ', e)
        DebugPrintTraceback()
        return False

    try:
        tar.close()
    except KeyboardInterrupt:
        raise   
    except SystemExit:
        raise   
    except Exception, e:
        DebugPrint(0, 'Warning: Exception caught while closing tar.bz2 file: ' + staging_name + ':')
        DebugPrint(0, 'Caught exception: ', e)
        DebugPrintTraceback()
        return False

    outstandingStagedTarCount += 1
    return True


def OpenNewRecordFile(dirIndex):

    global outstandingRecordCount
    # The file name will be r$pid.ConfigFragment.gratia.xml__UNIQUE

    DebugPrint(3, 'Open request: ', dirIndex)
    index = 0
    toomanyfiles = outstandingRecordCount >= Config.get_MaxPendingFiles()
    toomanystaged = outstandingStagedTarCount >= Config.get_MaxStagedArchives()

    if not toomanyfiles or not toomanystaged:
        for current_dir in backupDirList:
            index = index + 1
            if index <= dirIndex or not os.path.exists(current_dir):
                continue
            DebugPrint(3, 'Open request: looking at ', current_dir)
            current_dir = os.path.join(current_dir, 'gratiafiles')
            probe_dir = os.path.join(current_dir, 'subdir.' + Config.getFilenameFragment())
            working_dir = os.path.join(probe_dir, 'outbox')
            if toomanyfiles:
                if not os.path.exists(working_dir):
                    continue

                # Need to find and pack the full outbox

                outfiles = os.listdir(working_dir)
                if len(outfiles) == 0:
                    continue

                if CompressOutbox(probe_dir, working_dir, outfiles):

                    # then delete the content
                    for f in os.listdir(working_dir):
                        RemoveRecordFile(os.path.join(working_dir, f))
                        
                    # And reset the Bundle if needed.
                    if global_state.CurrentBundle.nItems > 0:
                        hasHandshake = global_state.CurrentBundle.nHandshakes > 0
                        global_state.CurrentBundle.clear()
                        if hasHandshake:
                            # Done to break circular dependency between send and sandbox_mgmt
                            __import__("gratia.common.send").common.send.Handshake()
                else:
                    continue

                # and retry

                toomanyfiles = outstandingRecordCount >= Config.get_MaxPendingFiles()
                if toomanyfiles:

                    # We did not suppress enough file, let's go on

                    continue

            if not os.path.exists(working_dir):
                try:
                    Mkdir(working_dir)
                except:
                    continue
            if not os.path.exists(working_dir):
                continue
            if not os.access(working_dir, os.W_OK):
                continue
            try:
                filename = GenerateFilename('r.', working_dir)
                DebugPrint(3, 'Creating file:', filename)
                outstandingRecordCount += 1
                f = open(filename, 'w')
                dirIndex = index
                return (f, dirIndex)
            except:
                continue
    else:
        DebugPrint(0, 'DEBUG: Too many pending files, the record has not been backed up')
    f = sys.stdout
    dirIndex = index
    return (f, dirIndex)

