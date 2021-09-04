#!/usr/bin/env python3

# add/merge ProbeConfig.add into ProbeConfig's @PROBE_SPECIFIC_DATA@
# updating any existing attributes

import sys
import os
import re


def read_if_exists(path):
    try:
        return open(path).read()
    except IOError:
        return ''


def filter_nonlast_lines(lines):
    haveattrs = set()
    for line in lines:
        m = re.match(r'^ *(\w+)=', line)
        if m:
            attr = m.group(1)
            if attr in haveattrs:
                continue
            haveattrs.add(attr)
        yield line


def main(pc, pc_add, pc_out=None):
    add_txt = read_if_exists(pc_add)
    pc_txt = open(pc).read().replace('@PROBE_SPECIFIC_DATA@', add_txt)

    lines = reversed(pc_txt.splitlines())
    lines = list(filter_nonlast_lines(lines))
    with open(pc_out or pc, "w") as outf:
        print('\n'.join(reversed(lines)), file=outf)


def usage():
    script = os.path.basename(__file__)
    print(f"usage: {script} ProbeConfig ProbeConfig.add [ProbeConfig.out]",
          file=sys.stderr)
    sys.exit(1)


if __name__ == '__main__':
    try:
        main(*sys.argv[1:])
    except TypeError:
        usage()

