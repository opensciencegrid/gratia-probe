#!/usr/bin/python
# script to run some io tests
# very primitive

from __future__ import with_statement
import time
import timeit
import sys

fname = "infile"
if len(sys.argv) > 1:
    if sys.argv[1] == '-h' or sys.argv[1] == '--help':
        print "%s [FNAME]  -  do the tests on FNAME (def: infile)"
        sys.exit(0)
    fname = sys.argv[1]

print "** Tests setup -t: %s" % time.time()
sys.stdout.flush()

#flength = 7
import commands
res = commands.getoutput('wc %s' % fname).split()
flength = int(res[0])
fsize = int(res[2])
tests = "12345678"
ITERATIONS = 10
REPETITIONS = 3

print "** Running tests %s (rep: %s) on file %s (%s)" % (tests, REPETITIONS, fname, flength)
sys.stdout.flush()


def do_time(statement, setup='pass', number=ITERATIONS, repeat=REPETITIONS):
    res = timeit.repeat(statement, setup, repeat=repeat, number=number)
    print "*** Times: %s %s" % (min(res), res)


if "1" in tests:
    print "** Test 1 - list file  -t: %s" % time.time()
    mark_int = int(flength/10)
    position = 0
    f = open(fname)
    pre = f.tell()
    for i, line in enumerate(f):
        # should be returning the position before (pre) or after (f.tell()) the line?
        #print line, i, f.tell()
        if i > position:
            print i, f.tell()
            position += mark_int
        pre = f.tell()
    f.close()
    sys.stdout.flush()


def markers(fname):
    mark20 = int(fsize/10)
    position = 0
    f = open(fname)
    for line in f:
        # m, r = divmod(f.tell(), mark20)
        # if r == 0:  - will rarely happen because of buffer and line size
        r = f.tell()
        if r > position:
            print " mark %s, %s" % (position, r)
            position += mark20
    f.close()

def markers2(f):
    mark20 = int(fsize/10)
    position = 0
    for line in f:
        # m, r = divmod(f.tell(), mark20)
        # if r == 0:  - will rarely happen because of buffer and line size
        r = f.tell()
        if r > position:
            print " mark %s, %s" % (position, r)
            position += mark20
def simplecount(fname):
    lines = 0
    for line in open(fname):
        lines += 1
    return lines

def simplecount2(f):
    lines = 0
    for line in f:
        lines += 1
    return lines

if "5" in tests:
    print "** Test 5 markers/fname (only+ timeit) -t: %s" % time.time()
    markers(fname)
    print "- Markers with timeit: "
    sys.stdout.flush()
    do_time("markers(fname)", setup="from __main__ import markers, fname")
    sys.stdout.flush()

if "6" in tests:
    print "** Test 6 markers2/file (only+ timeit) -t: %s" % time.time()
    f = open(fname)
    markers2(f)
    f.close()
    print "- Markers with timeit: "
    sys.stdout.flush()
    f = open(fname)
    do_time("f = open(fname); markers2(f)", setup="from __main__ import markers2, fname")
    f.close()
    sys.stdout.flush()

if "4" in tests:
    print "** Test 4 file vs name -t: %s" % time.time()
    print "- Open file markers: "
    f = open(fname)
    do_time("f = open(fname); markers2(f)", setup="from __main__ import markers2, fname")
    f.close()
    print "- Fname: "
    do_time("simplecount(fname)", setup="from __main__ import simplecount, fname")
    print "- Open file: "
    f = open(fname)
    do_time("f = open(fname); simplecount2(f)", setup="from __main__ import simplecount2, fname")
    f.close()
    print "- Fname 2: "
    do_time("simplecount(fname)", setup="from __main__ import simplecount, fname")
    print "- Open file: 2"
    f = open(fname)
    do_time("f = open(fname); simplecount2(f)", setup="from __main__ import simplecount2, fname")
    f.close()
    sys.stdout.flush()


def run_through(f):
    for line in f:
        pass


def run_through_tell(f):
    for line in f:
        f.tell()


def run_through_enum_tell(f):
    for i, line in enumerate(f):
        f.tell()


def run_through_ctr_tell(f):
    ctr = 0
    for line in f:
        f.tell()
        ctr += 1


if "2" in tests:
    print "** Test 2 timing -t: %s" % time.time()
    for i in ['run_through', 'run_through_tell', 'run_through_enum_tell', 'run_through_ctr_tell']:
        cmd = "%s(f)" % i
        print "Testing %s: " % cmd
        f = open(fname)
        print timeit.timeit(cmd, setup="from __main__ import %s, f" % i, number=REPETITIONS)
        f.close()
    sys.stdout.flush()



import time
import mmap
from collections import defaultdict

def mapcount(filename):
    f = open(filename, "r+")
    buf = mmap.mmap(f.fileno(), 0)
    lines = 0
    readline = buf.readline
    while readline():
        lines += 1
    return lines

def simplecount(filename):
    lines = 0
    for line in open(filename):
        lines += 1
    return lines

def bufcount(filename):
    f = open(filename)
    lines = 0
    buf_size = 1024 * 1024
    read_f = f.read  # loop optimization

    buf = read_f(buf_size)
    while buf:
        lines += buf.count('\n')
        buf = read_f(buf_size)

    return lines

def opcount(fname):
    with open(fname) as f:
        for i, l in enumerate(f):
            pass
    return i + 1


if "3" in tests:
    print "** Test 3 functions: -t: %s" % time.time()
    counts = defaultdict(list)

    for i in range(5):
        for func in [mapcount, simplecount, bufcount, opcount]:
            start_time = time.time()
            assert func(fname) == flength
            counts[func].append(time.time() - start_time)

    for key, vals in counts.items():
        print key.__name__, ":", sum(vals) / float(len(vals))

    sys.stdout.flush()

print "** End of all tests -t: %s" % time.time()