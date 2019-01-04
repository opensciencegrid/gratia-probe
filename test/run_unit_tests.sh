#!/bin/bash -xe

set +e
python -m unittest discover --help
discover_available=$?
set -e

if [ $discover_available -eq 0 ]; then
    # call tests directly
    python -m unittest discover test
else
    python test/test_condor_meter.py
fi
