#!/usr/bin/env python

# ZBWarDrive
# rmspeers 2010-11
# ZigBee/802.15.4 WarDriving Platform

import sys
import string
import socket
import struct
import bitstring
import subprocess

from killerbee import *
from db import *
from scanning import doScan
from capture import *

# startScan
# Detects attached interfaces
# Initiates scanning using doScan()
def startScan(zbdb, arg_verbose, arg_dblog):
    try:
        kb = KillerBee()
    except usb.USBError, e:
        if e.args[0].find('Operation not permitted') >= 0:
            print 'Error: Permissions error, try running using sudo.'
        else:
            print 'Error: USBError:', e
        sys.exit(1)
    except Exception, e:
        #print 'Error: Missing KillerBee USB hardware:', e
        print 'Error: Issue starting KillerBee instance:', e
        sys.exit(1)
    kbdev_info = kbutils.devlist()
    kb.close()
    for i in range(0, len(kbdev_info)):
        print 'Found device at %s: \'%s\'' % (kbdev_info[i][0], kbdev_info[i][1])
        zbdb.store_devices(
            kbdev_info[i][0], #devid
            kbdev_info[i][1], #devstr
            kbdev_info[i][2]) #devserial
    doScan(zbdb, arg_verbose, arg_dblog)
    return 0

# Command line main function
if __name__=='__main__':
    arg_verbose = False     #if True, give more verbosity
    arg_dblog   = False     #if True, try to log using KillerBee DBLogger
    # parse command line options
    while len(sys.argv) > 1:
        op = sys.argv.pop(1)
        if op == '-v':
            arg_verbose = True
        if op == '-d':
            arg_dblog = True  #attempt to log with KillerBee's dblog ability, to a MySQL db

    # try-except block to catch keyboard interrupt.
    zbdb = None
    try:
        zbdb = ZBScanDB()
        startScan(zbdb, arg_verbose, arg_dblog)
        zbdb.close()
    except KeyboardInterrupt:
        print 'Shutting down'
        if zbdb != None: zbdb.close()
