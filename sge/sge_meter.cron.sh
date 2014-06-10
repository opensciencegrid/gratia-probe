#!/bin/bash
#
# sge_meter.cron.sh - Shell script used with cron to parse sge log 
#   files for OSG accounting data collection.

# $Id$
# Full Path: $HeadURL$

Logger='/usr/bin/logger -s -t sge_meter'

# NOTE: some of the comments in this script indicate work still to be done.
#   The places that still require attention are marked with '###'.  Questions
#   still to be answered also include '???'.

# To direct the e-mail that may be output by this script, enter the crontab
#    entry where MAILTO is the destination address, in a form like:
# MAILTO=root
# 3,13,23,33,43,53 * * * *  $VDT_LOCATION/gratia/sge_meter.cron.sh
#    and using the full path of the VDT location rather than an Env Variable 

# These values were used during testing
#sgeLog_Dir='/export/osg/grid/globus/tmp/gram_job_state'  # on fngp-osg
#sgeLog_Dir='/usr/local/vdt-1.3.6/globus/tmp/gram_job_state'  # on fermigrid1
#sgeLog_Dir='/usr/local/vdt-1.3.9/globus/tmp/gram_job_state'  # on fermigrid1

Meter_BinDir=$(dirname $0)
if [ "x$1" != "x" ] ; then
   probeconfig_loc=$1
else
   probeconfig_loc=/etc/gratia/sge/ProbeConfig
fi

[[ -n "$1" ]] && sge_log_file="$1"

# Set the working directory, where we expect to find the following
#    necessary files.
if [ -d ${Meter_BinDir} ]; then
  cd ${Meter_BinDir}
else
  ${Logger} "No such directory ${Meter_BinDir}"
  exit -1
fi
  
# Need to be sure there is not one of these running already
NCMeter=`ps -ef | grep sge_meter | grep -v grep | wc -l`
eval `grep WorkingFolder $probeconfig_loc`
if [ ${NCMeter} -ne 0 -a -e ${WorkingFolder}/sge_meter.cron.pid ]; then
  # We might have a condor_meter.pl running, let's verify that we 
  # started it.
  
  otherpid=`cat ${WorkingFolder}/sge_meter.cron.pid`
  # exit if otherpid is non-empty and still running
  if [[ -n ${otherpid} && -e /proc/${otherpid} ]]; then
     ${Logger} "There is a 'sge_meter.py' task running already."
     exit 0
  fi
fi

# We need to locate the sge probe script and it must be executable
if [ ! -x sge_meter ]; then
  ${Logger} "The sge_meter file is not in this directory: $(pwd)"
  exit -2
fi
  
# We need to locate these files and they must be readable
for Needed_File in $probeconfig_loc
do
  if [ ! -f ${Needed_File} ]; then
    ${Logger} \
     "The ${Needed_File} file is not in this directory: $(pwd)"
    exit -3
  fi
done
  
# This is what we expect in a normal Gratia install
pp_dir=$(cd "$Meter_BinDir/../common"; pwd)

enabled=`${pp_dir}/GetProbeConfigAttribute -c $probeconfig_loc EnableProbe`
(( status = $? ))
if (( $status != 0 )); then
  echo "ERROR checking probe configuration!" 1>&2
  exit $status
fi
if [[ -n "$enabled" ]] && [[ "$enabled" == "0" ]]; then
  ${pp_dir}/DebugPrint -c $probeconfig_loc -l -1 "Probe is not enabled: check $Meter_BinDir/ProbeConfig."
  exit 1
fi

WorkingFolder=`${pp_dir}/GetProbeConfigAttribute -c $probeconfig_loc WorkingFolder`
if [ ! -d ${WorkingFolder} ]; then
  if [ "x${WorkingFolder}" != "x" ] ; then 
    mkdir -p ${WorkingFolder}
  else
    ${Logger} "There is no WorkingFolder directory defined in $Meter_BinDir/ProbeConfig."
    exit -4
  fi
fi

echo $$ > ${WorkingFolder}/sge_meter.cron.pid
(( status = $? ))
if (( $status != 0 )); then
   ${Logger} "sge_meter.cron.sh failed to store the pid in ${WorkingFolder}/sge_meter.cron.pid"
   exit -2
fi 

# Note: location of accounting file should be specified in ProbeConfig
./sge_meter -c
ExitCode=$?
# If the probe ended in error, report this in Syslog and exit
if [ $ExitCode != 0 ]; then
  ${pp_dir}/DebugPrint  -c $probeconfig_loc -l -1 "ALERT: $0 exited abnormally with [$ExitCode]"
  exit $ExitCode
fi
    
exit 0

