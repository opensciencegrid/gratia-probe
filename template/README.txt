This is a template for a new probe
These are suggestions to structure the files and make future modifications and the packaging easier

Components that will be or are used in the distribution package:
  template - (python) executable of the probe. Will send records to the collector
  gratia-probe-template.cron - cron file used to run the probe
* gratia/ (probably /gratia/template/) - auxiliary files, modules for the probe
* ProbeConfig.add - (if there are any) probe-specific lines to add to the probe configuration (for package building)

Components that will not be in the distribution:
  README* (README/README.txt/README.html/README.md) - this file, describes the probe. May be included in the comments or docstring of the probe executable
* dev/ - auxiliary files used/useful for development (e.g. libraries used and then included as dependency or included in the probe auxiliary files)
* test/ - test configuration, test files

* are optional files, directories, present only if needed

NOTES
- python module and package names should be all lowercase and include at most underscores (specially discouraged for package names)
  (PEP8).
  script names can contain dashes if you want to discourage import (regular import command fails on names with dashes)
- python packages must include a __init__.py file (e.g.  /gratia/template/__init__.py)
- build/gratia-probe.spec contains the packages specifications (anyway mention dependencies in README)

