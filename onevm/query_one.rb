#!/usr/bin/env ruby
 
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
require 'OpenNebula'
require 'OpenNebula/Pool'
 
include OpenNebula
 
##############################################################################
# Classes
##############################################################################

##############################################################################
# Custom Functions
##############################################################################

def extract_field_values(info, fields)
    
    #pp fields
    #pp info
    #puts "============"
    # info can be array or hash
    if info.is_a?(Hash)
        if info.has_key?(fields[0])
            if fields.size() == 1
                return info[fields[0]]
            else
                return extract_field_values(info[fields[0]],
                                            fields.slice(1, fields.size()-1))
            end
        else
            return nil
        end
    elsif info.is_a?(Array) 
        ret_arr = []
        info.each() do |i|
            ret_arr.push(extract_field_values(i, fields))
        end
        return ret_arr
    else
        return nil
    end
end

##############################################################################
# Main
##############################################################################

#CREDENTIALS = nil
#ENDPOINT = "http://fermicloud319.fnal.gov:2633/RPC2"
#HASH = true
#client = Client.new(CREDENTIALS, ENDPOINT, HASH)

options = {}
optparse = OptionParser.new() do |opts|
    opts.banner = "Usage: blah blah blah ..."

    options[:time] = Time.now().to_i()
    opts.on('-t', '--time TIME', 'Sec since epoch') do |time|
        options[:time] = time
    end

    options[:delta] = -3600
    opts.on('-d', '--delta DELTA', 'Sec since time. Negetive means go back in history. Defaults to -3600') do |d|
        options[:delta] = d
    end
    
    opts.on( '-h', '--help', 'Display help screen' ) do
        puts opts
        exit
    end
end
    
stime = etime = nil

if options[:delta] < 0
    stime = options[:time] + options[:delta]
    etime = options[:time]
else
    stime = options[:time]
    etime = options[:time] + options[:delta]
end

# Parse the command-line. There are two forms of the parse method.
# The 'parse' method simply parses ARGV, while the 'parse!' method parses
# ARGV and removes any options found there, as well as any parameters for
# the options. What's left is the list of files to resize.
optparse.parse!

#exit
# Use the default, i.e. anything that comes from the configs
client = Client.new()
 
vm_pool = VirtualMachinePool.new(client, -1)

=begin
# Added following vm_pool.info_dump
        def info_dump()
            return info_filter(VM_POOL_METHODS[:info],
                               INFO_ALL,
                               -1,
                               -1,
                               INFO_ALL)
        end

=end

# Query all the VMS
#rc = vm_pool.info_all()
#rc = vm_pool.info_dump()

#rc = vm_pool.info(user_id, -1, -1, state_id)

# Current VMS
rc = vm_pool.info(-2, -1, -1, -1)

# All VMS
#rc = vm_pool.info(-2, -1, -1, -2)

if OpenNebula.is_error?(rc)
    puts rc.message
    exit -1
end

# OpenNebula will return the information in form of a hash
# To extract relevant information, just create an entry in the fields_map
# with the key as the attribute name you want and value as array keys that
# lead to the info

fields_map = {
    "ID"              => ["ID"],
    "NAME"            => ["NAME"],
    "STIME"           => ["STIME"],
    "ETIME"           => ["ETIME"],
    "STATE"           => ["STATE"],
    "LCM_STATE"       => ["LCM_STATE"],
    "MEMORY"          => ["MEMORY"],
    "CPU"             => ["CPU"],
    "VCPU"            => ["TEMPLATE", "VCPU"],
    "MEMORY_REQ(MB)"  => ["TEMPLATE", "MEMORY"],
    "HID"             => ["HISTORY_RECORDS", "HISTORY", "HID"],
    "HISTORY_STIME"   => ["HISTORY_RECORDS", "HISTORY", "STIME"],
    "HISTORY_ETIME"   => ["HISTORY_RECORDS", "HISTORY", "ETIME"],
    "HISTORY_REASON"  => ["HISTORY_RECORDS", "HISTORY", "REASON"],
    "HOSTNAME"        => ["HISTORY_RECORDS", "HISTORY", "HOSTNAME"],
    "MAC"             => ["TEMPLATE", "NIC", "MAC"],
    "IP"              => ["TEMPLATE", "NIC", "IP"],
    "NETWORK"         => ["TEMPLATE", "NIC", "NETWORK"],
    "NETWORK_ID"      => ["TEMPLATE", "NIC", "NETWORK_ID"],
    "DISK_ID"         => ["TEMPLATE", "DISK", "DISK_ID"],
    "DISK_TYPE"       => ["TEMPLATE", "DISK", "TYPE"],
    "DISK_SIZE"       => ["TEMPLATE", "DISK", "SIZE"],
    "DISK_IMAGE"      => ["TEMPLATE", "DISK", "IMAGE"],
    "DISK_IMAGE_ID"   => ["TEMPLATE", "DISK", "IMAGE_ID"],
    "UID"             => ["UID"],
    "USERNAME"        => ["UNAME"],
    "GID"             => ["GID"],
    "GNAME"           => ["GNAME"],
}

vms = {}


vm_pool.each do |vm|
    rc = vm.info()
    if OpenNebula.is_error?(rc)
        puts "Virtual Machine #{vm.id}: #{rc.message}"
    else
        vm_info = vm.to_hash()["VM"]
        vm_id = vm_info["ID"]
        vms[vm_id] = {}

        fields_map.each_key() do |field|
            vms[vm_id][field] = extract_field_values(vm_info, fields_map[field])
        end
        # Additional info that cannot be mapped
        vms[vm_id]["STATE_STR"] = vm.state_str()
        vms[vm_id]["LCM_STATE_STR"] = vm.lcm_state_str()
    end
end
 
#out = vms.inspect()
puts vms.inspect().gsub("=>", ": ").gsub("nil", "None")
exit 0
