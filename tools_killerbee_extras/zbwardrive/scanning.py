#!/usr/bin/env python

import sys
import string
import socket
import struct
import bitstring

from killerbee import *
from db import toHex
from capture import startCapture
from scapy.all import Dot15d4, Dot15d4Beacon

# doScan_processResponse
def doScan_processResponse(packet, channel, zbdb, kbscan, verbose):
    scapyd = Dot15d4(packet['bytes'])
    # Check if this is a beacon frame
    if isinstance(scapyd.payload, Dot15d4Beacon):
        if verbose: print "Received frame is a beacon."
        spanid = scapyd.gethumanval('src_panid')
        source = scapyd.gethumanval('src_addr')
        #(src_addr_f, src_addr_v) = scapyd.getfield_and_val('src_addr')
        #source = src_addr_f.i2repr(scapyd, src_addr_v)[2:]
        key = ''.join([spanid, source])
        #TODO if channel already being logged, ignore it as something new to capture
        if zbdb.channel_status_logging(channel) == False:
            if verbose:
                print "A network on a channel not currently being logged replied to our beacon request."
                #print hexdump(packet['bytes'])
                #print scapyd.show()
            # Store the network in local database so we treat it as already discovered by this program:
            zbdb.store_networks(key, spanid, source, channel, packet['bytes'])
            # If possible, log the new network to the remote packet database:
            kbscan.dblog.add_packet(full=packet, scapy=scapyd)
            return key
        else: #network designated by key is already being logged
            if verbose: print 'Received frame is a beacon for a network we already found and are logging.'
    else: #frame doesn't look like a beacon according to scapy
        #if verbose: print 'Received frame is not a beacon.', toHex(packet['bytes'])
        return None
# --- end of doScan_processResponse ---

# doScan
def doScan(zbdb, verbose):
    # Choose a device for injection scanning:
    scannerDevId = zbdb.get_devices_nextFree()
    kbscan = KillerBee(device=scannerDevId, datasource="Wardrive Live")
    #  we want one that can do injection
    inspectedDevs = []
    while (kbscan.check_capability(KBCapabilities.INJECT) == False):
        zbdb.update_devices_status(scannerDevId, 'Ignore')
        inspectedDevs.append(scannerDevId)
        kbscan.close()
        scannerDevId = zbdb.get_devices_nextFree()
        if scannerDevId == None: raise Exception("Error: No free devices capable of injection were found.")
        kbscan = KillerBee(device=scannerDevId, datsource="Wardrive Live")
    #  return devices that we didn't choose to the free state
    for inspectedDevId in inspectedDevs:
        zbdb.update_devices_status(inspectedDevId, 'Free')
    print 'Network discovery device is %s' % (scannerDevId)
    zbdb.update_devices_status(scannerDevId, 'Discovery')

    # Much of this code adapted from killerbee/tools/zbstumbler:main
    beacon = "\x03\x08\x00\xff\xff\xff\xff\x07" #beacon frame
    beaconp1 = beacon[0:2]  #beacon part before seqnum field
    beaconp2 = beacon[3:]   #beacon part after seqnum field
    seqnum = 0              #seqnum to use (will cycle)
    channel = 11            #starting channel (will cycle)
    # Loop injecting and receiving packets
    while 1:
        if channel > 26: channel = 11
        if seqnum > 255: seqnum = 0
        try:
            #if verbose: print 'Setting channel to %d' % channel
            kbscan.set_channel(channel)
        except Exception, e:
            print 'Error: Failed to set channel to %d' % channel
            print e
            sys.exit(-1)
        if verbose: print 'Injecting a beacon request on channel %d.' % channel
        try:
            beaconinj = ''.join([beaconp1, "%c" % seqnum, beaconp2])
            kbscan.inject(beaconinj)
        except Exception, e:
            print 'Error: Unable to inject packet', e
            sys.exit(-1)

        # Process packets for 2 seconds looking for the beacon response frame
        start = time.time()
        while (start + 2 > time.time()):
            recvpkt = kbscan.pnext() #get a packet (is non-blocking)
            # Check for empty packet (timeout) and valid FCS
            if recvpkt != None and recvpkt[1]:
                #if verbose: print "Received frame."
                newNetwork = doScan_processResponse(recvpkt, channel, zbdb, kbscan, verbose)
                if newNetwork != None:
                    startCapture(zbdb, newNetwork)
        kbscan.sniffer_off()
        seqnum += 1
        channel += 1

    #TODO currently unreachable code, but maybe add a condition to break the infinite while loop in some circumstance to free that device for capture?
    kbscan.close()
    zbdb.update_devices_status(scannerDevId, 'Free')
# --- end of doScan ---
