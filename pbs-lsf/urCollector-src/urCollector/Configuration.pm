package urCollector::Configuration;

####################################
# Packages
####################################
use strict;
use urCollector::Common;

require Exporter;

####################################
# Global variables used internally
####################################
use vars qw(@EXPORT @ISA @EXPORT_OK
	    $configFilePath
	    %configValues);

####################################
# Symbol export
####################################
@ISA = qw(Exporter);
@EXPORT = qw($configFilePath %configValues &parseConf);

####################################
# Initialization / executable code
####################################
$configFilePath = "/usr/share/gratia/pbs-lsf/urCollector.conf";

%configValues =
(
 lrmsType              => "",
 pbsAcctLogDir         => "",
 lsfAcctLogDir         => "",
 ceJobMapLog           => "yes",
 writeGGFUR            => "no",

 keyList               => "GlueHostBenchmarkSF00,GlueHostBenchmarkSI00",
 ldifDefaultFiles      => "",
 glueLdifFile          => "",
 siteName              => "",	### read from glueLdifFile instead???

 URBox    =>  "/var/lib/gratia/tmp/urCollector",

 collectorLockFileName => "/var/lock/urCollector.lock",
 collectorBufferFileName => "/var/lib/gratia/tmp/urCollectorBuffer",
 mainPollInterval  => "5",
 timeInterval      =>"5",
 jobPerTimeInterval =>"10",
 lsfBinDir            => "/usr/bin/",
);

####################################
# End of initialization / executable code
####################################
1;

####################################
# Subroutines
####################################
sub parseConf {
    my $fconf = $_[0];
    open(FILE, "$fconf") || &error("Error: Cannot open configuration file $fconf\n");
    while(<FILE>) {
	if(/^lrmsType\s*=\s*\"(.*)\"$/){$configValues{lrmsType}=$1;}
	if(/^pbsAcctLogDir\s*=\s*\"(.*)\"$/){$configValues{pbsAcctLogDir}=$1;}
	if(/^lsfAcctLogDir\s*=\s*\"(.*)\"$/){$configValues{lsfAcctLogDir}=$1;}
	if(/^ceJobMapLog\s*=\s*\"(.*)\"$/){$configValues{ceJobMapLog}=$1;}
	if(/^useCEJobMap\s*=\s*\"(.*)\"$/){$configValues{useCEJobMap}=$1;}
	if(/^writeGGFUR\s*=\s*\"(.*)\"$/){$configValues{writeGGFUR}=$1;}

	if(/^keyList\s*=\s*\"(.*)\"$/){$configValues{keyList}=$1;}
	if(/^ldifDefaultFiles\s*=\s*\"(.*)\"$/){$configValues{ldifDefaultFiles}=$1;}
	if(/^glueLdifFile\s*=\s*\"(.*)\"$/){$configValues{glueLdifFile}=$1;}
	if(/^siteName\s*=\s*\"(.*)\"$/){$configValues{siteName}=$1;}

	if(/^URBox\s*=\s*\"(.*)\"$/){$configValues{URBox}=$1;}

	if(/^collectorLockFileName\s*=\s*\"(.*)\"$/){$configValues{collectorLockFileName}=$1;}
	if(/^collectorBufferFileName\s*=\s*\"(.*)\"$/){$configValues{collectorBufferFileName}=$1;}
	if(/^mainPollInterval\s*=\s*\"(.*)\"$/){$configValues{mainPollInterval}=$1;}
	if(/^timeInterval\s*=\s*\"(.*)\"$/){$configValues{timeInterval}=$1;}
	if(/^jobPerTimeInterval\s*=\s*\"(.*)\"$/){$configValues{jobPerTimeInterval}=$1;}
    if(/^lsfBinDir\s*=\s*\"(.*)\"$/){$configValues{lsfBinDir}=$1;}
    }
    close(FILE);
}



####################################
# Only POD beyond here.
####################################
__END__
