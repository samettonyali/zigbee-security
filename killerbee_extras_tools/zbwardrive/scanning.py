#!/usr/bin/env python

import sys
import string
import socket
import struct

from killerbee import *
from db import toHex
from capture import startCapture
from scapy.all import Dot15d4, Dot15d4Beacon

# doScan_processResponse
def doScan_processResponse(packet, channel, zbdb, kbscan, verbose, dblog=dblog):
    scapyd = Dot15d4(packet['bytes'])
    # Check if this is a beacon frame
    if isinstance(scapyd.payload, Dot15d4Beacon):
        if verbose: print "Received frame is a beacon."
        spanid = scapyd.gethumanval('src_panid')
        source = scapyd.gethumanval('src_addr')
        key = ''.join([spanid, source])
        #TODO if channel already being logged, ignore it as something new to capture
        if zbdb.channel_status_logging(channel) == False:
            if verbose:
                print "A network on a channel not currently being logged replied to our beacon request."
                #print hexdump(packet['bytes'])
                #print scapyd.show2()
            # Store the network in local database so we treat it as already discovered by this program:
            zbdb.store_networks(key, spanid, source, channel, packet['bytes'])
            # Log to the mysql db or to the appropriate pcap file
            if dblog == True:
                kbscan.dblog.add_packet(full=packet, scapy=scapyd)
            else:
                #TODO log this to a PPI pcap file maybe, so the packet is not lost? or print to screen?
                pass
            return channel
        else: #network designated by key is already being logged
            if verbose:
                print 'Received frame is a beacon for a network we already found and are logging.'
                return None
    else: #frame doesn't look like a beacon according to scapy
        return None
# --- end of doScan_processResponse ---

# doScan
def doScan(zbdb, verbose, dblog=False, agressive=False, staytime=2):
    # Choose a device for injection scanning:
    scannerDevId = zbdb.get_devices_nextFree()
    # log to online mysql db or to some local pcap files?
    kbscan = KillerBee(device=scannerDevId, datasource=("Wardrive Live" if dblog else None))
    #  we want one that can do injection
    inspectedDevs = []
    while (kbscan.check_capability(KBCapabilities.INJECT) == False):
        zbdb.update_devices_status(scannerDevId, 'Ignore')
        inspectedDevs.append(scannerDevId)
        kbscan.close()
        scannerDevId = zbdb.get_devices_nextFree()
        if scannerDevId == None:
            raise Exception("Error: No free devices capable of injection were found.")
        kbscan = KillerBee(device=scannerDevId, datasource=("Wardrive Live" if dblog else None))
    #  return devices that we didn't choose to the free state
    for inspectedDevId in inspectedDevs:
        zbdb.update_devices_status(inspectedDevId, 'Free')
    print 'Network discovery device is %s' % (scannerDevId)
    zbdb.update_devices_status(scannerDevId, 'Discovery')

    # Much of this code adapted from killerbee/tools/zbstumbler:main
    # Could build this with Scapy but keeping manual construction for performance
    beacon = "\x03\x08\x00\xff\xff\xff\xff\x07" #beacon frame
    beaconp1 = beacon[0:2]  #beacon part before seqnum field
    beaconp2 = beacon[3:]   #beacon part after seqnum field
    seqnum = 0              #seqnum to use (will cycle)
    channel = 11            #starting channel (will cycle)
    iteration = 0           #how many loops have we done through the channels?
    # Loop injecting and receiving packets
    while 1:
        if channel > 26:
            channel = 11
            iteration += 1
        if seqnum > 255: seqnum = 0
        try:
            #if verbose: print 'Setting channel to %d' % channel
            kbscan.set_channel(channel)
        except Exception as e:
            raise Exception('Failed to set channel to %d (%s).' % (channel,e))
        if verbose:
            print 'Injecting a beacon request on channel %d.' % channel
        try:
            beaconinj = beaconp1 + "%c" % seqnum + beaconp2
            kbscan.inject(beaconinj)
        except Exception, e:
            raise Exception('Unable to inject packet (%s).' % e)

        # Process packets for staytime (default 2 seconds) looking for the beacon response frame
        endtime = time.time() + staytime
        nonbeacons = 0
        while (endtime > time.time()):
            recvpkt = kbscan.pnext() #get a packet (is non-blocking)
            # Check for empty packet (timeout) and valid FCS
            if recvpkt != None and recvpkt['validcrc']:
                #if verbose: print "Received frame."
                newNetworkChannel = doScan_processResponse(recvpkt, channel, zbdb, kbscan, verbose, dblog=dblog)
                # Ugly. Gives you either a key for a network or a channel. Call startCapture differently based on this.
                if newNetworkChannel != None:
                    startCapture(zbdb, newNetworkChannel, dblog=dblog)
                    nonbeacons = 0 # forget about any non-beacons, as we don't care, we saw a beacon!
                    break          # made up our mind, stop wasting time
                elif agressive:    # we may care even though it wasn't a beacon
                    nonbeacons += 1
                    if verbose:
                        print 'Received frame (# %d) is not a beacon.' % nonbeacons, toHex(recvpkt['bytes'])

        # If we're in agressive mode and didn't see a beacon, we have nonbeacons > 0.
        # If we aren't logging the channel currently, and
        # If we have already tried a loop through without being agressive
        if nonbeacons > 0 and iteration > 2 and zbdb.channel_status_logging(channel) == False:
            if verbose:
                print "Start capture on %d as a channel without beacon." % channel
            #TODO
            # Maybe just increase a count and increase stay time on this channel to see if we get a few packets, thus making us care?
            # Maybe also do at least a full loop first every so often before going after these random packets...
            startCapture(zbdb, channel, dblog=dblog)
        elif verbose:
            print "Had {0} nonbeacon packets on loop iteration {1} and found that channel {2} being already logged was {3}.".format(
                nonbeacons, iteration, channel, zbdb.channel_status_logging(channel))

        kbscan.sniffer_off()
        seqnum += 1
        channel += 1

    #TODO currently unreachable code, but maybe add a condition to break the infinite while loop in some circumstance to free that device for capture?
    kbscan.close()
    zbdb.update_devices_status(scannerDevId, 'Free')
# --- end of doScan ---

