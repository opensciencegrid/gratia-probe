This directory contains an export of 20 test jobs from a SLURM 2.6pre4
accounting database for a cluster named "slurmtest".

* IDs range from 200561 to 200580
* Total CPU hours should be 1720
* Jobs vary in core count
* Some jobs have been preempted and resumed

Using the command-line test tool to summarize CPU hours per day:

	$ ./slurm_meter_test -p password -D database -c slurmtest -s 0
	Retrieving jobs completed after 1970-01-01T00:00:00
	Date      	Jobs   	Hours 
	----------	-------	-------
	2013-07-05	7	14
	2013-07-06	8	166
	2013-07-07	5	1539
	----------	-------	-------
	total     	20	1720
