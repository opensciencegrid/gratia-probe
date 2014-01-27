#!/bin/sh
#set -x
export PATH=$PATH:/usr/bin:/usr/local/bin/

_gratia_dir=/usr/share/gratia
_gratia_data_dir=/var/lib/gratia/data
_currentfile=${_gratia_data_dir}/query_one.log

#version
_version=`/sbin/runuser - oneadmin -c "onevm --version|grep ^OpenNebula|cut -d' ' -f2"`
if [ x${_version} = "x" ]
then
	_version=3.2
fi
_version=`echo ${_version%.*}`
options=""
exitCode=1
if [ `echo ${_version:0:1}` -ge 3 ]
then
        #check if chkpt_vm_DoNotDelete exists
        if [ ! -f ${_gratia_data_dir}/chkpt_vm_DoNotDelete ]
        then
                #we will start from the beginig
                options="-a"
        else
                ct=`date +%s`
                let delta=${ct}-`cut -d'.' -f 1 /var/lib/gratia/data/chkpt_vm_DoNotDelete`
                options="-t ${ct} -d -${delta}"
        fi
	if [ ${_version} = "3.2" ]
	then
		export ONE_LOCATION=/cloud/app/one/3.2/
		export PATH=$ONE_LOCATION/bin:$PATH
		/sbin/runuser - oneadmin -c "export ONE_AUTH=/var/lib/one/.one/one_x509; ${_gratia_dir}/onevm/query_one_lite.rb ${options} -c ${_gratia_data_dir} -o ${_currentfile}"
		exitCode=$?
	elif [ ${_version} = "4.4" ]
	then
		export ONE_LOCATION=/fcon-4.4
		export PATH=$PATH:$ONE_LOCATION/bin
        	/sbin/runuser - oneadmin -c "oneuser login oneadmin --x509 --cert /etc/grid-security/hostcert.pem --key /etc/grid-security/hostkey.pem 1>/dev/null;export ONE_AUTH=/var/lib/one/.one/one_x509; ${_gratia_dir}/onevm/query_one_lite.rb ${options} -c ${_gratia_data_dir} -o ${_currentfile} "
		exitCode=$?
	else
		echo "oops, don't know how to handle version: ${_version}"
	fi
fi
if  [ ${exitCode} -ne 0 ]
then
	echo "Failure to get information from ONE, exiting"
        exit 1
fi
${_gratia_dir}/onevm/VMGratiaProbe   -f ${_currentfile} -V ${_version} 
exit $?
