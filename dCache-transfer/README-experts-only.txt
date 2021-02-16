# Copyright 2007 Cornell University, Ithaca, NY. All rights reserved.

From Gregory Sharp. Modified by Ted Hesselroth and Chris Green.

NOTE: this README is intended only for packagers and experts; please
refer to the README provided with the RPM / VDT version of this probe
for end-user information.

------------------------------------------------------------------------

This directory contains the dCache Gratia Probe.
It is a python program that reads out the dCache billing database and
sends any relevant information to Gratia.


FILES:
=====
README - this file that you are reading now.
install.sh - the installation script.
Alarm.py - detects error conditions and sends a warning email.
Checkpoint.py - python code to record the last record sent to Gratia.
CheckpointTest.py - a set of unit tests for Checkpoint.py.
DCacheAggregator.py - code that reads the billing db, packages it and
                      sends it to Gratia.
dCacheBillingAggregator.py - this is the main routine.
Gratia.py - the Gratia library.
ProbeConfig - this is the Gratia configuration file. It tells the Aggregator
              where to find the Gratia server, security setup, etc.
external/psycopg2-2.0.5.1.tar.gz - the psycopg2 python module.


HOW IT WORKS:
============
The Aggregator reads the Postgres billing database produced by dCache.
This version only reads the "billinginfo" and "doorinfo" tables.
The first time it runs, the Aggregator scans the billinginfo table for records.
It gets the corresponding "initiator" information from the doorinfo table.
It packages up all the records it finds and sends them to Gratia, one at a
time. After sending each record, it stores the datestamp and transaction field
for the sent record in a "Checkpoint" file. The checkpoint is stored in the
DataFolder directory (specified in the ProbeConfig file).
Once all the newly found rows have been sent, it sleeps for the
"UpdateFrequency" interval.
When it wakes up again (or is restarted after a shutdown), the next search of
the billinginfo table starts from the last checkpointed datestamp and
transaction fields.
This might resend some duplicate records to Gratia (but very few). Gratia
detects duplicates and does not store them. The Aggregator assumes that Gratia
will ignore duplicates and report "OK" when this happens.

For performance reasons, sites with large dCache billing databases are advised
to alter the billinginfo table by adding an index on the pair of columns
    (datestamp, transaction)
and to alter the doorinfo table by adding an index on the (transaction) column.
This should speed up the search for newly added records.


UPGRADING:
=========

If you are upgrading, please make sure that the checkpoint file(s) 
are not lost or damaged. The upgraded installation will
need those file(s) to know which records have been sent to Gratia already.


INSTALLATION:
============

The Aggregator is written in Python. It relies on three other 3rd-party
packages: Python, Gratia and psycopg2. The following is a
step-by-step for getting everything to work.

1. Untar the package on the node which is running postgres for the billing
   cell. The billing cell normall runs in the dCache http domain and uses
   a postgres installed on the same node.

2. Ensure that you have Python 2.3.4 or newer and postgres 7.3 or newer.
   Ensure that python is in your path and the PYTHONPATH shell variable is
   not set. Module psycopg2 will be installed
   or upgraded. For psycopg2, python's datetime module header must available
   in the python installation.

3. Change to the gratia directory created from step 1 and run install.sh.
   You may run it as "install.sh -d" for the dryrun option - it will print
   what it would do but not execute any commands.

4. (Optional) Edit the ProbeConfig, and modify variables to your liking.
   Notes:
    1. SSLRegistrationHost uses port 8880 (the production server). Set this
       to port 8881 (the test server) for testing purposes.
    2. The "MeterName" the "SiteName" will have the hostname of the node you
       are installing on. Edit these lines if you wish to use another name,
       such as your srm node.
    3. You may wish to adjust the "LogLevel" and "DebugLevel".
    4. The directory name "MAGIC_VDT_LOCATION" can be left as is.
    5. Values for data, log, and tmp can be set to full paths of other
       directories.
    6. The UpdateFrequency is in seconds.
    7. DBHostName is localhost. Alter this if the node is not as per step 1.
    8. DCacheServerHost is the name of the host where the dCache master
       server runs. This WILL be sent to Gratia. If you don't want to publish
       the server name, put a fake hostname followed by your domain name.
       Do NOT use a fake domain name, or the statistics in the gratia database
       will be almost useless.
    9. LoggingDir can be set to the full path of another directory if you wish
       the logs to be separate from the installation directory.
   10. The EmailToList may contain more than one email address. Separate
       multiple email addresses with a comma and one space. For example,
       EmailToList="foo@yourDomain.edu, bar@yourDomain.edu"
   11. The "EmailFromAddress" does not need to be a valid address. It should
       be of the form "foo@yourDomain.edu". Some mail systems will reject it,
       or rewrite the domain if you use something other than the local domain.
   12. The SMTP server is the mail server to which email alarms will be sent.
       In many cases, "localhost" is okay. However, test this by stopping the
       Aggregator. The members of the "EmailToList" should each receive email
       warning that the dCache Probe has stopped.
   13. Valid logging levels for AggrLogLevel are "debug", "info", "warn" and
       "error". Any other value will result in the default of "debug".

      
STARTING:
========
1. Change directory to the directory where the dCacheBillingAggregator is
   installed.

2. Run the command:

   nohup python dCacheBillingAggregator.py &

   This will start the program up in the background.
   The Gratia logs and state information will appear in the LogFolder
   directory. The default for this is "logs" in the dCacheBillingAggregator
   directory.  Messages from the Aggregator will appear in the log file
   dcache2gratia.log in the LogFolder directory.
   If you enable debugging in ProbeConfig, the nohup.out file will be filled
   with print messages from Gratia. Otherwise, it should be empty.


STOPPING:
========
To STOP the Aggregator, you can either:
1. Create the stop file specified in the ProbeConfig file.
   The Aggregator checks for the stop file after each record. It should
   shut down within a few seconds.

2. If the above doesn't work, send it a kill -2 (control-C). Only do this
   if the stop file doesn't work.
   

TESTING:
=======
1. Open the web page
      http://gratia-osg.fnal.gov:8880/gratia-reporting/
   or other address based on the value of SSLRegistrationHost in ProbeConfig.

2. Click on "Custom SQL Report" in the left frame.

3. In the text box, enter

SELECT N.Value, N.StorageUnit, N.PhaseUnit,
N.Value/N.PhaseUnit/1024.0 as RateInMbPerSecond,
J.VOName, J.CommonName, J.Status, J.WallDuration, J.StartTime,
J.EndTime, J.SiteName, J.SubmitHost
FROM JobUsageRecord J, Network N
where J.ProbeName like 'dcache%' and J.dbid = N.dbid
and J.CommonName like 'Ted%' and EndTime > '2007/01/24'

  with the applicable CommonName and EndTime.

4. Click the Execute button. A table of billing records will be displayed.

5. Self testing

Probe can be run in the self test mode. In this mode, Billing db records are 
consistently sumulated such that resulting Gratia record output can be
verified against known pattern. In order to enable self test mode, TEST variable
must be set to 1. This variable is defined in TestContainer.py file.
Before running the probe in the self test mode,  the checkpoint file  must be removed.
In order to observe self test output , set    AggrLogLevel to "debug"

The assertion is that statistics of records in the Billing db and
statistics of records send to Gratia after summarization (complicated by
restarts and query window limit management)as reported at the end of the
run should be the same:

Property of the simulated billing DB:
number of records per second : 2
time covered: 4 hours 700 seconds
number of records : 30200

Other params:
STARTING_MAX_SELECT = 50
MAX_SELECT = 100
STARTING_RANGE = 60
MIN_RANGE = 1

Number of restarts:
Aprox: 1 restart for every 15 records send to Gratia UNION 1 restart for
every 300 query invocations

Results:

2010-05-05 11:10:35,072 INFO Send to gratia:
2010-05-05 11:10:35,072 INFO Overall 30200
2010-05-05 11:10:35,072 INFO initiator 10124
2010-05-05 11:10:35,072 INFO errorcode 30200
2010-05-05 11:10:35,073 INFO num records  54
2010-05-05 11:10:35,073 INFO Generated:
2010-05-05 11:10:35,153 INFO Overall 30200
2010-05-05 11:10:35,153 INFO initiator 10124
2010-05-05 11:10:35,153 INFO errorcode 30200
2010-05-05 11:10:35,153 INFO num records  30200

PROFILING:
=========
If you find that the probe is not sending records quickly enough to Gratia
(for example, you have a backlog of records) you can profile the performance
and find the bottlenecks.

The profiling doesn't include the sleep time, just the time
it spent actually trying to discover and send records.

If the time spent in querying the dCache database is excessive, you
may benefit from adding an index on the (datestamp, transaction) fields
in the billinginfo table, and on the transaction field in the doorinfo
table.

****
  This is NOT intended for normal use. This is for debugging if you
  are experiencing performance problems. It is also only for people
  who understand python. If you don't understand python, only do this
  with the aid of a Gratia support person, or better yet, let them
  log in and run this.
*****

To start the probe with profiling enabled, use

    python dCacheBillingAggregator.py -profile

and let it run for 5 to 10 minutes. Check the log file to ensure that it
is indeed sending a significant number of records. Once it has sent at least
100 records, create the stop file (in another window) and within a few
minutes it will stop and print out some statistics about where the program
spent its time.

