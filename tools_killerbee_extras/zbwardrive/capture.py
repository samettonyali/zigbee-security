import sys
from datetime import datetime
import threading, signal
from killerbee import *

# Globals
triggers = []

# startCapture
# Given a database and a key into the database's networks table,
#  initiate a pcap and online database capture.
def startCapture(zbdb, key):
    nextDev = zbdb.get_devices_nextFree()
    if nextDev == None:
        print 'Cap%s: No free device to use for capture.' % key
        return None
    capChan = zbdb.get_networks_channel(key)
    timeLabel = datetime.now().strftime('%Y%m%d-%H%M')
    print 'Cap%s: Launching a capture on channel %s.' % (key, capChan)
    fname = 'zb_c%s_%s.pcap' % (capChan, timeLabel) #fname is -w equiv
    signal.signal(signal.SIGINT, interrupt)
    trigger = threading.Event()
    triggers.append(trigger)
    CaptureThread(capChan, nextDev, fname, trigger).start()
    zbdb.update_devices_start_capture(nextDev, capChan)

# Called on keyboard interput to exit threads and exit the scanner script.
def interrupt(signum, frame):
    global triggers
    for trigger in triggers:
        trigger.set()
    sys.exit(1)

# Thread to capture a given channel, using a given device, to a given filename
#  exits when trigger (threading.Event object) is set.
#TODO if device not availabe, wait till one opens up, and then occupy it. if nothing opens within 10 seconds, say you don't have a device available
class CaptureThread(threading.Thread):
    def __init__(self, channel, devstring, fname, trigger):
        self.channel = channel
        self.devstring = devstring
        self.trigger = trigger
        self.pd = PcapDumper(DLT_IEEE802_15_4, fname)
        self.packetcount = 0
        threading.Thread.__init__(self)
    def run(self):
        self.kb = KillerBee(device=self.devstring, datasource="Wardrive Live")
        self.kb.set_channel(self.channel)
        self.kb.sniffer_on()
        print "Capturing on \'%s\' at channel %d." % (self.kb.get_dev_info()[0], self.channel)
        # loop capturing packets to dblog and file
        while not self.trigger.is_set():
            packet = self.kb.pnext()
            if packet != None:
                self.packetcount+=1
                self.kb.dblog.add_packet(full=packet)
                self.pd.pcap_dump(packet[0])
            #TODO if no packet detected in a certain length, and we know other channels want capture, then quit

        # trigger threading.Event set to false, so shutdown thread
        self.kb.sniffer_off()
        self.kb.close()
        self.pd.close()
        print "%d packets captured" % self.packetcount

