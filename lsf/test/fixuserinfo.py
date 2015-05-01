#!/usr/bin/python
__author__ = 'marcom'

USERVO_FILE = '../user-vo-map.txt'
DEST_DIR = '../dst'
usermap = {}


def load_uvomap(fname):
    global usermap
    for line in open(fname, 'r').readlines():
        if line[0] == '#':
            continue
        try:
            tok = line.split()
            usermap[tok[0].strip()] = tok[1].strip()
        except:
            pass

import os
import sys
import glob
import re

print "Adding user info from: %s" % USERVO_FILE
print "To files in: %s" % sys.argv[1]
print "Saving to: %s" % DEST_DIR
load_uvomap(USERVO_FILE)

ID_STRING = """<UserIdentity>
        <LocalUserId>%(lid)s</LocalUserId>
        <VOName>%(voname)s</VOName>
        <ReportableVOName>%(voname)s</ReportableVOName>
</UserIdentity>"""

ID_STRING1 = """<UserIdentity>
        <LocalUserId>%(lid)s</LocalUserId>
        <DN>/DC=com/DC=DigiCert-Grid/O=Open Science Grid/OU=People/CN=John Weigand 144</DN>
        <VOName>$(voname)s</VOName>
        <ReportableVOName>$(voname)s</ReportableVOName>
</UserIdentity>
"""

USER_START = re.compile(".*<UserIdentity>.*")
USER_EXTRACT = re.compile(".*<LocalUserId>([^<]*)</LocalUserId>.*")
USER_END = re.compile(".*</UserIdentity>.*")
filelist = glob.iglob("%s/*" % sys.argv[1])
for i in filelist:
    print "Working on %s" % i
    inlines = open(i, 'r').readlines()
    before = True
    ctr = 0
    while ctr < len(inlines):
        if USER_START.match(inlines[ctr]):
            break
        ctr += 1
    outlines = inlines[0:ctr]
    if ctr < len(inlines):
        # found start
        ctr += 1
        while ctr < len(inlines):
            line = inlines[ctr]
            if USER_END.match(line):
                found_end = ctr
                break
            m = USER_EXTRACT.match(line)
            if m:
                lid = m.group(1)
                try:
                    voname = usermap[lid]
                except KeyError:
                    print "** User not found %s" % lid
                    raise
                outlines += ["%s\n" % j for j in (ID_STRING % ({'lid': lid, 'voname': voname})).split('\n')]
            ctr += 1
    if ctr < len(inlines):
        outlines += inlines[ctr+1:len(inlines)]
    # " Writing to %s" % i
    of = open("%s/%s" % (DEST_DIR, os.path.basename(i)), 'w')
    of.writelines(outlines)






