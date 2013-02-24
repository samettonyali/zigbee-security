#!/usr/bin/env python

# ZBWarDrive
# rmspeers 2010-13
# ZigBee/802.15.4 WarDriving Platform

import sys
import argparse
from time import sleep
from multiprocessing import Process, Manager
from usb import USBError

from killerbee import KillerBee, kbutils
from db import ZBScanDB
from scanning import doScan

# GPS Poller
def gpsdPoller(currentGPS):
    '''
    @type currentGPS multiprocessing.Manager dict manager
    @arg currentGPS store relavent pieces of up-to-date GPS info
    '''
    import gps
    gpsd = gps.gps()
    gpsd.poll()
    gpsd.stream()

    try:
        while True:
            gpsd.poll()
            if gpsd.fix.mode > 0:
                lat = gpsd.fix.latitude
                lng = gpsd.fix.longitude
                alt = gpsd.fix.altitude
                print 'latitude    ' , lat
                print 'longitude   ' , lng
                print 'time utc    ' , gpsd.utc,' + ', gpsd.fix.time
                print 'altitude (m)' , alt
                currentGPS['lat'] = lat
                currentGPS['lng'] = lng
                currentGPS['alt'] = alt
            else:
                print "Waiting for a GPS fix."
                #TODO timeout lat/lng/alt values if too old...?
            sleep(3)
    except KeyboardInterrupt:
        print "Got KeyboardInterrupt in gpsdPoller, returning."
        return

# startScan
# Detects attached interfaces
# Initiates scanning using doScan()
def startScan(zbdb, arg_verbose, dblog=False, agressive=False):
    try:
        kb = KillerBee()
    except usb.USBError, e:
        if e.args[0].find('Operation not permitted') >= 0:
            print 'Error: Permissions error, try running using sudo.'
        else:
            print 'Error: USBError:', e
        return False
    except Exception, e:
        #print 'Error: Missing KillerBee USB hardware:', e
        print 'Error: Issue starting KillerBee instance:', e
        return False
    for kbdev in kbutils.devlist():
        print 'Found device at %s: \'%s\'' % (kbdev[0], kbdev[1])
        zbdb.store_devices(
            kbdev[0], #devid
            kbdev[1], #devstr
            kbdev[2]) #devserial
    kb.close()
    doScan(zbdb, arg_verbose, dblog=dblog, agressive=agressive)
    return True

# Command line main function
if __name__=='__main__':
    # Command line parsing
    parser = argparse.ArgumentParser(description="""
Use any attached KillerBee-supported capture devices to preform a wardrive,
by using a single device to iterate through channels and send beacon requests
while other devices are assigned to capture all packets on a channel after
it is selected as 'of interest' which can change based on the -a flag.
""")
    parser.add_argument('-v', '--verbose', dest='verbose', action='store_true',
                        help='Produce more output, for debugging')
    parser.add_argument('-d', '--db', dest='dblog', action='store_true',
                        help='Enable KillerBee\'s log-to-database functionality')
    parser.add_argument('-a', '--agressive', dest='agressive', action='store_true',
                        help='Initiate capture on channels where packets were seen, even if no beacon response was received')
    parser.add_argument('-g', '--gps', dest='gps', action='store_true',
                        help='Connect to gpsd and grab location data as available to enhance PCAPs')
    args = parser.parse_args()

    # try-except block to catch keyboard interrupt.
    zbdb = None
    gpsp = None
    manager = Manager()
    devices = manager.dict()
    currentGPS = manager.dict()
    try:
        if args.gps:
            gpsp = Process(target=gpsdPoller, args=(currentGPS, ))
            gpsp.start()
        zbdb = ZBScanDB()
        #TODO check return value from startScan
        startScan(zbdb, args.verbose, dblog=args.dblog, agressive=args.agressive)
        zbdb.close()
    except KeyboardInterrupt:
        print 'Shutting down'
        if zbdb != None: zbdb.close()
        if gpsp != None: gpsp.terminate()


