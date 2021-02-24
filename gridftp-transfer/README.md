# gratia-probe-gridftp

This is an example overhaul of the Gratia GridFTP probe.

Based on recent changes to the OSG GridFTP configuration, all necessary
information for the GridFTP probe is in gridftp-auth.log.  Hence, we don't
need to do a join between two log files - we can scan linearly through just one.

The tricky portion is splitting events over multiple logfiles and "looking back"
to previous logfiles to find transfer information.  Note that, over time, the
PID is reused - hence it's tricky to use it as a unique identifier.

# Testing

To generate some test events, do:

```
pushd test
./test_driver.sh
```

The fully formed Gratia record should be printed out.

