Raw XML for Condor Probe Records
================================

Here are sample XML records sent for ResourceType = Batch and BatchPilot
(aka Payload) jobs.


### RawXML for `ResourceType=Batch`:

```
<JobUsageRecord>
<RecordIdentity urwg:createTime="2019-04-18T21:10:07Z" urwg:recordId="uct2-gk.mwt2.org:2965220.138"/>
<JobIdentity>
	<GlobalJobId>condor.uct2-gk.mwt2.org#699399.0#1555621594</GlobalJobId>
	<LocalJobId>699399</LocalJobId>
</JobIdentity>
<UserIdentity>
	<LocalUserId>usatlas1</LocalUserId>
	<GlobalUsername>usatlas1@osg-gk.mwt2.org</GlobalUsername>
	<DN>/DC=ch/DC=cern/OU=Organic Units/OU=Users/CN=jhover/CN=653174/CN=John Raymond Hover</DN>
	<VOName>/atlas/usatlas/Role=production/Capability=NULL</VOName>
	<ReportableVOName>atlas</ReportableVOName>
</UserIdentity>
	<JobName>uct2-gk.mwt2.org#699399.0#1555621594</JobName>
	<MachineName>uct2-gk.mwt2.org</MachineName>
	<SubmitHost>uct2-gk.mwt2.org</SubmitHost>
	<Status urwg:description="Condor Exit Status">0</Status>
	<WallDuration urwg:description="Was entered in seconds">PT2M32.0S</WallDuration>
	<TimeDuration urwg:type="RemoteUserCpu">PT2.0S</TimeDuration>
	<TimeDuration urwg:type="LocalUserCpu">PT0S</TimeDuration>
	<TimeDuration urwg:type="RemoteSysCpu">PT0S</TimeDuration>
	<TimeDuration urwg:type="LocalSysCpu">PT0S</TimeDuration>
	<TimeDuration urwg:type="CumulativeSuspensionTime">PT0S</TimeDuration>
	<TimeDuration urwg:type="CommittedSuspensionTime">PT0S</TimeDuration>
	<TimeDuration urwg:type="CommittedTime">PT2M32.0S</TimeDuration>
	<CpuDuration urwg:description="Was entered in seconds" urwg:usageType="system">PT0S</CpuDuration>
	<CpuDuration urwg:description="Was entered in seconds" urwg:usageType="user">PT2.0S</CpuDuration>
	<EndTime urwg:description="Was entered in seconds">2019-04-18T21:09:15Z</EndTime>
	<StartTime urwg:description="Was entered in seconds">2019-04-18T21:06:43Z</StartTime>
	<Host primary="true">uct2-c430.mwt2.org</Host>
	<Queue urwg:description="Condor's JobUniverse field">5</Queue>
	<NodeCount urwg:metric="max">1</NodeCount>
	<Processors urwg:metric="max">1</Processors>
	<Resource urwg:description="CondorMyType">Job</Resource>
	<Resource urwg:description="AccountingGroup">group_atlas.prod.score.himem.usatlas1</Resource>
	<Resource urwg:description="ExitBySignal">false</Resource>
	<Resource urwg:description="ExitCode">0</Resource>
	<Resource urwg:description="condor.JobStatus">4</Resource>
	<Network urwg:metric="total" urwg:phaseUnit="PT2M32.0S" urwg:storageUnit="b">0</Network>
	<ProbeName>condor:uct2-gk.mwt2.org</ProbeName>
	<SiteName>MWT2_CE_UC</SiteName>
	<Grid>OSG</Grid>
	<Njobs>1</Njobs>
	<Resource urwg:description="ResourceType">Batch</Resource>
</JobUsageRecord>
```


### RawXML for `ResourceType=Payload`:

```
<JobUsageRecord>
<RecordIdentity urwg:createTime="2019-04-14T00:11:54Z" urwg:recordId="xd-login.opensciencegrid.org:1953476.608"/>
<JobIdentity>
	<GlobalJobId>condor.xd-login.opensciencegrid.org#130244362.0#1555195970</GlobalJobId>
	<LocalJobId>130244362</LocalJobId>
</JobIdentity>
<UserIdentity>
	<LocalUserId>donkri</LocalUserId>
	<DN>/OU=LocalUser/CN=donkri</DN>
	<GlobalUsername>donkri@xd-login.opensciencegrid.org</GlobalUsername>
<VOName>/osg/LocalGroup=xsede</VOName><ReportableVOName>osg</ReportableVOName></UserIdentity>
	<JobName>xd-login.opensciencegrid.org#130244362.0#1555195970</JobName>
	<MachineName>xd-login.opensciencegrid.org</MachineName>
	<SubmitHost>xd-login.opensciencegrid.org</SubmitHost>
	<Status urwg:description="Condor Exit Status">0</Status>
	<WallDuration urwg:description="Was entered in seconds">PT10M59.0S</WallDuration>
	<TimeDuration urwg:type="RemoteUserCpu">PT7M29.0S</TimeDuration>
	<TimeDuration urwg:type="LocalUserCpu">PT0S</TimeDuration>
	<TimeDuration urwg:type="RemoteSysCpu">PT9.0S</TimeDuration>
	<TimeDuration urwg:type="LocalSysCpu">PT0S</TimeDuration>
	<TimeDuration urwg:type="CumulativeSuspensionTime">PT0S</TimeDuration>
	<TimeDuration urwg:type="CommittedSuspensionTime">PT0S</TimeDuration>
	<TimeDuration urwg:type="CommittedTime">PT10M59.0S</TimeDuration>
	<CpuDuration urwg:description="Was entered in seconds" urwg:usageType="system">PT9.0S</CpuDuration>
	<CpuDuration urwg:description="Was entered in seconds" urwg:usageType="user">PT7M29.0S</CpuDuration>
	<EndTime urwg:description="Was entered in seconds">2019-04-13T23:59:59Z</EndTime>
	<StartTime urwg:description="Was entered in seconds">2019-04-13T23:49:00Z</StartTime>
	<Host primary="true" urwg:description="TACC">c506-114.stampede2.tacc.utexas.edu</Host>
	<Queue urwg:description="Condor's JobUniverse field">5</Queue>
	<NodeCount urwg:metric="max">1</NodeCount>
	<Processors urwg:metric="max">1</Processors>
	<Resource urwg:description="CondorMyType">Job</Resource>
	<Resource urwg:description="AccountingGroup">group_opportunistic.IBN130001-Plus.donkri</Resource>
	<Resource urwg:description="ExitBySignal">false</Resource>
	<Resource urwg:description="ExitCode">0</Resource>
	<Resource urwg:description="condor.JobStatus">4</Resource>
	<ProjectName urwg:description="As specified in Condor submit file">IBN130001-Plus</ProjectName>
	<Network urwg:metric="total" urwg:phaseUnit="PT10M59.0S" urwg:storageUnit="b">0</Network>
	<ProbeName>condor:xd-login.opensciencegrid.org</ProbeName>
	<SiteName>XD-LOGIN</SiteName>
	<Grid>OSG</Grid>
	<Njobs>1</Njobs>
	<Resource urwg:description="ResourceType">BatchPilot</Resource>
</JobUsageRecord>
```

#### Notes

The key difference is the "payload" jobs (ResourceType=Payload in GRACC, ResourceType=BatchPilot in the xml sent by the
gratia-probe) are identified when they have a MATCH_EXP_JOBGLIDEIN_ResourceName attribute in their classad, as found in
the condor history logfile.

Note that none of the other batch probes (that is, other than condor) are able to report as payload jobs.

