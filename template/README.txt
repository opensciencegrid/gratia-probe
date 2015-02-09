This is a template for a new probe

Components that will be or are used in the distribution package:
  template - (python) executable of the probe
  gratia-probe-template.cron - cron file used to run the probe
* gratia/template/ - auxiliary files, modules for the probe
* ProbeConfig.add - (if there) probe-specific lines to add to the probe configuration (for package building)

Components that will not be in the distribution:
  README.txt/README.html - this file, describes the probe. May be included in the comments or docstring of the probe executable
* dev/ - auxiliary files useful for development (e.g. libraries used)  
* test/ - test configuration, test files

* are optional files, directories, present only if needed
