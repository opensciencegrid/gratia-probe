#!/usr/bin/perl -w
########################################################################
# pbs-lsf_meter.pl
#
# Read the urCollector configuration file for URBox, then invoke the
# "real" probe in the original Klin^H^H^H^HPython.
#
# Chris Green 2006/10/06
#
# (C) 2006 Fermilab. Released under GPL v2.
########################################################################

####################################
# Packages
####################################
use strict;
use POSIX;

use urCollector::Common qw(:DEFAULT);
use urCollector::Configuration;

sub local_error {
  system("/usr/share/gratia/common/DebugPrint", "-l", "-1", @_);
}

####################################
# BEGIN clause
####################################

####################################
# Initialization / executable code
####################################

# Config file path if specified
if ($ARGV[0]) {
  $configFilePath = shift @ARGV;
}

# Parse configuration file
&parseConf($configFilePath);

my $sigset = POSIX::SigSet ->new();
my $cleanup_action =
  POSIX::SigAction->new("cleanup", $sigset);

POSIX::sigaction(&POSIX::SIGINT, $cleanup_action);
POSIX::sigaction(&POSIX::SIGQUIT, $cleanup_action);
POSIX::sigaction(&POSIX::SIGTERM, $cleanup_action);

my $lrms = uc $configValues{lrmsType};
my $lsfBinDir = $configValues{lsfBinDir};

my $lrms_version;
if ($lrms eq "PBS") {
  ($lrms_version) = grep /\bpbs_version\b/, `qmgr -c "print server" 2>/dev/null`;
  if ($lrms_version) {
    $lrms_version =~ s&^.*=\s*(.*)\n$&$1&;
  }
} elsif ($lrms eq "LSF") {
  my $bsub = $lsfBinDir."/bsub";
  $lrms_version = `$bsub -V 2>&1 1>/dev/null`;
  if ($lrms_version) {
    $lrms_version =~ m&^Platform\s*([^\n]*)(?:.*binary type\s*:\s*(.*))?&s and
      $lrms_version = $2?"$1 / $2":"$1";
  }
}

my $status;
if ($lrms_version) {
  $status = system("/usr/share/gratia/pbs-lsf/pbs-lsf",
                   "$configValues{URBox}",
                   $lrms,
                   $lrms_version);
} else {
  $status = system("/usr/share/gratia/pbs-lsf/pbs-lsf",
                   "$configValues{URBox}",
                   $lrms);
}

exit($status);
####################################
# End of initialization / executable code
####################################
1;


####################################
# Subroutines
####################################
sub cleanup {
}

__END__
