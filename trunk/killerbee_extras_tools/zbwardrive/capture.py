import sys
from datetime import datetime
import threading, signal
from killerbee import *

# Globals
triggers = []

# startCapture
# Given a database and a key into the database's networks table,
#  initiate a pcap and online database capture.
def startCapture(zbdb, arg_dblog, channel):
    '''
    Before calling, you should have already ensured the channel or the 
    channel which the key is associated with does not already have an active
    capture occuring.
    '''
    nextDev = zbdb.get_devices_nextFree()
    #TODO if device not availabe, wait till one opens up, and then occupy it. if nothing opens within 10 seconds, say you don't have a device available
    capChan = channel
    key = "CH%d" % channel
    if nextDev == None:
        print 'Cap%s: No free device to use for capture.' % key
        return None
    print 'Cap%s: Launching a capture on channel %s.' % (key, capChan)
    signal.signal(signal.SIGINT, interrupt)
    trigger = threading.Event()
    triggers.append(trigger)
    CaptureThread(capChan, nextDev, trigger, arg_dblog).start()
    zbdb.update_devices_start_capture(nextDev, capChan)

# Called on keyboard interput to exit threads and exit the scanner script.
def interrupt(signum, frame):
    global triggers
    for trigger in triggers:
        trigger.set()
    sys.exit(1)

# Thread to capture a given channel, using a given device, to a given filename
#  exits when trigger (threading.Event object) is set.
class CaptureThread(threading.Thread):
    def __init__(self, channel, devstring, trigger, arg_dblog):
        self.channel = channel
        self.rf_freq_mhz = (channel - 10) * 5 + 2400
        self.devstring = devstring
        self.trigger = trigger
        self.packetcount = 0
        self.arg_dblog = arg_dblog

        timeLabel = datetime.now().strftime('%Y%m%d-%H%M')
        fname = 'zb_c%s_%s.pcap' % (channel, timeLabel) #fname is -w equiv
        self.pd = PcapDumper(DLT_IEEE802_15_4, fname, ppi=True)

        threading.Thread.__init__(self)

    def run(self):
        if self.arg_dblog == True:
            self.kb = KillerBee(device=self.devstring, datasource="Wardrive Live")
        else:
            self.kb = KillerBee(device=self.devstring)
        self.kb.set_channel(self.channel)
        self.kb.sniffer_on()
        print "Capturing on \'%s\' at channel %d." % (self.kb.get_dev_info()[0], self.channel)
        # loop capturing packets to dblog and file
        while not self.trigger.is_set():
            packet = self.kb.pnext()
            if packet != None:
                self.packetcount+=1
                if self.arg_dblog == True: #by checking, we avoid wasted time and warnings
                    self.kb.dblog.add_packet(full=packet)
                self.pd.pcap_dump(packet[0], freq_mhz=self.rf_freq_mhz, 
                                  ant_dbm=packet['dbm'])
            #TODO if no packet detected in a certain length, and we know other channels want capture, then quit

        # trigger threading.Event set to false, so shutdown thread
        self.kb.sniffer_off()
        self.kb.close()
        self.pd.close()
        print "%d packets captured on channel %d." % (self.packetcount, self.channel)

