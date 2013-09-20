#!/usr/bin/perl -w

# Job monitor and Usage Records collector.
# Authors: R.M. Piro (piro@to.infn.it) with code
# A. Guarise (guarise@to.infn.it)
# G. Patania (patania@to.infn.it).
# copyright 2004-2006 EGEE project (see LICENSE file)

use strict;
use POSIX;

use Time::Local;
use File::Basename;
use urCollector::Common qw(:DEFAULT :Locking);
use urCollector::Configuration;

use List::Util qw(first); 

# turn off buffering of STDOUT
$| = 1;

my $TSTAMP_ACC = 86400; # timestamps between CE log and LRMS log can
# differ for up to a day.
my $DEF_LDIF_VALIDITY = 86400; # assume the GLUE attributes taken from the LDIF
# didn't change within the last day.

my $sigset = POSIX::SigSet ->new();
my $actionHUP = 
POSIX::SigAction->new("sigHUP_handler",$sigset,&POSIX::SA_NODEFER);
my $actionInt = 
POSIX::SigAction->new("sigINT_handler",$sigset,&POSIX::SA_NODEFER);
POSIX::sigaction(&POSIX::SIGHUP, $actionHUP);
POSIX::sigaction(&POSIX::SIGINT, $actionInt);
POSIX::sigaction(&POSIX::SIGTERM, $actionInt);
my $urCreatorExecutable = "/usr/share/gratia/pbs-lsf/urCreator";

my $onlyOneIteration = 0; # default is run as daemon!
my $useCElog = 1;   # default is use the CE's map: grid job <-> local job

my $useGGFformat = 0;  # default is no, for backward compatibility

# get command line arguments (if any):
my $clinearg = "";
while (@ARGV) {
   $clinearg = shift @ARGV;
   if ($clinearg eq "--nodaemon") {
      $onlyOneIteration = 1; # one iteration then quit! (for cronjobs)
   }
   else {
      # take it as configuration file name
      $configFilePath = $clinearg;
   }
}


# Parse configuration file
&parseConf($configFilePath);



my $lrmsType = $configValues{lrmsType};
my $pbsAcctLogDir = $configValues{pbsAcctLogDir};
my $lsfAcctLogDir = $configValues{lsfAcctLogDir};
my $ceJobMapLog = $configValues{ceJobMapLog};
my $useCEJobMap = $configValues{useCEJobMap};
my $writeGGFUR = $configValues{writeGGFUR};
my $keyList = $configValues{keyList};
my $ldifDefaultFiles = $configValues{ldifDefaultFiles};
my $glueLdifFile = $configValues{glueLdifFile};
my $siteName = $configValues{siteName};
my $URBox   = $configValues{URBox};
my $collectorLockFileName = $configValues{collectorLockFileName};
my $collectorBufferFileName = $configValues{collectorBufferFileName};
my $mainPollInterval = $configValues{mainPollInterval};
my $timeInterval = $configValues{timeInterval};
my $jobPerTimeInterval = $configValues{jobPerTimeInterval};
my $lsfBinDir = $configValues{lsfBinDir};



# check that UR box exists (where the pushd expects the URs), if not create it!
( -d $URBox ) || mkdir $URBox;
chmod 0750, $URBox;



# put lock
if ( &putLock($collectorLockFileName) != 0 ) {
   &error("Fatal Error: Couldn't open lock file! in $collectorLockFileName\n");
}
else {
   print "".localtime().": Daemon started. Lock file succesfully created.\n";
}


# check wether to use the CE log and get name of directory:
my $ceJobMapLogDir = "";

if ($useCEJobMap ne "yes" && $useCEJobMap ne "YES") {
   $useCElog = 0;  # don't use it, treat all jobs as local
   print "Warning: Not using the CE's job map log file for retrieving grid-related\ninformation. All jobs treated as local jobs!\n";
}
else {
   if ( -d $ceJobMapLog ) {
      # specified in conf file: directory, not a file
      $ceJobMapLogDir = $ceJobMapLog;
   }
   else {
      # if $ceJobMapLog is a file, not a directory, get the directory:
      $ceJobMapLogDir = dirname($ceJobMapLog)."/";
   }
   
   # check whether what was specified exists:
   if ( ! -d $ceJobMapLogDir ) {
      &error("Fatal error: directory with ceJobMapLog doesn't exist: '$ceJobMapLog'\n");
   }
}

if ($writeGGFUR eq "yes" || $writeGGFUR eq "YES") {
   $useGGFformat = 1;  # write GGF UR (xml) files
   print "Files in '$URBox' will be written in the GGF UR format (XML)!\n";
}



my $timeZone = `date +%z`;
chomp($timeZone);
my $domainName = `hostname -d`;
chomp($domainName);

# This is for parsing LDIF files:
my %glueAttributes = ();
my $ldifModTimestamp = 0;

# This is for storing CE log and LRMS log info (used for the GGF UR format)
my %urGridInfo = ();
my %urAcctlogInfo = ();


my $keepgoing = 1;
my $jobsThisStep = 0; # used to process only bunchs of jobs, as specified in
# the configuration file

# determine the LRMS type we have to treat:
my $lrmsLogDir = "";
if ($lrmsType eq "pbs") {
   $lrmsLogDir = $pbsAcctLogDir;
}
elsif ($lrmsType eq "lsf") {
   $lrmsLogDir = $lsfAcctLogDir;
}
elsif ($lrmsType eq "") {
   &error("Error: LRMS type not specified in configuration file!\n");
}
else {
   &error("Error: Unknown LRMS type specified in configuration file!\n");
}


# check LRMS log directory:
if (! -d $lrmsLogDir || ! -r $lrmsLogDir || ! -x $lrmsLogDir) {
   &error("Error: Directory for LRMS log ($lrmsLogDir) cannot be accessed!\n");
}


# append LRMS type to buffer file name:
$collectorBufferFileName = $collectorBufferFileName.".".$lrmsType;


# check whether we can use the 'less' command (should be present on each
# Linux system ...) this is usefull for gzipped log files!
my $have_less = 1;
my $less_cmd = `which less`;
chomp($less_cmd);
if ( ! -x $less_cmd ) {
   $have_less = 0;
}

# this is used for parsing log files backwards ...
my $have_tac = 1;
my $tac_cmd = `which tac`;
chomp($tac_cmd);
if ( ! -x $tac_cmd ) {
   $have_tac = 0;
}

# this is used for parsing log file forwards ...
my $have_cat = 1;
my $cat_cmd = `which cat`;
chomp($cat_cmd);
if ( ! -x $cat_cmd ) {
   $have_cat = 0;
}

if (!$have_tac || !$have_cat) {
   &error("Error: commands 'cat' and 'tac' required for parsing log files! Quitting!\n");
}

if (!$have_less) {
   print "Warning: command 'less' required for parsing compressed log files! Compressed log files will be skipped!\n";
}


# first get info on last job processed:
my $startJob = "";
my $startTimestamp = 0;
my $lastJob = "";
my $lastTimestamp = 0;
&readBuffer($collectorBufferFileName, $startJob, $startTimestamp);

while ($keepgoing) {
   
   if ($onlyOneIteration) {
      print "".localtime().": Not run as a daemon. Executing a single iteration!\n";
   }
   
   # see whether the GLUE attributes are available and have changed
   $ldifModTimestamp = &getGLUEAttributesFromLdif();
   
   # process LRMS log from last file to startJob
   &processLrmsLogs($startJob, $startTimestamp, $lastJob, $lastTimestamp);
   
   # write buffer (lastJob and lastTimestamp), if necessary!
   if ( $keepgoing && ($lastJob ne "") && ($lastJob ne $startJob) ) {
      print "".localtime().": Processed backwards from $lastJob (timestamp $lastTimestamp) to $startJob (timestamp $startTimestamp). Updating buffer $collectorBufferFileName.\n";
      
      &putBuffer($collectorBufferFileName, $lastJob, $lastTimestamp);
      
      $startJob = $lastJob;
      $startTimestamp = $lastTimestamp;
   }
   
   if ($onlyOneIteration) {
      # not run as a daemon, stop after first round!
      print "".localtime().": Not run as a daemon. Single iteration completed!\n";
      $keepgoing = 0;
   }
   
   if ($keepgoing) {
      # print "".localtime().": Waiting for new jobs to finish. Sleeping for $mainPollInterval seconds.\n";
      sleep $mainPollInterval;
   }
   
}

## at the end eventually update the buffer
#if ($lastJob ne "" ) {
#    &putBuffer($collectorBufferFileName, $lastJob,
#               $lastTimestamp);
#}




print "Exiting...\n";
if ( &delLock($collectorLockFileName) != 0 ) {        
   print "Error removing lock file.\n";
}
else {
   print "Lock file removed.\n";
}
print "".localtime().": Exit.\n";

exit(0);





#### ------------------------ END OF MAIN PART ------------------------ ####


#### ------------------------ Functions: ------------------------ ####


##--------> routines for job processing buffer <---------##
sub putBuffer {
   # arguments are: 0 = buffer name
   #                1 = last LRMS job id
   #                2 = last LRMS job timestamp (log time)
   my $buffName = $_[0];
   if ($keepgoing == 1) {
      # this is done only if no SIGINT was received!
      #print "".localtime().": Writing info on last processed job in buffer $buffName.\n";
      open(OUT, "> $buffName") || return 2;
      print OUT  "$_[1]:$_[2]";
      close(OUT);
   }
   return 0;
}

sub readBuffer {
   my $buffname = $_[0];
   open(IN, "< $buffname") || return 2;
   my $line;
   my $tstamp;
   while ( <IN> )
   {
      ($line,$tstamp) = split(':');
      $_[1] = $line;
      chomp($tstamp); # remove eventual newline
      $_[2] = $tstamp;
   }        
   close(IN);
   print "Reading buffer $buffname. First job to analyse: id=$line; log timestamp=$tstamp\n";
   return 0;
}

##-------> sig handlers subroutines <---------##
sub sigHUP_handler {
   print "".localtime().": Got SIGHUP!\n";
   $keepgoing = 1;
}

sub sigINT_handler {
   print "".localtime().": Got SIGINT!\n";
   $keepgoing = 0;
}


##--------> process the LRMS log and process the jobs <-------##

# process LRMS log from last file (set lastJob and lastTimestamp) to 
# startJob (get directory in temporal order and check modification date)

sub processLrmsLogs {
   my $startJob = $_[0];
   my $startTimestamp = $_[1];
   my $lastJob = $_[2];
   my $lastTimestamp = $_[3];
   
   my @lrmsLogFiles;
   
   my %logFMod = ();
   
   opendir(DIR, $lrmsLogDir) || &error("Error: can't open dir $lrmsLogDir: $!");
   while( defined(my $file = readdir(DIR)) ) {
      next if ( $file =~ /^\.\.?$/o ); # skip '.' and '..' 
      next if ( $lrmsType eq "pbs" && !($file =~ /^\d{8}(\.(gz|bz2))?$/o) );
      next if ( $lrmsType eq "lsf" && !($file =~ /^lsb\.acct(\.\d*)?(\.(gz|bz2))?$/o) );
      # we accept compressed files as well (but will be able to parse them
      # only if we have the command less, see later)
      
      push @lrmsLogFiles, $file;
      
      # keep track of last modification timestamp:
      
      #my ($dev,$ino,$mode,$nlink,$uid,$gid,$rdev,$size,
      #    $atime,$mtime,$ctime,$blksize,$blocks)
      #    = stat($file);
      $logFMod{$file} = (stat("$lrmsLogDir/$file"))[9]; #mtime in sec. after epoch
   }
   closedir DIR;
   
   # now we sort the LRMS log files according to their modification
   # timestamp
   my @sortedLrmsLogFiles
   = (sort{ $logFMod{$b} <=> $logFMod{$a} } keys %logFMod);
   
   # we process these LRMS log files from the last, until we find the
   # last job previously considered.
   
   my $continueProcessing = 1;
   my $newestFile = 1; # the first file we open is the current file
   
   while ($keepgoing && $continueProcessing && @sortedLrmsLogFiles) {
      my $thisLogFile = shift (@sortedLrmsLogFiles);
      
      if ( $logFMod{$thisLogFile} < $startTimestamp ) {
         # last modified (appended) _before_ the job we have already
         # processed hence we stop here!
         $continueProcessing = 0;
      }
      else {
         print "".localtime().": Processing LRMS log file: $thisLogFile; last modified: $logFMod{$thisLogFile}\n";
         
         &processLrmsLogFile($thisLogFile, $newestFile,
         $_[0], $_[1], $_[2], $_[3]);
         $newestFile = 0;
         # Call Gratia processing internally now to avoid leaving huge numbers of files unprocessed
         system("/usr/share/gratia/pbs-lsf/pbs-lsf_meter.pl 2>&1");
         # Note we can't update the state buffer becuse of the crazy way we
         # read backwards. That means if we get interrupted and have to
         # start again, Gratia will get a bunch of duplicates.
      }
   }
   
   
}


# --- parse a single log file --- #
sub processLrmsLogFile {
   
   my $filename = $_[0];
   my $skipFile = $_[1];
   
   my $startJob = $_[2];
   my $startTimestamp = $_[3];
   # my $lastJob = $_[4];
   # my $lastTimestamp = $_[5];
   
   # for each job to process: check the CE accounting log dir (ordered by
   # modification date) for the right log file +/- 1 (according to last
   # modification date) and process it from backwards.
   
   # if the job is found in the CE's accounting log: route 2
   # if not: route 3 (local job)
   
   # building command to open the log file
   my $cmd = $tac_cmd;
   # decide whether to decompress using 'less':
   if ($filename =~ /(\.(gz|bz2))?$/o) {
      # decompress and pipe into tac:
      $cmd = "$less_cmd -f $lrmsLogDir/$filename | ".$cmd;
   } else {
      # just use tac:
      $cmd = $cmd." $lrmsLogDir/$filename";
   }
   
   #print "".localtime().": Trying to open log file $filename\n";
   if ( !open ( LRMSLOGFILE, "$cmd |" ) ) {
      print "Warning: Couldn't open the log file ... skipping!\n";
      return 1;
   }
   
   my $firstJobId = 1;
   
   my $line = "";
   my $line_counter = 0;
   
   my ($log_year, $log_month, $log_day) = ($filename =~ m&^(?:.*/)?(\d{4})(\d{2})(\d{2})&);
   if ($log_year and $log_month and $log_day) {
      my @datime = (localtime);
      if (int($log_year) == ($datime[5] + 1900) and
         int($log_month) == ($datime[4] + 1)
         and int($log_day) == $datime[3]) {
            # Skip this even if it's not the most recently modified file.
            $skipFile = 1;
         } else {
            # Can avoid skipping last entry of most recent file if it's a PBS log not for today
            $skipFile = 0;
         }
   }
   
   while ($line = <LRMSLOGFILE>) {
      ++$line_counter;
      # Ignore the first record: pick it up next time
      $skipFile and $line_counter == 1 and next;
      
      if ($useGGFformat) {
         %urGridInfo = ();    # reset grid-related info
         %urAcctlogInfo = (); # reset usage info
      }
      
      if (!$keepgoing) {
         print "".localtime().": Stop processing $filename ...\n";
         close LRMSLOGFILE;
         return 1;
      }
      
      # not more than a bunch of jobs at a time!
      if ($jobsThisStep == $jobPerTimeInterval) {
         #print "".localtime().": $jobsThisStep jobs processed. Sleeping for $timeInterval seconds.\n";
         sleep $timeInterval;
         $jobsThisStep = 0;
      }
      # not here, but only when UR file created: $jobsThisStep++;
      
      # for debugging:
      #print "Scanning line: $line\n";
      
      # Populate job fields array
      my $lrmsRecordFields = populate_lrmsRecordFields($lrmsType, $line);
      
      # returns an LRMS job ID only if the line contains a finished
      # job
      my $targetJobId = &getLrmsTargetJobId($lrmsType, $lrmsRecordFields);
      
      next if ($targetJobId eq "");
      
      # get event time of LRMS log for the job (0 if not found)
      # this is for the buffer! the CE log timestamp will be matched to 
      # the LRMS creation time (=submission time)!
      my $lrmsEventTimeString = "";
      my $lrmsEventTimestamp = &getLrmsEventTime($lrmsType, $lrmsRecordFields, $lrmsEventTimeString);
      
      if($lrmsEventTimestamp == 0) {
         print "Error: could not determine LRMS event timestamp! Wrong file format ... ignoring this log file!\n";
         close LRMSLOGFILE;
         return 1;
      }
      
      # get creation time stamp for LRMS job (for matching CE log timestamp)
      my $job_ctime = &getLrmsJobCTime($lrmsType, $lrmsRecordFields);
      
      if ($job_ctime == 0) {
         print "Error: could not determine LRMS job creation/submission timestamp! Wrong file format ... ignoring this log file!\n";
         close LRMSLOGFILE;
         return 1;
      }
      
      
      if ( ($targetJobId eq $startJob) && ($startJob ne "") &&
         ($lrmsEventTimestamp eq $startTimestamp) && ($startTimestamp ne "")
         ) {
            
            # write this only if we have processed at least one job!
            # Otherwise it would be written on all empty iterations.
            if ( ($_[4] ne $startJob) || ($_[5] ne $startTimestamp)) {
               print "".localtime().": Found already processed $targetJobId with log event time $lrmsEventTimeString (=$lrmsEventTimestamp) in log! Done with iteration!\n";
            }
            
            close LRMSLOGFILE;
            return 0;
         } else {
            # need to process the job:
            if ( $firstJobId && $_[1] ) {
               
               $_[4] = $targetJobId; # $lastJob, i.e. newest job processed
               $_[5] = $lrmsEventTimestamp; # $lastTimestamp, i.e. of newest job
               $firstJobId = 0;
               
               print "".localtime().": This is the most recent job to process: $targetJobId; LRMS log event time: $lrmsEventTimeString (=$lrmsEventTimestamp)\n";
            }
            print "".localtime().": Processing job: $targetJobId with LRMS log event time(local): $lrmsEventTimeString (=$lrmsEventTimestamp); LRMS creation time: $job_ctime\n";
            
            my $gianduiottoHeader;
            if ($useCElog) {
               # get grid-related info from CE job map
               $gianduiottoHeader =  &parseCeUserMapLog($targetJobId,
               $lrmsEventTimestamp,
               $job_ctime);
            } else {
               # don't use CE job map ... local job!
               $gianduiottoHeader = "JOB_TYPE=local\n";
            }
            
            # keep track of the number of jobs processed:
            $jobsThisStep++;
            
            if (!$useGGFformat) {
               # for backward compatibility: actual parsing is done by pushd
               if (&writeGianduiottoFile($targetJobId, $lrmsEventTimestamp,
                  $gianduiottoHeader, $line)
                  != 0) {
                     print "".localtime().": Error: could not create UR file in $URBox for job $targetJobId with LRMS event time: $lrmsEventTimeString!\n";
                  }
            } else {
               # parse the LRMS log line and write a GGF UR file (XML):
               if (&writeGGFURFile($targetJobId, $lrmsEventTimestamp,
                  $gianduiottoHeader, $lrmsRecordFields)
                  != 0) {
                     print "".localtime().": Error: could not create GGF UR file (XML) in $URBox for job $targetJobId with LRMS event time: $lrmsEventTimeString!\n";
                  }
            }
            
            # &parseUR_PBS($_);
            # print "processing $hash{jobName}\n";
            # &callAtmClient();
         }
      
   }  # while (<LRMSLOGFILE>) ...
   
   close (LRMSLOGFILE);
}



## --------- parse CE user map log file for accounting --------##
## to find a specific job ...

sub parseCeUserMapLog {
   
   my $lrmsJobID = $_[0];
   my $lrmsTimestamp = $_[1];
   my $job_ctime = $_[2];
   
   # important note: the CE's log file might not have the precise timestamp
   # of the job's submission to the LRMS (due to implementation problems)
   # hence the CE log's entry is not necessarily in the (rotated?) log file
   # we expect from the LRMS timestamp
   
   my $gHeader = "";
   my $isLocal = 0; # assume it is a grid job with an entry in the CE log
   
   my @ceLogFiles;
   
   my %logFMod = ();
   
   opendir(DIR, $ceJobMapLogDir) || &error("Error: can't open dir $ceJobMapLogDir: $!");
   while( defined(my $file = readdir(DIR)) ) {
      my $fullname = $ceJobMapLogDir.$file;
      #print "CE_LOG_FILE:$fullname ...\n";
      
      next if ($file =~ /^\.\.?$/o); # skip '.' and '..' 
      next if ( !( $fullname =~ /^$ceJobMapLog[\/\-_]?\d{8}(\.(gz|bz2))?$/ ) &&
      !( $fullname =~ /^$ceJobMapLog[\/\-_]?\d{4}-\d{2}-\d{2}(\.(gz|bz2))?$/ ) &&
      !( $fullname =~ /^$ceJobMapLog(\.\d*)?(\.(gz|bz2))?$/)
      ); # skip if not like "<logname>(-)20060309(.gz)" (one per day)
      # skip if not like "<logname>(-)2006-03-09(.gz)" (one per day)
      # and not like "<logname>.1(.gz)" (rotated)!
      push @ceLogFiles, $file;
      
      #print "accepted!";
      
      # keep track of last modification timestamp:
      
      #my ($dev,$ino,$mode,$nlink,$uid,$gid,$rdev,$size,
      #    $atime,$mtime,$ctime,$blksize,$blocks)
      #    = stat($file);
      $logFMod{$file} = (stat("$ceJobMapLogDir/$file"))[9]; #mtime in sec. after epoch
   }
   closedir DIR;
   
   # now we sort the CE log files according to their modification
   # timestamp
   my @sortedCeLogFiles
   = (sort{ $logFMod{$b} <=> $logFMod{$a} } keys %logFMod);
   
   # find up to 3 file names: the log file that should contain the
   # LRMS timestamp; the previous file and the next file (in case the
   # CE log timestamp is not exactly synchronized the CE log entry might
   # end up in a previous or next file):
   
   
   my @ceScanLogFiles = ("", "", "");
   my %scanDirection;
   
   # $ceScanLogFiles[0] is the file expected for this timestamp
   # $ceScanLogFiles[1] is the previous file
   # $ceScanLogFiles[2] is the next file
   
   my $logFile = "";
   while (@sortedCeLogFiles) {
      $logFile = shift @sortedCeLogFiles;
      
      if ($logFMod{$logFile} < $job_ctime) {
         # this is the first file with an earlier timestamp, thus it is the
         # previous file
         $ceScanLogFiles[1] = $logFile;
         $scanDirection{$logFile} = "backward";
         last;
      } else {
         # as long as we didn't find the previous file, this might be
         # the expected one:
         $ceScanLogFiles[2] = $ceScanLogFiles[0]; # next file
         $scanDirection{$ceScanLogFiles[2]} = "forward";
         $ceScanLogFiles[0] = $logFile;           # expected file
         $scanDirection{$ceScanLogFiles[0]} = "backward";
      }
   }
   
   # shouldn't be done because due to the skew between the CE log timestamp
   # and the LRMS job_ctime there might be only the previous file in some
   # few cases:
   #
   #if ($ceScanLogFiles[0] eq "") {
   #        print "Warning: no CE user map log file found for the LRMS creation time $job_ctime of job $lrmsJobID!\n";
   #        return "";
   #}
   #else {
   
   my $scanFile = "";
   my $keepSearchingCeLogs = 1;
   foreach $scanFile (@ceScanLogFiles) {
      
      last if (!$keepSearchingCeLogs);
      
      next if ($scanFile eq "");
      
      print "".localtime().": Scanning CE log $scanFile (last modified=$logFMod{$scanFile}); direction: $scanDirection{$scanFile}\n";
      
      # decide whether to read forward or backward:
      my $cmd = $tac_cmd;  # default for backward!
      if ($scanDirection{$scanFile} eq "forward") {
         $cmd = $cat_cmd;
      }
      # decide whether to decompress using 'less':
      if ($scanFile =~ /(\.(gz|bz2))?$/o) {
         # decompress and pipe into cat/tac:
         $cmd = "$less_cmd $ceJobMapLogDir/$scanFile | ".$cmd;
      } else {
         # just use cat/tac:
         $cmd = $cmd." $ceJobMapLogDir/$scanFile";
      }
      
      if ( !open ( CELOGFILE, "$cmd |" ) ) {
         print "Warning: Couldn't open the log file ... skipping!\n";
         next;
      }
      
      while (my $line = <CELOGFILE>) {
         if ($line =~ /\s*\"lrmsID=$lrmsJobID\"\s*/) {
            # found something, check timestamp (+/- a day):
            # "timestamp=2006-03-08 12:45:01" or
            # "timestamp=2006/03/08 12:45:01"
            my $ceLogTstamp = 0;
            if ($line =~ /\s*\"timestamp=(\d{4})[-\/](\d{2})[-\/](\d{2})\s(\d{2}):(\d{2}):(\d{2})\"\s*/o) {
               
               # get timestamp for this UTC time!
               my $ceEntryTimestamp =
               timegm(int($6),int($5),int($4),    # ss:mm:hh
               int($3),int($2)-1,int($1)); # dd-mm-yy
               # month should be from 0 to 11 => -1 !
               
               print "".localtime().": Found in CE log: lrmsID=$lrmsJobID with timestamp(UTC)=$1-$2-$3 $4:$5:$6 ($ceEntryTimestamp)\n";
               
               if ( ($ceEntryTimestamp > $job_ctime-$TSTAMP_ACC)
                  && ($ceEntryTimestamp < $job_ctime+$TSTAMP_ACC)
                  ) {
                     # the timestamp from the CE log is within a day
                     # from the LRMS creation timestamp, accept it!
                     
                     print "Accepting timestamp from CE log!\nParsing entry: ";
                     
                     # example: "timestamp=2006-03-08 12:45:01" "userDN=/C=IT/O=INFN/OU=Personal Certificate/L=Padova/CN=Alessio Gianelle/Email=alessio.gianelle@pd.infn.it" "userFQAN=/atlas/Role=NULL/Capability=NULL" "userFQAN=/atlas/production/Role=NULL/Capability=NULL" "ceID=grid012.ct.infn.it:2119/jobmanager-lcglsf-infinite" "jobID=https://scientific.civ.zcu.cz:9000/-QcMu-Pfv4qHlp2dFvaj9w" "lrmsID=3639.grid012.ct.infn.it"
                     
                     # we already got the timestamp and the lrmsID
                     my $userDN = "";
                     my @userFQANs = ();
                     my $ceID = "";
                     my $jobID = "";
                     
                     my @fields = split(/\"/, $line);
                     my $fld;
                     my $foundsomething = 0;
                     foreach $fld (@fields) {
                        next if ($fld =~ /^\s*$/o); # spaces in between
                        if ($fld =~ /^userDN=(.*)$/o) {
                           $userDN = $1;
                           print "userDN=$userDN; ";
                           $foundsomething = 1;
                        } elsif ($fld =~ /^userFQAN=(.*)$/o) {
                           my $fqan = $1;
                           if (! $fqan =~ /^\s*$/o) {
                              push (@userFQANs, $fqan);
                           }
                           print "userFQAN=$fqan; ";
                           $foundsomething = 1;
                        } elsif ($fld =~ /^ceID=(.*)$/o) {
                           $ceID = $1;
                           print "ceID=$ceID; ";
                           $foundsomething = 1;
                        } elsif ($fld =~ /^jobID=(.*)$/o) {
                           $jobID = $1;
                           print "jobID=$jobID; ";
                           $foundsomething = 1;
                           if ($jobID eq "none" || $jobID eq "NONE") {
                              $jobID = "";
                           }
                        }
                     }
                     print "\n" if $foundsomething;
                     
                     # check that we have the minimum info:
                     if ($ceID eq "") {
                        print "Warning: ceID missing! Considering this as a local job!\n";
                        $isLocal = 1;
                     }
                     
                     # info on job
                     $gHeader = $gHeader."GRID_JOBID=$jobID\n"
                     ."LRMS_TYPE=$lrmsType\n"
                     ."LRMS_JOBID=$lrmsJobID\n"
                     ."LRMS_EVENTTIME=$lrmsTimestamp\n"
                     ."LRMS_SUBMTIME=$job_ctime\n";
                     if ($useGGFformat) {
                        $urGridInfo{GRID_JOBID} = $jobID;
                        $urGridInfo{LRMS_TYPE} = $lrmsType;
                        $urGridInfo{LRMS_JOBID} = $lrmsJobID;
                        $urGridInfo{LRMS_EVENTTIME} = $lrmsTimestamp;
                        $urGridInfo{LRMS_SUBMTIME} = $job_ctime;
                     }
                     
                     # info on user
                     $gHeader = $gHeader."USER_DN=$userDN\n"
                     ."USER_FQAN=";
                     my $fqans = "";
                     my $fq = "";
                     foreach $fq (@userFQANs) {
                        $fqans .= $fq.";";
                     }
                     if ($fqans ne "") {
                        chop($fqans); # cut last ";"
                     }
                     $gHeader = $gHeader.$fqans;
                     $gHeader = $gHeader."\n"; # terminate field USER_FQAN
                     if ($useGGFformat) {
                        $urGridInfo{USER_DN} = $userDN;
                        $urGridInfo{USER_FQAN} = $fqans;
                     }
                     
                     ###$gHeader = $gHeader."HLR_LOCATION=HLR_LOCATION\n";
                     
                     # info on CE:
                     $gHeader = $gHeader."CE_ID=$ceID\n"
                     ."timeZone=$timeZone\n";
                     if ($useGGFformat) {
                        $urGridInfo{CE_ID} = $ceID;
                        $urGridInfo{timeZone} = $timeZone;
                     }
                     
                     # eventually add info from LDIF file if this job
                     # is not too old and we can assume the current GLUE
                     # attributes to be correct:
                     if ($ldifModTimestamp != 0) { 
                        if ($job_ctime >= $ldifModTimestamp) {
                           print "Adding GLUE attributes to UR ...\n";
                           my $key;
                           foreach $key (keys(%glueAttributes)) {
                              $gHeader = $gHeader."$key=$glueAttributes{$key}\n";
                              if ($useGGFformat) {
                                 $urGridInfo{$key} = $glueAttributes{$key};
                              }
                           }
                        } else {
                           print "Job too old, GLUE attributes from LDIF file cannot be assumed to be correct ... not added to UR!\n";
                        }
                     }
                     
                     $keepSearchingCeLogs = 0;
                     last;
                  } elsif ($ceEntryTimestamp<$job_ctime-$TSTAMP_ACC) {
                     # the timestamp from the CE log is too low, stop
                     # trying to find the job!
                     print "Timestamp of CE log before LRMS creation time: no job found in CE log: local job!\n";
                     $isLocal = 1;
                     $keepSearchingCeLogs = 0;
                     last;
                  } else {
                     print "Timestamp of CE log after LRMS creation time: job with recycled LRMS ID ... ignoring!\n";
                  }
               
            } # if ($line =~ /\s*\"timestamp= ...
            
         } # if ($line =~ /\s*\"lrmsID= ...
         
      } # while ($line = <CELOGFILE>) ...
      
      close CELOGFILE;
      
   } # foreach ...
   
   if ($gHeader eq "") {
      print "No job found in CE log: local job!\n";
      $isLocal = 1;
   }
   
   if ($isLocal) {
      $gHeader = "JOB_TYPE=local\n".$gHeader;
   } else {
      # grid job
      $gHeader = "JOB_TYPE=grid\n".$gHeader;
   }
   
   return $gHeader;
}



## ------ write file in URBox for pushd ---------- ##
sub writeGianduiottoFile {
   
   my $filename = $lrmsType."_".$_[0]."_".$_[1]; 
   # unique filename: <lrmsType>_<lrmsJobID>_<lrmsEventTimestamp>
   my $header = $_[2];
   my $acctlog = $_[3];
   
   open(OUT, "> $URBox/$filename") || return 1;
   
   print OUT "$header";
   print OUT "ACCTLOG:$acctlog";
   
   close (OUT);
   
   return 0;
}


## ------ write GGF UR file (XML) in URBox ---------- ##
sub writeGGFURFile {
   
   my $lrmsJobID = $_[0];
   my $lrmsEventTimestamp = $_[1];
   my $header = $_[2];
   my $UR = $_[3];
   
   chomp($UR);
   
   # unique filename: <lrmsType>_<lrmsJobID>_<lrmsEventTimestamp>
   my $filename = $lrmsType."_".$lrmsJobID."_".$lrmsEventTimestamp; 
   
   # get grid-related info from previously composed header:
   my @headerLines = split(/\n/, $header);
   my $hLine;
   foreach $hLine (@headerLines) {
      if ($hLine =~ /^([^=]*)=(.*)$/o) {
         $urGridInfo{$1}=$2;
      }
   }
   
   # parse usage info from LRMS account log:
   if ($lrmsType eq "pbs") {
      &parseUR_pbs($UR);
   } elsif ($lrmsType eq "lsf") {
      &parseUR_lsf($UR);
   } else {
      print "ERROR: unknown LRMS type ($lrmsType) ... skipping!\n";
      return 2;
   }
   
   # determine grid job ID:
   my $gridJobId = "";
   if (exists($urGridInfo{GRID_JOBID})) {
      $gridJobId = $urGridInfo{GRID_JOBID};
   } elsif (exists($urAcctlogInfo{server}) && $urAcctlogInfo{server} ne ""
            && exists($urAcctlogInfo{lrmsId}) && $urAcctlogInfo{lrmsId} ne ""
            && exists($urAcctlogInfo{start}) && $urAcctlogInfo{start} ne "") 
   {
      $gridJobId = $urAcctlogInfo{server}.":".$urAcctlogInfo{lrmsId}."_".$urAcctlogInfo{start};
   }
   
   if ($gridJobId eq "") {
      print "ERROR: Cannot determine or construct a unique job ID ... skipping!\n";
      return 3;
   } else {
      print "Using grid job ID '$gridJobId' also as RecordIdentity!\n";
   }
   
   # determine VO:
   my $userVo = "";
   my $fqan = "";
   if (exists($urGridInfo{USER_FQAN}) && $urGridInfo{USER_FQAN} ne "") {
      $fqan = $urGridInfo{USER_FQAN};
   }
   if ( &determineUserVO($fqan, $urAcctlogInfo{user}, $userVo) == 0 ) {
      print "Determined user VO: $userVo\n";
   }
   

   # Fixes for invalid records (see GRATIA-119), zero out time fields if they 
   # have really large numbers, threshold time based on bad values used in 
   # condor probe
   if ($urAcctlogInfo{cput} > 2000000000 ) {
   	  print "WARNING: INVALID DATA: Record for $gridJobId has invalid cpu ".
   	        "time ".$urAcctlogInfo{cput}."replacing value with 0\n";
      $urAcctlogInfo{cput} = 0;  
   }
   
   if ($urAcctlogInfo{walltime} > 2000000000) {
      print "WARNING: INVALID DATA: Record for $gridJobId has invalid ".
            "walltime time ".$urAcctlogInfo{walltime}."replacing value with 0\n";
      $urAcctlogInfo{walltime} = 0;  
   }
   
   ### compose urCreator command line
   my $cmd = "$urCreatorExecutable -t \"".&timestamp2String("".time(),"Z")."\""
   ." -r \"$gridJobId\" -g \"$gridJobId\" ";
   
   if ($lrmsJobID ne "") {
      $cmd .= "-l \"$lrmsJobID\" ";
   }
   
   if (exists($urAcctlogInfo{user}) && $urAcctlogInfo{user} ne "") {
      $cmd .= "-u \"$urAcctlogInfo{user}\" ";
   }
   
   if (exists($urGridInfo{USER_DN}) && $urGridInfo{USER_DN} ne "") {
      $cmd .= "-k \"$urGridInfo{USER_DN}\" ";
   }
   
   if (exists($urAcctlogInfo{jobName}) && $urAcctlogInfo{jobName} ne "") {
      $cmd .= "-j \"$urAcctlogInfo{jobName}\" ";
   }
   
   if (exists($urAcctlogInfo{exitStatus}) && $urAcctlogInfo{exitStatus} =~ /^\d+$/o) {
      $cmd .= "-x \"$urAcctlogInfo{exitStatus}\" -X \"exit status\" ";
   }
   
   if (exists($urAcctlogInfo{walltime}) && $urAcctlogInfo{walltime} ne "") {
      $cmd .= "-w \"".&timeSecs2Period("".$urAcctlogInfo{walltime})."\" ";
   }
   
   if (exists($urAcctlogInfo{cput}) && $urAcctlogInfo{cput} ne "") {
      $cmd .= "-c \"".&timeSecs2Period("".$urAcctlogInfo{cput})."\" ";
   }
   
   if (exists($urAcctlogInfo{end}) && $urAcctlogInfo{end} ne "") {
      $cmd .= "-e \"".&timestamp2String("".$urAcctlogInfo{end},"Z")."\" ";
   }
   
   if (exists($urAcctlogInfo{start}) && $urAcctlogInfo{start} ne "") {
      $cmd .= "-s \"".&timestamp2String("".$urAcctlogInfo{start},"Z")."\" ";
   }
   
   if ($siteName ne "") {
      $cmd .= "-m \"$siteName\" -M \"SiteName\" ";
   } elsif (exists($urAcctlogInfo{server}) && $urAcctlogInfo{server} ne "") {
      $cmd .= "-m \"$urAcctlogInfo{server}\" -M \"Server\" ";
   }
   
   if (exists($urAcctlogInfo{execHost}) && $urAcctlogInfo{execHost} ne "") {
      $cmd .= "-y \"$urAcctlogInfo{execHost}\" -Y \"executing host\" ";
   }
   
   if (exists($urAcctlogInfo{queue}) && $urAcctlogInfo{queue} ne "") {
      $cmd .= "-q \"$urAcctlogInfo{queue}\" ";
   }
   
   if ($lrmsType ne "") {
      $cmd .= "-Q \"LRMS type: $lrmsType\" ";
   }
   
   if (exists($urAcctlogInfo{group}) && $urAcctlogInfo{group} ne "") {
      $cmd .= "\"LocalUserGroup=$urAcctlogInfo{group}\" ";
   }
   
   #supress generation of UserVOName attribute that causes to 
   # gratia collector to store the value of this attribute as a VOName	
   #if ($userVo ne "") {
   #   $cmd .= "\"UserVOName=$userVo\" ";
   #} elsif (exists $urAcctlogInfo{account} and $urAcctlogInfo{account} ne "") {
   #   $cmd .= "\"UserVOName=$urAcctlogInfo{account}\" ";
   #}
   
   if ($fqan ne "") {
      $cmd .= "\"UserFQAN=$fqan\" ";
   }
   
   if (exists($urGridInfo{CE_ID}) && $urGridInfo{CE_ID} ne "") {
      my $resGridId = $urGridInfo{CE_ID};
      # does the CE ID finish with the queue name???
      if ($resGridId !~ /[-:]$urAcctlogInfo{queue}\W*$/) {
         $resGridId = $resGridId."-".$urAcctlogInfo{queue};
      }
      $cmd .= "\"ResourceIdentity=$resGridId\" ";
   }
   
   if (exists($urAcctlogInfo{mem}) && $urAcctlogInfo{mem} =~ /^(\d+)([^\d]*)$/o) {
      my $unit = "KB";
      if ($2 ne "") {
         $unit = uc($2);
      }
      $cmd .= "\"Memory=$1,,$unit,,total,\" ";
   }
   
   if (exists($urAcctlogInfo{vmem}) && $urAcctlogInfo{vmem} =~ /^(\d+)([^\d]*)$/o) {
      my $unit = "KB";
      if ($2 ne "") {
         $unit = uc($2);
      }
      $cmd .= "\"Swap=$1,,$unit,,total,\" ";
   }
   
   if (exists($urAcctlogInfo{processors}) && $urAcctlogInfo{processors} ne "") {
      my $descr = "";
      if (exists($glueAttributes{GlueHostBenchmarkSI00})
      && $glueAttributes{GlueHostBenchmarkSI00} ne "") {
         $descr .= "GlueHostBenchmarkSI00=$glueAttributes{GlueHostBenchmarkSI00}";
      }
      if (exists($glueAttributes{GlueHostBenchmarkSF00})
      && $glueAttributes{GlueHostBenchmarkSF00} ne "") {
         if ($descr ne "") {
            $descr .= ";";
         }
         $descr .= "GlueHostBenchmarkSF00=$glueAttributes{GlueHostBenchmarkSF00}";
      }
      $cmd .= "\"Processors=$urAcctlogInfo{processors},$descr,total,\" ";
   }
   
   if ($lrmsEventTimestamp ne "") {
      $cmd .= "\"TimeInstant=".&timestamp2String("".$lrmsEventTimestamp,$timeZone).",LRMS event timestamp,\" ";
   }
   
   print "Executing: $cmd\n";
   
   if (system ("$cmd > $URBox/$filename") != 0) {
      return 1;
   }
   
   return 0;
}


## ------ get GLUE attributes From LDIF file --------- ##
sub getGLUEAttributesFromLdif {
   my $modTStamp = 0; # returns 0 if no valid attributes found!
   # otherwise returns the timestamp of the last
   # modification of the file!
   
   # to be stored in %glueAttributes
   %glueAttributes = (); # first empty everything
   
   my @ldifFiles = split(/,/, $ldifDefaultFiles);
   unshift(@ldifFiles, $glueLdifFile); # first to try!
   
   my @keys = split(/,/, $keyList);
   
   if (!@keys) {
      print "".localtime().": Warning: No GLUE attributes will be added to usage records (reason: no keyList in configuration file)!\n";
      return 0; # no keys -> no benchmarks
   }
   
   while (@ldifFiles) {
      my $file = shift(@ldifFiles);
      print "".localtime().": Trying to get GLUE benchmarks from LDIF file: $file\n";
      
      if (!open(GLUEFILE, "< $file")) {
         print "Warning: could not open the LDIF file ... skipping!\n";
         next;
      }
      
      my $foundSomething = 0;
      my $line;
      while ($line = <GLUEFILE>) {
         my $key;
         foreach $key (@keys) {
            if ( ($line =~ /^$key:\s?(.*)$/o )
               || ($line =~ /^$key=(.*)$/o ) ) {
                  # accept stuff like "GlueHostBenchmarkSI00: 955" and
                  # "GlueHostApplicationSoftwareRunTimeEnvironment: SI00MeanPerCPU=955"
                  $glueAttributes{$key} = $1;
                  print "found: $key=$1; ";
                  $foundSomething = 1;
               }
         }
      }
      
      close(GLUEFILE);
      
      if ($foundSomething) {
         print "\n";
         # get timestamp of file:
         $modTStamp = (stat($file))[9]; #mtime in sec. after epoch
         
         last; # don't check the other files (if any)!
      }
      
   }
   
   my $thisTStamp = time();
   
   if ($modTStamp == 0) {
      print "".localtime().": Warning: No GLUE attributes will be added to usage records (reason: no valid entries in LDIF file(s))!\n";
      return 0;
   }
   else {
      if($modTStamp > $thisTStamp-$DEF_LDIF_VALIDITY) {
         # accept it for at least a day, even if more recently modified
         $modTStamp = $thisTStamp-$DEF_LDIF_VALIDITY;
      }
      print "GLUE attributes will be accepted for all jobs with LRMS creation time after $modTStamp\n";
   }
   
   
   
   return $modTStamp;
}


## ------ determine the LRMS type from the log file ------ ##
#sub determinLrmsType() {
#    my $lrmsLine = $_[0];
#
#    my $lType = "";  # unknown;
#
#    if ($lrmsLine =~ /^\d{2}\/\d{2}\/\d{4}\s\d{2}:\d{2}:\d{2};.;\d+\./) {
#        # 03/10/2006 00:03:36;S;5738.[t2-ce-01.to.infn.it;user=atlas001 ...]
#        $lType = "pbs";
#    }
#    elsif ($lrmsLine =~ /^\"JOB_FINISH\"\s\"[0-9\.]+\"\s\d+\s/) {
#        # "JOB_FINISH" "6.0" 1140193736 [55455 774 40370307 ...]
#        $lType = "lsf";
#    }
#
#    return $lType;
#}



## ------ these are the LRMS type-specific functions ------ ##


# returns "" if the line should be ignored!
sub getLrmsTargetJobId {
   if ($_[0] eq "pbs") {
      return &getLrmsTargetJobId_pbs($_[1]);
   } elsif ($_[0] eq "lsf") {
      return &getLrmsTargetJobId_lsf($_[1]);
   }
   return "";
}

sub getLrmsTargetJobId_pbs {
   my $jid = ""; # default: line to ignore!
   my $lrmsRecordFields = shift;
   
   if (scalar(@$lrmsRecordFields) > 1) {
      my @ARRAY2 = split(";" , $$lrmsRecordFields[1] );
      if (scalar(@ARRAY2) > 2 && $ARRAY2[1] eq "E" ) {
         $jid = $ARRAY2[2]; # finished job, return LRMS ID!
      }
   }
   return $jid; # line to ignore?
}

sub getLrmsTargetJobId_lsf {
   my $jid = ""; # default: line to ignore!
   my $lrmsRecordFields = shift;
   
   if ( (scalar(@$lrmsRecordFields) > 3) && ($$lrmsRecordFields[0] eq "JOB_FINISH") ) {
      $jid = $$lrmsRecordFields[3];           # finished job, return LRMS ID!
   }
   return $jid; # line to ignore?
}


# get event time for LRMS log entry: returns 0 if not found
sub getLrmsEventTime {
   if ($_[0] eq "pbs") {
      return &getLrmsEventTime_pbs($_[1], $_[2]);
   } elsif ($_[0] eq "lsf") {
      return &getLrmsEventTime_lsf($_[1], $_[2]);
   }
   return 0;
}

sub getLrmsEventTime_pbs {
   # Format in PBS log: 03/10/2006 00:03:33;E; ...
   
   my $eventTimestamp = 0;
   my $lrmsRecordFields = shift;
   
   return $eventTimestamp unless scalar(@$lrmsRecordFields) > 1;
   
   my @ARRAY = split(";" , join(" ", $$lrmsRecordFields[0], $$lrmsRecordFields[1]));
   if (scalar(@ARRAY) > 0) {
      my $sec = 0; my $min = 0; my $hour = 0;
      my $mday = 0; my $mon = 0; my $year = 0;
      
      if ($ARRAY[0] =~
         /^(\d{2})\/(\d{2})\/(\d{4})\s(\d{2}):(\d{2}):(\d{2})$/o) {
            
            $mon = int($1)-1; # has to be 0 to 11 -> -1 !
            $mday = int($2);
            $year = int($3);
            $hour = int($4);
            $min = int($5);
            $sec = int($6);
            
            $eventTimestamp = timelocal($sec,$min,$hour,    # ss:mm:hh
            $mday,$mon,$year);  # dd-mm-yy
            $_[1] = $ARRAY[0];
         }
   }
   
   return $eventTimestamp;
}

sub getLrmsEventTime_lsf {
   # Format in LSF log: "JOB_FINISH" "6.0" 1140194675 ...
   
   my $eventTimestamp = 0;
   my $lrmsRecordFields = shift;
   
   if ( (scalar(@$lrmsRecordFields) > 2) && ($$lrmsRecordFields[2] =~ /^(\d*)$/o) ) {
      $eventTimestamp = int($1);
      
      $_[1] = $$lrmsRecordFields[2];
   }
   
   return $eventTimestamp;
}


# get the LRMS creation time for the job: returns 0 if not found:
sub getLrmsJobCTime {
   if ($_[0] eq "pbs") {
      return &getLrmsJobCTime_pbs($_[1]);
   } elsif ($_[0] eq "lsf") {
      return &getLrmsJobCTime_lsf($_[1]);
   }
   return 0;
}

sub getLrmsJobCTime_pbs {
   my $ctime = 0;
   my $lrmsRecordFields = shift;
   
   # Not sure if it's in the same field for all PBS-style LRMS systems,
   # so map all (there should only be one)
   my @ctime_matches = map { m&^ctime=(\d*)$&o?$1:() } @$lrmsRecordFields;
   if (scalar @ctime_matches > 0) {
      $ctime = int($ctime_matches[0]);
   }
   
   return $ctime;
}

sub getLrmsJobCTime_lsf {
   my $ctime = 0;
   my $lrmsRecordFields = shift;
   
   # in lsb.acct the creation time is the submitTime, the 8th field
   
   if ( (scalar(@$lrmsRecordFields) > 7) && ($$lrmsRecordFields[7] =~ /^(\d*)$/o) ) {
      $ctime = int($1);
   }
   
   return $ctime;
}

sub parseUR_pbs {
   my $lrmsRecordFields = shift;
   
   my @tmpArray = split ( ';', $$lrmsRecordFields[1] );
   $_ = $tmpArray[3];
   if (/^user=(.*)$/o) {
      $urAcctlogInfo{user}=$1;
   }
   $urAcctlogInfo{lrmsId}=$tmpArray[2];
   $_ = $tmpArray[2];
   if (/^([\d|\-|\[|\]|\<|\>]*)\.(.*)$/o) {
      $urAcctlogInfo{server}=$2;
   }
   foreach my $record_field ( @$lrmsRecordFields ) {
      if ( $record_field =~ /^queue=(.*)$/o) {
         $urAcctlogInfo{queue}=$1;
         next;
      }
      if ( $record_field =~ /^resources_used\.cput=.*?(\d+):(\d+):(\d+)$/o) {
         $urAcctlogInfo{cput}= $3 + $2*60 + $1*3600;
         next;
      }
      if ( $record_field =~ /^resources_used\.walltime=*?(\d+):(\d+):(\d+)$/o) {
         $urAcctlogInfo{walltime}= $3 + $2*60 + $1*3600;
         next;
      }
      if ( $record_field =~ /^resources_used\.vmem=.*?(\d*[M.k]b)$/o) {
         $urAcctlogInfo{vmem}     = $1;
         next;
      }
      if ( $record_field =~ /^resources_used\.mem=.*?(\d*[M.k]b)$/o) {
         $urAcctlogInfo{mem}     = $1;
         next;
      }
      if ( $record_field =~ /^Resource_List\.mppwidth=(\d+)$/o) {
         $urAcctlogInfo{mppwidth} = $1;
         next;
      } elsif ( $record_field =~ /^Resource_List\.neednodes=(\d+)$/o) {        
         $urAcctlogInfo{neednodes} = $1;
         # attention! might also be list of hostnames,
         # in this case the number of hosts should be
         # counted!? What about SMP machines; is their
         # hostname listed N times or only once??
         next;
      } elsif ( $record_field =~ /^Resource_List\.nodect=(\d+)/o ) {
         $urAcctlogInfo{nodect} = $1;
         next;
      } elsif ( $record_field =~ /^Resource_List\.select=(\d+)(?::ncpus=(\d+))/o ) {
         $urAcctlogInfo{select} = $1 * ( ${2} || 1 );
         next;
      } elsif ( $record_field =~ /^Resource_List\.select=(\d+)/o ) {
         $urAcctlogInfo{select} = $1;
         next;
      } elsif ( $record_field =~ /^Resource_List\.nodes=(\d+)(?::(\d+))/o ) {
         $urAcctlogInfo{nodes} = ${1} * ( ${2} || 1 );
         next;
      } elsif ( $record_field =~ /^Resource_List\.nodes=(\d+):ppn=(\d+)/o ) {
         $urAcctlogInfo{nodes} = ${1} * ( ${2} || 1 );
         next;
      } elsif ( $record_field =~ /^Resource_List\.ncpus=(\d+)/o ) {
         $urAcctlogInfo{cores} = ${1};
         next;
      }
      if ( $record_field =~ /^group=(.*)$/o) {        
         $urAcctlogInfo{group} = $1;
         next;
      }
      if ( $record_field =~ /^account=(.*)$/o) {
         $urAcctlogInfo{account} = $1;
         next;
      }     
      if ( $record_field =~ /^jobname=(.*)$/o) {        
         $urAcctlogInfo{jobName} = $1;
         next;
      }
      if ( $record_field =~ /^ctime=(\d*)$/o) {        
         $urAcctlogInfo{ctime} = $1;
         next;
      }
      if ( $record_field =~ /^qtime=(\d*)$/o) {        
         $urAcctlogInfo{qtime} = $1;
         next;
      }
      if ( $record_field =~ /^etime=(\d*)$/o) {        
         $urAcctlogInfo{etime} = $1;
         next;
      }
      if ( $record_field =~ /^start=(\d*)$/o) {        
         $urAcctlogInfo{start} = $1;
         next;
      }
      if ( $record_field =~ /^end=(\d*)$/o) {        
         $urAcctlogInfo{end} = $1;
         next;
      }
      if ( $record_field =~ /^exec_host=(.*)$/o) {        
         $urAcctlogInfo{execHost} = $1;
         next;
      }
      if ( $record_field =~ /^Exit_status=(\d*)$/) {        
         $urAcctlogInfo{exitStatus} = $1;
         next;
      }
   }
   $urAcctlogInfo{processors} = 
    $urAcctlogInfo{cores} ||       # Number of cores used.
    $urAcctlogInfo{select} ||      # Number of cores selected
    $urAcctlogInfo{nodes} ||       # Alternative way? of counting core used
    $urAcctlogInfo{nodect} ||      # Number of nodes used
    $urAcctlogInfo{neednodes} ||   # 
    $urAcctlogInfo{mppwidth} || 1;
}

sub parseUR_lsf {
   my $lrmsJobRecordFields = shift;
   
   my $shift1 = $$lrmsJobRecordFields[22];
   my $shift2 = $$lrmsJobRecordFields[23+$shift1];
   $urAcctlogInfo{server}=$$lrmsJobRecordFields[16].".".$domainName;
   $urAcctlogInfo{queue}=$$lrmsJobRecordFields[12];
   $urAcctlogInfo{user}=$$lrmsJobRecordFields[11];
   $urAcctlogInfo{lrmsId}=$$lrmsJobRecordFields[3];
   $urAcctlogInfo{processors}=$$lrmsJobRecordFields[6];
   if ($$lrmsJobRecordFields[10]) {
      $urAcctlogInfo{walltime}=$$lrmsJobRecordFields[2]-$$lrmsJobRecordFields[10];
      $urAcctlogInfo{cput}=int($$lrmsJobRecordFields[28+$shift2])+int($$lrmsJobRecordFields[29+$shift2]);
   } else {
      $urAcctlogInfo{walltime}=0;
      $urAcctlogInfo{cput}=0;
   }
   $urAcctlogInfo{cput} = 0 if ($urAcctlogInfo{cput} < 0);
   $urAcctlogInfo{mem}=$$lrmsJobRecordFields[54+$shift2]."k";
   $urAcctlogInfo{vmem}=$$lrmsJobRecordFields[55+$shift2]."k";
   $urAcctlogInfo{start}=$$lrmsJobRecordFields[10];
   $urAcctlogInfo{end}=$$lrmsJobRecordFields[2];
   $urAcctlogInfo{ctime}=$$lrmsJobRecordFields[7];
   if ($$lrmsJobRecordFields[23+$shift1]) {
      $urAcctlogInfo{execHost}=$$lrmsJobRecordFields[23+$shift2];
   }
   $urAcctlogInfo{jobName}=$$lrmsJobRecordFields[26+$shift2];
   $urAcctlogInfo{command}=$$lrmsJobRecordFields[27+$shift2];
   $urAcctlogInfo{exitStatus}=$$lrmsJobRecordFields[49+$shift2];
   
   # Get the number of Processors if the node is in exclusive mode.
   if  ( $urAcctlogInfo{command} =~ m/#BSUB -x/i
         && ((exists($urAcctlogInfo{execHost}) && $urAcctlogInfo{execHost} ne "") 
         && (!exists($urAcctlogInfo{processors}) || $urAcctlogInfo{processors} eq "" || $urAcctlogInfo{processors} eq "1") ) )
   {
         # Execute: lshosts $exec   Host
         # which returns
         #HOST_NAME      type    model  cpuf ncpus maxmem maxswp server RESOURCES
         #c485         X86_64   PC1133  23.1     8 16046M 16378M    Yes (mpich2)
         
         # print "Will execute lshost $urAcctlogInfo{execHost}\n";
         my $lshosts = $lsfBinDir."/lshosts";
         open FH, "$lshosts $urAcctlogInfo{execHost} |" or die "Failed to open pipeline to/from lshost";
         my @lines = <FH>;
         close(FH);
         print "Need: @lines\n";
         if ( scalar @lines == 2) {
            my @headers = split(/ +/,$lines[0]);
            my @values = split(/ +/,$lines[1]);
            my $search = "ncpus";
            my $index = first { $headers[$_] eq $search } 0 .. $#headers;
            # print "Found value for $search = $values[$index]\n";
            $urAcctlogInfo{processors} = $values[$index] || 1;
         }
   }
   # print "DEBUG: $urAcctlogInfo{execHost}\n";
}


sub determineUserVO()
{
   
   my $retVal = 1; # not found
   
   my $uFqan = $_[0];
   my $uid = $_[1];
   
   my @fqanParts = split(/\//, $uFqan);
   
   if (scalar(@fqanParts) > 1 && $fqanParts[1] ne "")
   {
      if ($fqanParts[1] =~ /^VO=(.*)$/o)
      {
         $fqanParts[1] = $1;
      }
      $_[2] = $fqanParts[1];
      $retVal = 0;
   }
   
   return $retVal;
}



# ---------------------------------------------------------------------------
#
# arguments: timestamp, timeZone(e.g. "+0200")
# returns a local time if the second argument is not "+0000" or "Z"
#
# ---------------------------------------------------------------------------
sub timestamp2String () {
   
   my $tstamp = $_[0];
   my $tzStr = $_[1];
   
   # parse timeZone:
   if ($tzStr eq "+0000" || $tzStr eq "Z") {
      $tzStr = "Z";
   }
   elsif ($tzStr =~ /^(\+|-)\d{4}/o) {
      my $hourDiff;
      my $minDiff;
      
      $hourDiff = int(substr($tzStr,0,3));
      $minDiff = int(substr($tzStr,3,2));
      
      #        if ($hourDiff < 0) { <- this is wrong since it misses e.g. -0030 !
      if ($tzStr =~ /^-/o) {
         # negative time zone, consider minutes negative as well!
         $minDiff = $minDiff * (-1);
      }
      
      # compute difference to UTC:
      $tstamp = $tstamp + ($hourDiff * 3600) + ($minDiff * 60);
      $tzStr = "Z";
   }
   else {
      print "Warning: Wrong timezone format: $tzStr - cannot convert timestamp\n";
      return "NULL";
   }
   
   my ($sec,$min,$hour,$mday,$mon,$year,$wday,$yday,$isdst);
   
   eval {
      ($sec,$min,$hour,$mday,$mon,$year,$wday,$yday,$isdst) = gmtime($tstamp);
   };
   if ($@) {
      print  "Warning: Wrong timestamp format: $tstamp - cannot convert timestamp\n";
      return "NULL";
   }
   
   my $sTime = "";
   # year
   $year = $year+1900;
   # month
   $mon = $mon+1;
   # day
   
   # hour
   $hour = $hour;
   # minute
   $min = $min;
   # second
   $sec = $sec;
   
   
   # composing string:
   $sTime = "".$year."-";
   if ($mon < 10) {
      $sTime = $sTime."0".$mon."-";
   }
   else {
      $sTime = $sTime.$mon."-";
   }
   if ($mday < 10) {
      $sTime = $sTime."0".$mday."T";
   }
   else {
      $sTime = $sTime.$mday."T";
   }
   if ($hour < 10) {
      $sTime = $sTime."0".$hour.":";
   }
   else {
      $sTime = $sTime.$hour.":";
   }
   if ($min < 10) {
      $sTime = $sTime."0".$min.":";
   }
   else {
      $sTime = $sTime.$min.":";
   }
   if ($sec < 10) {
      $sTime = $sTime."0".$sec;
   }
   else {
      $sTime = $sTime.$sec;
   }
   
   return $sTime.$tzStr;
}



# ---------------------------------------------------------------------------
#
# argument: time in seconds
# returns a phase string (time period) for a time in seconds
#
# ---------------------------------------------------------------------------
sub timeSecs2Period () {
   
   # compute it in the human readable format (as phase units):
   # Since the length of a month is unclear we prefer not to use it ...
   # according to the GGF UR-WG Usage Record - Format Recomendation
   # (draft of March 2005): "... only resources that are typically
   #  measured in month and year intervals should use that component
   #  of duration." (e.g. software licenses, etc.)
   
   my $tSecs = $_[0];
   
   my $timePeriodString = "P";
   
   if ($tSecs =~ /^\d*$/o) {
      
      my $remainingSecs = $tSecs;
      my $days = int($tSecs/86400);
      $remainingSecs = $remainingSecs - ($days * 86400);
      my $hours = int($remainingSecs/3600);
      $remainingSecs = $remainingSecs - ($hours * 3600);
      my $minutes = int($remainingSecs/60);
      $remainingSecs = $remainingSecs - ($minutes * 60);
      #print LOGFILE "days=$days; hours=$hours; minutes=$minutes; remainingSecs=$remainingSecs\n";
      if ($days > 0) {
         $timePeriodString = $timePeriodString."$days"."D";
      }
      $timePeriodString = $timePeriodString."T";
      if ($hours > 0) {
         $timePeriodString = $timePeriodString."$hours"."H";
      }
      if ($minutes > 0) {
         $timePeriodString = $timePeriodString."$minutes"."M";
      }
      if (!$tSecs or $remainingSecs > 0) {
         $timePeriodString = $timePeriodString."$remainingSecs"."S";
      }
      
   }
   else {
      print "Warning: Wrong time(seconds) format: $tSecs - cannot convert to time period\n";
      return "NULL";
   }
   
   return $timePeriodString;
}

sub populate_lrmsRecordFields {
   my ($lrmsType, $line) = @_;
   chomp $line;
   my @lrmsRecordFields = ();       # Reset
   if ($lrmsType eq "pbs") {
      # Simple, match previous behavior
      @lrmsRecordFields = split(" ", $line);
   } else {
      #     print "$line\n";
      my ($last_char, $token_buffer, $open_quote) = ("", "", 0);
      my @line_chars = split //, $line;
      my ($char, $error, $complete_token);
      while (scalar @line_chars) {
         $char = shift @line_chars;
         $token_buffer="${token_buffer}${char}";
         if ($char eq '"') {
            if ($line_chars[0] and $line_chars[0] eq '"') {
               # Next character is a quote: swallow it
               $char = shift @line_chars;
               $token_buffer="${token_buffer}${char}";
               unless ($open_quote) {
                  $complete_token = 1; # Finished
               }
            } elsif ($open_quote) { # Close a quote
               $open_quote = 0;
               # Finished string: push to @lrmsRecordFields
               $complete_token = 1;  # Finished
               # Expect a space or EOI
               if ($line_chars[0] and $line_chars[0] ne ' ') {
                  $error = "Non-space character following field-closing quote: $line_chars[0]";
                  last;
               }
            } else {                # Open a quote
               ++$open_quote;
            }
         } elsif ((not $open_quote) and $char eq ' ') {
            # Finished number or this is a simple delimiter: remove space
            chop $token_buffer;
            # If there's something left, it's a field.
            if (length($token_buffer)) {
               $complete_token = 1;  # Finished
            }
         }
         if ($complete_token) {
            # Empty string: push to @lrmsRecordFields
            if ($token_buffer =~ /^((?:[^-\+\"\.\d]|[-\+\.\d]+[^-\+\.\d]).*)$/o) {
               # Unquoted non-numeric
               $error = "Unquoted non-numeric field: $1";
               last;                 # exit
            }
            # Remove surrounding quotes if present
            $token_buffer =~ s&^"(.*)"$&$1&o;
            push @lrmsRecordFields, $token_buffer;
            $token_buffer = "";
            undef $complete_token;
         }
      }
      if (not $error) {
         # Check for global problems
         if ($open_quote) {
            $error = "Open quote at end of line";
         } elsif (not scalar @lrmsRecordFields) {
            $error = "Empty input line";
         } elsif (grep /^"JOB_FINISH"$/o, @lrmsRecordFields[1 .. (@lrmsRecordFields - 1)]) {
            $error = "Two lines concatenated";
         }
      }
      if ($error) {
         # Error
         print scalar(localtime()), ": ERROR: $error\n";
         print scalar(localtime()), ": Unable to parse received line: fields as follows - ",
         join(", ", map { "*$_*" } @lrmsRecordFields), "\n";;
         @lrmsRecordFields = ();
      }
   }
   return \@lrmsRecordFields;
}
