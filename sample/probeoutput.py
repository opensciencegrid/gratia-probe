

def get_ce(probe_name, server_id, ce_name, lrms_name, lrms_version, cluster, time_now):
    r = ComputeElement.ComputeElement() 

    # use config in caller
    #ce_name = Gratia.Config.getConfigAttribute('CEName')

    r.UniqueID('%s:%s/%s' % (probe_name, server_id, cluster))
    r.CEName(ce_name)
    r.Cluster(ce_name)
    r.HostName(ce_name)
    r.Timestamp(str(time_now) + "Z")
    r.LrmsType(lrms_name)
    r.LrmsVersion(lrms_version)

    return r

def user_to_cer(probe_name, user, server_id, time_now):
    # user is a dictionary containing user accounting information (VO/username, cpus running, cpus pending, cluster
    r = ComputeElementRecord.ComputeElementRecord() 

    r.UniqueID('%s:%s/%s' % (probe_name, server_id, user['cluster']))
    r.VO(user['user'])
    r.Timestamp(str(time_now) + "Z")
    r.RunningJobs(user['cpus_running'])
    r.WaitingJobs(user['cpus_pending'])
    r.TotalJobs(user['cpus_running'] + user['cpus_pending'])

    return r



# Usage Record from the OGF Usage Record WG
# This website does not exist any more
# https://forge.gridforum.org/projects/ur-wg/
# https://forge.gridforum.org/sf/docman/do/downloadDocument/projects.ur-wg/docman.root.final_document.ur_v1/doc15329
# The OLD standard definition (GFD-R-P.098) is available here:
# https://redmine.ogf.org/dmsf/ur-wg?folder_id=6520
# NEW url of the standard repository
# http://redmine.ogf.org/projects/ur-wg
# Here is the new standard document (GWD-R UR-WG)
# https://redmine.ogf.org/dmsf_files/13010?download=



def job_to_jur(job, server_id):
    """Convert a job record into a Gratia UsageRecord"""
    r = Gratia.UsageRecord("Batch")

    # 3 Base Properties

    # 3.2 GlobalJobId
    # "slurm:<hostname>/<cluster>.<job>"
    r.GlobalJobId('slurm:%s/%s.%s' % (server_id, job['cluster'], job['id_job']))

    # 3.3 LocalJobId
    r.LocalJobId(str(job['id_job']))

    # 3.4 ProcessId

    # 3.5 LocalUserId
    if job['user']:
        r.LocalUserId(job['user'])

    # 3.7 JobName
    if job['job_name']:
        r.JobName(job['job_name'])

    # 3.9 Status
    r.Status(job['exit_code'])

    # 4.6 Processors
    # if cpus allocated is unreadable or < 1,
    #    then set to 1 and write a warning.
    cpus_allocated = 0
    if job['cpus_alloc']:
        cpus_allocated = int(job['cpus_alloc'])
    else:
        DebugPrint(2, "CPUs allocated for job %s is not readable.  Below is the full job description" % (str(job['id_job'])))
        DebugPrint(2, str(job))
        cpus_allocated = 1
        DebugPrint(2, "Setting CPUs allocated to %s" % cpus_allocated)
    if cpus_allocated < 1:
        DebugPrint(2, "CPUs allocated(%s) < 1 on job %s.  Below is the full job description" % (cpus_allocated,str(job['id_job'])))
        DebugPrint(2, str(job))
        cpus_allocated = 1
        DebugPrint(2, "Setting CPUs allocated to %s" % cpus_allocated)
    r.Processors(cpus_allocated)

    # 3.10 WallDuration and 3.11 CpuDuration
    # The validations here attempt to take into account multi-core processors
    # and the reporting by the job managers for wall and cpu.
    # For example, a 2 core node,
    #    could have wall of 1 day and total cpu of 2 days
    # So, the number of cores (cpus allocated) is a factor in evaluating
    # thresholds for wall and cpu time.
    # The intent here is to avoid sending garbage up to Gratia.
    #
    # If the user or system cpu unreadable,
    #    then set to 0 and write a warning
    # If the wall time is unreadable,
    #    then set to total cpu / cpus_allocated and write a warning
    # If either system or user cpu exceed the cpu threshold,
    #    then assume a job manager error, set to zero and write a warning
    # If the (wall time * cpus allocated) is over n days,
    #    then set the walltime to n days and write a warning
    # If total cpu exceeds (wall time * cpus allocated),
    #    then set wall to the (total cpu / cpus allocated) and write a warning

    # thresholds for wall and cpu times
    threshold_days = 60
    wall_threshold = 86400 * threshold_days
    cpu_threshold  = wall_threshold * cpus_allocated

    # User CPU validations
    usercpu = 0.0
    if job['cpu_user']:
        usercpu = float(job['cpu_user'])
    else:
        DebugPrint(2, "User CPU for job %s is not readable.  Below is the full job description" % (str(job['id_job'])))
        DebugPrint(2, str(job))
        usercpu = 0.0
        DebugPrint(2, "Setting User CPU to %s" % usercpu)

    if usercpu > cpu_threshold:
        DebugPrint(2, "User CPU time (%f) for job %s > %s days.  Below is the full job description" % (usercpu,str(job['id_job']),threshold_days))
        DebugPrint(2, str(job))
        usercpu = 0
        DebugPrint(2, "Setting User CPU to %f" % usercpu)

    # System CPU validations
    systemcpu = 0.0
    if job['cpu_sys']:
        systemcpu= float(job['cpu_sys'])
    else:
        DebugPrint(2, "System CPU for job %s is not readable.  Below is the full job description" % (str(job['id_job'])))
        DebugPrint(2, str(job))
        systemcpu = 0.0
        DebugPrint(2, "Setting System CPU to %s" % systemcpu)

    if systemcpu > cpu_threshold:
        DebugPrint(2, "User CPU time (%f) for job %s > %s days.  Below is the full job description" % (systemcpu,str(job['id_job']),threshold_days))
        DebugPrint(2, str(job))
        systemcpu = 0
        DebugPrint(2, "Setting System CPU to %s" % systemcpu)

    # Wall time validations
    walltime = 0
    if job['wall_time']:
        walltime = float(job['wall_time'])
    else:
        DebugPrint(2, "Wall time for job %s is not readable.  Below is the full job description" % (str(job['id_job'])))
        DebugPrint(2, str(job))
        walltime = (usercpu + systemcpu) / cpus_allocated
        DebugPrint(2, "Setting Wall time to %s" % walltime)

    if walltime > wall_threshold:
        DebugPrint(2, "Wall time (%f) for job %s > %s days.  Below is the full job description" % (walltime,str(job['id_job']),threshold_days))
        DebugPrint(2, str(job))
        walltime = wall_threshold
        DebugPrint(2, "Setting Wall time to %s" % walltime)

    if (walltime * cpus_allocated) < (usercpu + systemcpu):
        DebugPrint(2, "Wall time is less than total CPU for job %s: wall(%f) cpus(%s) user cpu(%f) system cpu(%f).  Below is the full job description" % \
            (str(job['id_job']),walltime,cpus_allocated,usercpu,systemcpu))
        DebugPrint(2, str(job))
        walltime = (usercpu + systemcpu) / cpus_allocated
        DebugPrint(2, "Setting Walltime to CPU: %s" % walltime)


    r.WallDuration(walltime)
    r.CpuDuration(usercpu,   "user",   "Was entered in seconds")
    r.CpuDuration(systemcpu, "system", "Was entered in seconds")

    # 3.12 EndTime
    r.EndTime(job['time_end'],"Was entered in seconds")

    # 3.13 StartTime
    r.StartTime(job['time_start'],"Was entered in seconds")

    # 3.14 MachineName
    # 3.15 Host
    # 3.16 SubmitHost

    # 3.17 Queue
    r.Queue(job['partition'])

    # 3.18 ProjectName
    if job['acct']:
        r.ProjectName(job['acct'])

    # 4 Differentiated Properties

    # 4.1 Network
    # 4.2 Disk

    # 4.3 Memory
    if job['max_rss']:
        r.Memory(job['max_rss'], 'kB', description = "RSS")

    # 4.4 Swap
    # 4.5 NodeCount

    # 4.6 Processors
    r.Processors(job['cpus_alloc'])

    # 4.7 TimeDuration
    # 4.8 TimeInstant
    # 4.9 Service Level
    # 4.10 Extension

    return r

