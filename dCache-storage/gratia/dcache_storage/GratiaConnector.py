#!/usr/bin/python

from __future__ import print_function

import os
import re
import sys
import time
import socket
import datetime
import optparse
import xml.sax.saxutils

has_gratia = True
try:
    import gratia.common.Gratia as Gratia
    from gratia.services.StorageElement import StorageElement
    from gratia.services.StorageElementRecord import StorageElementRecord

except:
    has_gratia = False
    Gratia = None
    StorageElement = None
    StorageElementRecord = None

class GratiaConnector:
    
  def __init__(self,cp):
    global has_gratia
    global Gratia
    global StorageElement
    global StorageElementRecord
    if not has_gratia:
        try:
            Gratia = __import__("Gratia")
            StorageElement = __import__("StorageElement")
            StorageElementRecord = __import__("StorageElementRecord")
            has_gratia = True
        except:
            raise
    if not has_gratia:
        print("Unable to import Gratia and Storage modules!")
        sys.exit(1)

    Gratia.Initialize()
    try:
        if Gratia.Config.get_SiteName().lower().find('generic') >= 0:
            Gratia.Config.setSiteName(socket.getfqdn())
    except:
        pass
    try:
        if Gratia.Config.get_ProbeName().lower().find('generic') >= 0:
            Gratia.Config.setProbeName('dCache-storage:%s' % socket.getfqdn())
    except:
        pass

  def send(self,record):
        Gratia.Send(record)

