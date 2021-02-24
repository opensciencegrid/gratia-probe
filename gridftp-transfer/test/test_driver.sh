#!/bin/sh -xe

rm -rf testing/
mkdir -p testing/{tmp,data,log}
mkdir -p testing/data/quarantine


sed -e "s|@PWD@|$PWD|" -e "s|@TESTFILE@|simple-xfer.log|" ProbeConfigTemplate > ProbeConfig
../gratia-probe-gridftp -f ProbeConfig

sed -e "s|@PWD@|$PWD|" -e "s|@TESTFILE@|simple-split-xfer.log|" ProbeConfigTemplate > ProbeConfig
../gratia-probe-gridftp -f ProbeConfig

echo "******************************************************************************"

../gratia-probe-gridftp -f ProbeConfig

