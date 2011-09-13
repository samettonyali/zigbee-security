#!/usr/bin/env python
import sys
import signal
from killerbee import *
from killerbee.dev_freakduino import FREAKDUINO

def usage():
    print >>sys.stderr, """
zbdumpeeprom - a tcpdump-like tool for ZigBee/IEEE 802.15.4 networks
               for data retreived from a zbplant's EEPROM logging system
               instead of in real time

Usage: zbdumpeeprom [-w pcapfile] [-i devnumstring]
    """

def show_dev():
    kb = KillerBee()
    print "Dev\tProduct String\tSerial Number"
    for dev in kb_dev_list():
        print "%s\t%s\t%s" % (dev[0], dev[1], dev[2])

def interrupt(signum, frame):
    global packetcount
    global kb
    global pd
    kb.sniffer_off()
    kb.close()
    if pd:
        pd.close()
    print "%d packets captured" % packetcount
    sys.exit(0)

# PcapDumper, only used if -w is specified
pd = None

# Command-line arguments
arg_pcapsavefile = None
arg_devstring = None
arg_count = -1

# Global
packetcount = 0

while len(sys.argv) > 1:
    op = sys.argv.pop(1)
    if op == '-w':
        arg_pcapsavefile = sys.argv.pop(1)
    if op == '-i':
        arg_devstring = sys.argv.pop(1)
    if op == '-h':
        usage()
        sys.exit(0)
    if op == '-D':
        show_dev()
        sys.exit(0)
    if op == '-c':
        arg_count = int(sys.argv.pop(1))

if arg_pcapsavefile == None:
    print >>sys.stderr, "ERROR: Must specify a savefile with -w (libpcap)"
    usage()
    sys.exit(1)
if (arg_pcapsavefile != None):
    pd = PcapDumper(DLT_IEEE802_15_4, arg_pcapsavefile)

kb = KillerBee(device=arg_devstring)
signal.signal(signal.SIGINT, interrupt)

if not isinstance(kb.driver, FREAKDUINO):
    raise Exception("This script is only for Dartmouth-mod Freakduino devices.")

kb.sniffer_off() #we don't want the actual sniffer to be adding to EEPROM as we try to read it
print "zbdumpeeprom: reading from \'%s\'" % kb.get_dev_info()[0]

kb.driver.eeprom_dump()
while arg_count != packetcount:
    try:
        packet = kb.driver.pnext_rec()
        if packet != None:
            packetcount+=1
            if pd:
                pd.pcap_dump(packet[0])
    except StopIteration:
        print "Done Reading Data from EEPROM"
        break

kb.close()
if pd:
    pd.close()
print "%d packets received" % packetcount
