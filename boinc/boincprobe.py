#!/usr/bin/python
# -*- coding: utf-8 -*-

# Gratia probe

from __future__ import print_function

import os
import shutil

import gratia.common.Gratia as Gratia

# Note: meant for use on the Clemson network with
# condor jobs running BOINC processes. Any other use
# will require significant alteration.

BASEDIR = '/home/gprobe/Data/'
flist = os.listdir(BASEDIR)

# test file
# file = 'history.COES-MCAD120-1#1256755408#1#1256755408'

# Fields that we're going to populate

starttime = ''
walltime = ''
localjobid = ''
endtime = ''
user = 'Einstein@Home'

Gratia.RegisterReporterLibrary('myprobe.py')

for var in flist:
    if var.count('history') > 0:
        fd = open('/home/gprobe/Data/' + var)
        lines = fd.readlines()
        boincjob = False

        for var2 in lines:
            if var2.count('QDate') > 0:
                starttime = var2.split()[2]
            elif var2.count('RemoteWallClockTime') > 0:
                walltime = var2.split()[2]
            elif var2.count('CompletionDate') > 0:
                endtime = var2.split()[2]
            elif var2.count('Owner') > 0:
                if var2.split()[2] == '"boinc"':
                    boincjob = True

        if boincjob == True:
            Gratia.setProbeBatchManager('Condor')
            Gratia.Initialize()
            r = Gratia.UsageRecord('Condor')
            r.ResourceType('Backfill')

      # parsing the filenames for the hostname/localjobid.
      # the files are in the format: history.<hostname>#<localjobid>#1#<localjobid>

            host = var.partition('.')[2].partition('#')[0]
            localjobid = var.partition('.')[2].partition('#')[2].partition('#')[0]

      # print 'endtime: ' + endtime
      # print 'starttime: ' + starttime
      # print 'walltime: ' + walltime

      # Gratia likes ints, not strings, for times.

            r.LocalJobId(localjobid)
            r.EndTime(int(endtime))
            r.StartTime(int(starttime))
            r.Njobs(1)
            r.WallDuration(int(walltime))
            r.LocalUserId('labuser')
            r.MachineName('clemson-boinc')
            r.Host(host, True)
            r.CpuDuration(int(walltime), 'user')
            r.CpuDuration(0, 'system')
            r.VOName('LIGO')

            print(Gratia.Send(r))
            shutil.move('/home/gprobe/Data/' + var, '/home/gprobe/Data/parsed/' + var)
        else:

      # Get rid of the file, since it is
      # not a boinc job.

            os.remove(BASEDIR + var)

      # print "Not a boinc job.. returning."
