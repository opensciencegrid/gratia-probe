#!/usr/bin/env ruby

VERSION_STRING="0.4"

##############################################################################
# Environment Configuration
##############################################################################

ONE_LOCATION=ENV["ONE_LOCATION"]
 
if !ONE_LOCATION
    RUBY_LIB_LOCATION="/usr/lib/one/ruby"
else
    RUBY_LIB_LOCATION=ONE_LOCATION+"/lib/ruby"
end
 
$: << RUBY_LIB_LOCATION
 
##############################################################################
# Required libraries
##############################################################################

require 'pp'
require 'optparse'
require 'singleton'
begin
	require 'opennebula'
	require 'opennebula/pool'
rescue LoadError
	require 'OpenNebula'
	require 'OpenNebula/Pool'
end
 
include OpenNebula
 
##############################################################################
# Classes
##############################################################################

class OpenNebulaSensorCache

    attr_reader :is_valid, :queued_vm_ids, :last_known_id, :etime, :filename

    #######################################################################
    # Constants and Class Methods
    #######################################################################
        
    # Class constructor
    def initialize(rtime=Time.now().to_i(), stime=0, etime=0,
                   last_known_id=0, queued_vm_ids=[])
        @filename = nil
        @rtime = rtime
        @etime = etime
        @stime = stime
        @last_known_id = last_known_id
        @queued_vm_ids = queued_vm_ids
        @is_valid = false
        if stime > 0 and etime > 0 and last_known_id > 0
            @is_valid = true
        end
    end

    # String representation of the cache
    def to_s()
        str = "RUN_TIME=#{@rtime}" + "\n" +
              "RUN_STIME=#{@stime}" + "\n" + 
              "RUN_ETIME=#{@etime}" + "\n" + 
              "LAST_KNOWN_ID=#{@last_known_id}"
        if @queued_vm_ids.size() > 0
            str = str + "\n" + "QUEUED_VM_IDS=" + @queued_vm_ids.join(",")
            #str = str + "\n" + "QUEUED_VM_IDS=" + @queued_vm_ids
        end
        return str
    end


    # Store the cache to file
    def store(file)
        if @is_valid
            @filename = file
            cachefile = File.new(file, "w")
            cachefile.puts to_s()
            cachefile.close()
        end
    end


    # Load from file
    def load(file)
        info = {} 
        if File.exists?(file)
            begin 
                #puts "Using cachefile: #{file}"
                cachefile = File.new(file, "r")
                while (line = cachefile.gets())
                    tokens = line.split("=")
                    if tokens.size() > 1
                        field = tokens[0].strip()
                        value = tokens[1, tokens.size()-1].join("=").strip()
                        info[field] = value
                    end
                end
                cachefile.close()
                @filename = file
            rescue => err
                puts "Exception: #{err}"
                err
            end
        else
            puts "Cache file '#{file}' does not exist. Fetching info for all the VMs."
        end

        if info.has_key?("LAST_KNOWN_ID")
            @last_known_id = Integer(info["LAST_KNOWN_ID"])
        end
        
        if info.has_key?("RUN_TIME")
            @rtime = Integer(info["RUN_TIME"])
        end
        
        if info.has_key?("RUN_STIME")
            @stime = Integer(info["RUN_STIME"])
        end
        
        if info.has_key?("RUN_ETIME")
            @etime = Integer(info["RUN_ETIME"])
        end
        
        if info.has_key?("QUEUED_VM_IDS")
            info["QUEUED_VM_IDS"].split(",").each do |q_id|
                @queued_vm_ids << Integer(q_id.strip())
            end
            @queued_vm_ids.sort!
        end

        @is_valid = true
    end

end #OpenNebulaSensorCache


class OpenNebulaSensorCacheManager

    # Class constructor
    def initialize(cachedir="/var/tmp/one-gratia-history")
        @cachedir = cachedir
        @cache_prefix = @cachedir + "/cache."
        @caches = {}
    end
  

    # Find, load and return best available cache based on the etime
    def find(stime)
        # Look for cache file with etime <= stime
        ts = []
        files = Dir.glob(@cache_prefix + "*")
        files.each() do |f|
            tokens = f.split(".")
            if tokens.size() > 1
                # etime for the run is at the end of the filename
                ts << Integer(tokens[tokens.size() - 1])
            end
        end
        # Do a reverse sort
        ts.sort! {|x,y| y <=> x}
    
        # We can be smart here and do O(log(n)) but thats for future
        et = 0
        ts.each() do |t|
            if stime >= t
                # Cache with RUN_ETIME closest to this stime
                et = t
                break
            end
        end

        if not @caches.has_key?(et)
            cache = OpenNebulaSensorCache.new()
            cache.load(@cache_prefix + et.to_s())
            @caches[et] = cache
        end
        return @caches[et]
    end


    # Store the cache to cache file
    def store(cache)
        cache.store(@cache_prefix + cache.etime.to_s())
        @caches[cache.etime] = cache
    end


    # Cleanup cache and only retain cache files upto limit
    def cleanup(limit)
        if (limit > 0)
            files = (Dir.glob(@cache_prefix + "*")).sort()

            to_rm = files.size() - limit
            if (to_rm > 0)
                files_to_rm = files.first(to_rm)
                #PP.pp(files_to_rm)
                files_to_rm.each() do |f|
                    File.delete(f)
                end
            end
        end
    end


end #OpenNebulaSensorCacheManager


class OpenNebulaVirtualMachine

    attr_reader :info

    # States from which VM can never transition to a different state
    COMPLETED_STATES = Set.new("6")

    # OpenNebula will return the information in form of a hash
    # To extract relevant information, just create an entry in the fields_map
    # with the key as the attribute name you want and value as array keys that
    # lead to the info

    FIELDS_MAP = {
        "ID"              => { "field" => ["ID"], "type" => "string" },
        "NAME"            => { "field" => ["NAME"], "type" => "string" },
        "STIME"           => { "field" => ["STIME"], "type" => "string" },
        "ETIME"           => { "field" => ["ETIME"], "type" => "string" },
        "STATE"           => { "field" => ["STATE"], "type" => "string" },
        "LCM_STATE"       => { "field" => ["LCM_STATE"], "type" => "string" },
        "MEMORY"          => { "field" => ["MEMORY"], "type" => "string" },
        "CPU"             => { "field" => ["CPU"], "type" => "string" },
        "VCPU"            => { "field" => ["TEMPLATE","VCPU"],
                               "type" => "string" },
        "MEMORY_REQ(MB)"  => { "field" => ["TEMPLATE","MEMORY"],
                               "type" => "string" },
        "HISTORY_RECORDS" => { "field" => ["HISTORY_RECORDS","HISTORY"],
                               "type" => "array" },
        "HID"             => { "field" => ["HISTORY_RECORDS","HISTORY","HID"],
                               "type" => "array" },
        "HISTORY_STIME"   => { "field" => ["HISTORY_RECORDS","HISTORY","STIME"],
                               "type" => "array" },
        "HISTORY_ETIME"   => { "field" => ["HISTORY_RECORDS","HISTORY","ETIME"],
                               "type" => "array" },
        "HISTORY_REASON"  => { "field" => ["HISTORY_RECORDS","HISTORY","REASON"],
                               "type" => "array" },
        "HOSTNAME"        => { "field" => ["HISTORY_RECORDS","HISTORY","HOSTNAME"],
                               "type" => "array" },
        "MAC"             => { "field" => ["TEMPLATE","NIC","MAC"],
                               "type" => "array" },
        "IP"              => { "field" => ["TEMPLATE","NIC","IP"],
                               "type" => "array" },
        "NETWORK"         => { "field" => ["TEMPLATE","NIC","NETWORK"],
                               "type" => "string" },
        "NETWORK_ID"      => { "field" => ["TEMPLATE","NIC","NETWORK_ID"],
                               "type" => "string" },
        "DISK_ID"         => { "field" => ["TEMPLATE","DISK","DISK_ID"],
                               "type" => "array" },
        "DISK_TYPE"       => { "field" => ["TEMPLATE","DISK","TYPE"],
                               "type" => "array" },
        "DISK_SIZE"       => { "field" => ["TEMPLATE","DISK","SIZE"],
                               "type" => "array" },
        "DISK_IMAGE"      => { "field" => ["TEMPLATE","DISK","IMAGE"],
                               "type" => "array" },
        "DISK_IMAGE_ID"   => { "field" => ["TEMPLATE","DISK","IMAGE_ID"],
                               "type" => "array" },
        "UID"             => { "field" => ["UID"], "type" => "string" },
        "USERNAME"        => { "field" => ["UNAME"], "type" => "string" },
        "GID"             => { "field" => ["GID"], "type" => "string" },
        "GNAME"           => { "field" => ["GNAME"], "type" => "string" },
    }
    #    "VO"              => { "field" => ["TEMPLATE", "VO"], "type" => "string" },

    # Class constructor
    def initialize(info={})
        @info = info
    end

    # Class constructor
    # Get the info from the OpenNebula VirtualMachine class
    def initialize(client, id)
        @info = {}
        vm = VirtualMachine.new_with_id(id, client)
        vm.info()
        vminfo = vm.to_hash()["VM"]
        if vminfo.size() == 1
            return
        end

        FIELDS_MAP.each_key() do |field|
            #puts "EXTRACTING VALUE FOR FEILD:"
            #puts "="*50
            #puts field + " = " + FIELDS_MAP[field]["field"].inspect
            #puts "-"*50
            @info[field] = extract_field_values(vminfo,
                                                FIELDS_MAP[field]["field"])
            #puts "_"*50
            #puts "RESULT:"
            #PP.pp(@info)
            #puts "_"*50
        end
        sanitize_fieldtype()

        # Additional info that cannot be mapped
        @info["STATE_STR"] = vm.state_str()
        @info["LCM_STATE_STR"] = vm.lcm_state_str()

        user_manager = OpenNebulaUserManager.instance()
        @info["DN"] = user_manager.uid2dns(client, @info["UID"])
        #puts @info.inspect()
    end


    def is_completed()
        if (@info.size() > 1) and (@info.has_key?("STATE"))
            return COMPLETED_STATES.include?(@info["STATE"])
        end

        return false
    end

    
    def guessed_etime()
        etime = 0
        if @info.has_key?("HISTORY_ETIME") and @info["HISTORY_ETIME"]
            if (@info["HISTORY_ETIME"]).kind_of?(Array)
                etime = Integer(@info["HISTORY_ETIME"][@info["HISTORY_ETIME"].size()-1])
            else
                etime = Integer(@info["HISTORY_ETIME"])
            end
            if (etime == 0)
                etime = Integer(@info["ETIME"])
            end
        else
            etime = Integer(@info["ETIME"])
        end

        return etime
    end
    

    def guessed_stime()
        stime = 0
        if @info.has_key?("HISTORY_STIME") and @info["HISTORY_STIME"]
            if @info["HISTORY_STIME"].kind_of?(Array)
                stime = Integer(@info["HISTORY_STIME"][0])
            else
                stime = Integer(@info["HISTORY_STIME"])
            end
            if (stime == 0) or (stime > Integer(@info["STIME"]))
                stime = Integer(@info["STIME"])
            end
        else
            stime = Integer(@info["STIME"])
        end

        return stime
    end


    def predates_era(time)
        etime = guessed_etime()
        if time > 0
            #puts @info["ID"] +":"+ Integer(@info["ETIME"]).to_s + "=========>"
            #puts "predates_era: #{@info["ID"]} : #{time} : #{etime} : #{is_completed()}"
            if is_completed() and etime > 0 and etime < time
                # Compare it with the last etime in the history. Thats the only
                # correct means to make sure the vm was not done before
                return true
            end
        end
        return false
    end

    
    def postdates_era(time)
        stime = guessed_stime()
        if time > 0
            # Usually we want to consider @info["STIME"]. When the vm is 
            # resubmitted, the STIME is overwritten by STIME when resubmitted
            # In this case first value in @info["HISTORY_STIME"] is best info
            #puts "postdates_era: #{@info["ID"]} : #{time} : #{stime}"
            if stime > time and stime > 0
                return true
            end
        end
    
        return false
    end

    
    def lived_in_era(stime, etime)
        #if (stime > 0) and (etime > 0) and
        #(Integer(vm["STIME"]) >= stime) and (vm_predates_era(vm, etime))

        # VM launched and shutdown in the interval
        if (stime > 0) and (etime > 0) and
           (not postdates_era(stime)) and (predates_era(etime))
            return true
        end
        return false
    end


    def extract_field_values(info, fields)
        
        #PP.pp(fields)
        #PP.pp(info)
        #puts "-"*50
       
        if info.is_a?(Hash)
            #puts "info IDENTIFIED as a HASH"
            if info.has_key?(fields[0])
                if fields.size() == 1
                    #puts "RETURNING NOW"
                    #PP.pp(info[fields[0]])
                    return info[fields[0]]
                else
                    return extract_field_values(info[fields[0]],
                                                fields.slice(1,fields.size()-1))
                end
            else
                return nil
            end
        elsif info.is_a?(Array) 
            #puts "info IDENTIFIED as a ARRAY"
            ret_arr = []
            info.each() do |i|
                ret_arr.push(extract_field_values(i, fields))
            end
            #puts "RETURNING NOW"
            #PP.pp(ret_arr)
            return ret_arr
        else
            #puts "RETURNING nil"
            return nil
        end
    end


    def sanitize_fieldtype()
        @info.each_key do |key|
            if FIELDS_MAP.has_key?(key)
                if (FIELDS_MAP[key]["type"] == "array") and
                   (not @info[key].is_a?(Array))
                   @info[key] = [@info[key]]
                end
            end
        end
    end


end #OpenNebulaVirtualMachine


class OpenNebulaVirtualMachinePool < VirtualMachinePool

    # WE ONLY DERIVE THIS CLASS TO GET ACCESS TO THE info_filter
    # member thats private in OpenNebula 3.2
    def initialize(client, user_id=-1)
        super(client, user_id)
    end


    def info_filter(xml_method, who, start_id, end_id, state)
        return xmlrpc_info(xml_method, who, start_id, end_id, state)
    end


end #OpenNebulaVirtualMachinePool


class OpenNebulaUserManager
    @@singleton__instance__ = nil
    @@singleton__mutex__ = Mutex.new

    def self.instance
        return @@singleton__instance__ if @@singleton__instance__
        @@singleton__mutex__.synchronize {
            return @@singleton__instance__ if @@singleton__instance__
            @@singleton__instance__ = new()
        }
        @@singleton__instance__
    end


    def uid2dns(client, uid)
        if not @users.has_key?(uid)
            cache_user_info(client, uid)
        end

        if @users.has_key?(uid)
            return @users[uid]["DN"]
        end
        return nil
    end


    def cache_user_info(client, uid)
        u = User.new_with_id(uid, client)
        u.info()
        #puts "-"*50

        info = u.to_hash()["USER"]
        if info.size() == 1
            return
        end
        @users[uid] = {}
        @user_fields.each() do |f|
            @users[uid][f] = info[f]
        end
        if @x509_auth_drivers.include?(@users[uid]["AUTH_DRIVER"])
            @users[uid]["DN"] = info["PASSWORD"].split("|")
        else
            @users[uid]["DN"] = [] 
        end
    end


    private
    def initialize()
        @users = {}
        @uname = {}
        #@client = client
        @user_fields = ["ID", "NAME", "GID", "GNAME", "ENABLED", "AUTH_DRIVER"]
        @x509_auth_drivers = ["x509", "server_x509"]
    end
    private_class_method :new
    

end #OpenNebulaUserManager

##############################################################################
# Custom Functions
##############################################################################

def version()
    return VERSION_STRING
end


def version_string()
    return "query_one_lite.rb #{version()}" + "\n" +
           "License: http://fermitools.fnal.gov"
end


def format_results(vms)
    ovms = {}
    vms.each_key() do |id|
        ovms[id] = vms[id].info
    end
    return ovms.inspect().gsub("=>", ": ").gsub("nil", "None")
end


def output_results(results, file)
    outfile = File.new(file, "w")
    old = $stdout
    $stdout = outfile
    puts results
    outfile.close()
    $stdout = old
end


def get_queued_vm_ids(vms, etime)
    ids = []
    vms.each_key() do |id|
        if (vms[id].guessed_etime() > etime) or (not vms[id].is_completed())
            ids << id
        end
    end
    ids.sort!
    return ids
end


def get_last_vmid(client, id)
    last_vmid = id
    start_vmid = id
    if id > 0
        start_vmid -= 1
    end
    
    line_size = 80
    vm_pool = OpenNebulaVirtualMachinePool.new(client)
    # Get vms in all state starting from start_vmid.
    # This is best way to get the last known vm id
    rc = vm_pool.info_filter(
             OpenNebulaVirtualMachinePool::VM_POOL_METHODS[:info],
             OpenNebulaVirtualMachinePool::INFO_ALL,
             start_vmid,
             -1,
             OpenNebulaVirtualMachinePool::INFO_ALL_VM)

    if OpenNebula.is_error?(rc)
        puts rc.message
        exit -1
    end

    ids = Array.new
    vm_pool.each do |vm|
        ids.push(vm.id)
    end
    ids.sort!
    last_vmid = ids[-1]

    return last_vmid
end


def print_report(options, stime, etime, output, cachein, cacheout, vm_ids)
    line_size = 80
    puts "="*line_size
    puts "                                 REPORT"
    puts "="*line_size
    
    #puts "Options: #{options.inspect()}"
    
    opt_str = "Options:"
    indent = opt_str.size()
    cur_line_size = opt_str.size()
    options.each_key() do |opt|
        if options[opt]
            new_str = "#{opt}=#{options[opt]}"
        else
            new_str = "#{opt}=nil"
        end

        if (cur_line_size + " ".size() + new_str.size()) > 80
            cur_line_size = indent + new_str.size()
            opt_str = opt_str + "\n         " + new_str
        else
            cur_line_size = cur_line_size + new_str.size() + 1
            opt_str = opt_str + " " + new_str
        end
    end
    puts opt_str

    puts "Script Version: #{version()}"
    puts "Ruby Version: #{VERSION}"
    if options[:all]
        puts "Reporting all vms: #{options[:all]}"
    else
        puts "stime: #{stime}"
        puts "etime: #{etime}"
    end
    puts "Output: #{output}"
    puts "Cachefile Used: #{cachein}"
    puts "Cachefile Wrote: #{cacheout}"
    puts "VMs Found: #{vm_ids.size()}"
    puts "VM Ids: #{vm_ids.inspect()}"
    puts "_"*line_size
end

##############################################################################
# Main
##############################################################################

#CREDENTIALS = nil
#ENDPOINT = "http://fermicloud319.fnal.gov:2633/RPC2"
#HASH = true
#client = Client.new(CREDENTIALS, ENDPOINT, HASH)

###############################################################################
# Command line parsing
###############################################################################
options = {}
optparse = OptionParser.new() do |opts|
    opts.banner = "Usage: query_one_lite.rb [options]"

    options[:time] = Time.now().to_i()
    opts.on('-t', '--time TIME', 'Sec since epoch. Defaults to current time') do |t|
        options[:time] = Integer(t)
    end

    options[:delta] = -3600
    opts.on('-d', '--delta DELTA', 'Sec since time. Defaults to -3600') do |d|
        options[:delta] = Integer(d)
    end
    
    options[:all] = false
    opts.on('-a', '--all', 'Query all the vms. Ignore time & delta') do |a|
        options[:all] = true
    end
    
    options[:cachedir] = "/var/tmp/one-gratia-history"
    opts.on('-c', '--cache-dir CACHEDIR', 'Cache dir. Defaults to /var/tmp/one-gratia-history') do |cachedir|
        options[:cachedir] = cachedir
    end
    
    options[:cachelimit] = 1
    opts.on('-l', '--cache-limit CACHELIMIT', 'Number of cached records to keep. Anything older is cleaned up. Defaults to 1') do |cachelimit|
        options[:cachedir] = cachelimit
    end
    
    options[:cachelimitcheck] = true
    opts.on('-x', '--skip-cache-limit-check', 'Do not clean cached records even if they are more than limit') do |cachelimitcheck|
        options[:cachelimitcheck] = false
    end
    
    options[:output] = nil
    opts.on('-o', '--output OUTPUT', 'File to store VM information. Defaults to CACHEDIR/onestats') do |o|
        options[:output] = o
    end
    
    options[:report] = false
    opts.on('-r', '--report', 'Print a summary report') do |a|
        options[:report] = true
    end
    
    opts.on( '-v', '--version', 'Display script version' ) do
        puts version_string()
        exit
    end

    opts.on( '-h', '--help', 'Display help screen' ) do
        puts opts
        exit
    end
end
    
# Parse the command-line. There are two forms of the parse method.
# The 'parse' method simply parses ARGV, while the 'parse!' method parses
# ARGV and removes any options found there, as well as any parameters for
# the options. What's left is the list of files to resize.
optparse.parse!

###############################################################################

stime = etime = nil

if options[:delta] < 0
    stime = options[:time] + options[:delta]
    etime = options[:time]
else
    stime = options[:time]
    etime = options[:time] + options[:delta]
end

# Use the default, i.e. anything that comes from the configs
client = Client.new()


if not File.directory?(options[:cachedir])
    Dir.mkdir(options[:cachedir])
end

outputfile = nil
if options[:output]
    outputfile = options[:output]
else
    outputfile = File.join(options[:cachedir], "onestats")
end

#cachefile = File.join(options[:cachedir], "/cache")

last_run_etime = 0
# Starting id
id = 1
vms = {}

cache_manager = OpenNebulaSensorCacheManager.new(cachedir=options[:cachedir])

cache = nil

if not options[:all] 
    # Check if the cache from last run exists.
    # Cache has list of running VMs since last run and the last known ID
    cache = cache_manager.find(stime)

    if cache.is_valid
        # Get the info for vms that we know were running in last run
        cache.queued_vm_ids.each do |i|
            #puts "Last known ids: #{i}"
            vm = OpenNebulaVirtualMachine.new(client, i)
            if (vm.info.size() > 2) and 
               (not vm.predates_era(stime)) and
               (not vm.postdates_era(etime))
                vms[i] = vm
            end
        end
    
        # Start looking for VMs after the last known id
        id = cache.last_known_id + 1
    else
        puts "Ignoring Cache"
    end
end

# Starting from last known id, get the last vm id from OpenNebula
id_last = get_last_vmid(client, id-1)

#puts id
#puts id_last

# Check for any vms past last known vm id that may have state transitions
# This is required so we consider any vms that may have been launched and
# shutdown since last known run
while id <= id_last
    # Skip Bad VM ID
    #if id == 14524
    #    id += 1
    #    next
    #end

    vm = OpenNebulaVirtualMachine.new(client, id)

    if (vm.info.size() >= 2)
        # This is a valid vm record
        if vm.postdates_era(etime)
            # We are past the etime we care
            break
        end

        if options[:all]
            vms[id] = vm
        else
            # Consider the stime and etime. We only need vms that were running
            # or had a state transition in the interval stime - etime
            if not vm.predates_era(stime)
                vms[id] = vm
            end
        end
    end

    # Skip to next id until we have hit the id_last
    id += 1
end

if vms.size() < 1
    # There is no good way for now to figure out if the opnnebula or db is down
    # Ignore this run, do not delete or create new cache and exit with 
    # non-zero exit code
    puts "E099: Querying OpenNebula returned no records for any VM. Ignoring changes to cache and cache cleanup"
    exit 99
end

output_results(format_results(vms), outputfile)

result_cache = OpenNebulaSensorCache.new(
                   rtime=Time.now().to_i(), stime=stime,
                   etime=etime, last_known_id=(id-1),
                   queued_vm_ids=get_queued_vm_ids(vms, etime))
cache_manager.store(result_cache)

if (options[:cachelimitcheck] and (options[:cachelimit] > 0))
    cache_manager.cleanup(options[:cachelimit])
end

# HACK
#exit 0

###############################################################################
# Print Short Runtime Report to stdout
###############################################################################

cachefile = "None"
if cache and cache.filename
    cachefile = cache.filename
end

if options[:report]
    print_report(options, stime, etime, outputfile, cachefile,
                 result_cache.filename, vms.keys().sort!)
end

exit 0
