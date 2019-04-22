Raw XML for Slurm Probe Records
================================


### RawXML for a `slurm` probe record:

```
<JobUsageRecord>
<RecordIdentity urwg:createTime="2019-03-26T19:43:54Z" urwg:recordId="cms.ufhpc:3444492.622"/>
<JobIdentity>
        <GlobalJobId>slurm:slurmdb-mgmt/3307/slurm/hipergator.34033351</GlobalJobId>
        <LocalJobId>34033351</LocalJobId>
</JobIdentity>
<UserIdentity>
        <LocalUserId>cmspilot</LocalUserId>
        <VOName>/cms/uscms/Role=pilot/Capability=NULL</VOName>
        <ReportableVOName>cms</ReportableVOName>
        <DN>/DC=ch/DC=cern/OU=computers/CN=cmspilot01/vocms080.cern.ch</DN>
</UserIdentity>
        <JobName>bl_cms914c44d277b1</JobName>
        <Status>0</Status>
        <Processors urwg:metric="total">8</Processors>
        <WallDuration>PT24M54.0S</WallDuration>
        <CpuDuration urwg:description="Was entered in seconds" urwg:usageType="user">PT34.92S</CpuDuration>
        <CpuDuration urwg:description="Was entered in seconds" urwg:usageType="system">PT29.0S</CpuDuration>
        <EndTime urwg:description="Was entered in seconds">2019-03-26T19:42:26Z</EndTime>
        <StartTime urwg:description="Was entered in seconds">2019-03-26T19:17:32Z</StartTime>
        <Queue>hpg1-compute</Queue>
        <ProjectName>avery</ProjectName>
        <Memory urwg:description="RSS" urwg:metric="total" urwg:storageUnit="kB">20480</Memory>
        <ProbeName>slurm:cms.rc.ufl.edu</ProbeName>
        <SiteName>UFlorida-HPC</SiteName>
        <Grid>OSG</Grid>
        <Njobs>1</Njobs>
        <Resource urwg:description="ResourceType">Batch</Resource>
</JobUsageRecord>
```

