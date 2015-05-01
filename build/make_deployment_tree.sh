#!/bin/bash
# Make symlinks for a deployment tree. Useful for pythonpath and doc generation
# Before running sphinx all modules must be in the path

# $HOME/prog/repos/gratia/gratia-svn-trunk/gratia-probes/probes:$HOME/prog/repos/gratia/gratia-svn-trunk/gratia-probes/:
# /System/Library/Frameworks/Python.framework/Versions/2.7/Extras/lib/python

# was: export PYTHONPATH="$TREE_ROOT/$TREE_DIR/probes:$TREE_ROOT/$TREE_DIR:$TREE_ROOT/stubs"

# To run sphinx:
#  export PYTHONPATH="$TREE_ROOT/$TREE_DIR:$TREE_ROOT/stubs" 
#  sphinx-apidoc -f -l -F -H gratia-probes -V 1.14.2 -o sphinx/ $TREE_ROOT/$TREE_DIR
#  cd sphinx; make html

SRC_DIR="$HOME/prog/repos/gratia/gratia-svn-trunk"
TREE_ROOT="$HOME/prog/repos/gratia"
TREE_DIR="gratia-probes"

mkdir -p "$TREE_ROOT"
cd "$TREE_ROOT"

# make stubs directory for sphinx imports
if [ ! -d stubs ]; then
  mkdir stubs
  mkdir stubs/OpenSSL
  mkdir stubs/MySQLdb
  mkdir stubs/psycopg2
  touch stubs/MySQLdb.py
  touch stubs/psycopg2.py
  touch stubs/OpenSSL/__init__.py
  touch stubs/OpenSSL/crypto.py
  touch stubs/MySQLdb/__init__.py
  touch stubs/MySQLdb/cursors.py
  touch stubs/psycopg2/__init__.py
  touch stubs/psycopg2/extras.py
fi

mkdir "$TREE_DIR"
cd "$TREE_DIR"
mkdir gratia
touch gratia/__init__.py
#mkdir probes
#touch probes/__init__.py
for i in "$SRC_DIR/probe"/* 
do 
  if [ -d "$i/gratia/`basename $i`" ]; then  
    ln -s "$i/gratia/`basename $i`" gratia/"`basename $i`" 
  #else 
  #  echo "NO $i/gratia/`basename $i`" 
  fi;
  for j in "$i"/*
  do
    if [ -f "$j" ]; then
      head -n 1 "$j" | grep -q python
      if [ $? -eq 0 ]; then
        # valid module name used by sphinx 
        newname="`basename ${j%.py} | tr "-" "_"`.py"
        #ln -s "$j" probes/"`basename ${j%.py}`.py"
        #ln -s "$j" probes/"`basename $j`"
        ln -s "$j" "$newname"
      fi
    fi
  done
done
