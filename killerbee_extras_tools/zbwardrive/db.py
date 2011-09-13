import string

# Manages Local "database" for ZBWarDrive:
# This keeps track of current ZBWarDrive and Sniffing Device State.
# It is different from the online logging database.

class ZBScanDB:
    """API to interact with the database storing information 
    for the zbscanning program"""

    # Database utility functions for SQLite
    def __init__(self):
        self.channels = {11:None, 12:None, 13:None, 14:None, 15:None, 16:None, 17:None, 18:None, 19:None, 20:None, 21:None, 22:None, 23:None, 24:None, 25:None, 26:None}
        self.devices = {}

    def close(self):
        pass

    # Add a new devices to the DB
    def store_devices(self, devid, devstr, devserial):
        self.devices[devid] = (devstr, devserial, 'Free', None)

    # Returns the devid of a device marked 'Free',
    # or None if there are no Free devices in the DB.
    def get_devices_nextFree(self):
        for devid, dev in self.devices.items():
            if dev[2] == 'Free':
                return devid

    def update_devices_status(self, devid, newstatus):
        if devid not in self.devices:
            return None
        (devstr, devserial, _, chan) = self.devices[devid]
        self.devices[devid] = (devstr, devserial, newstatus, chan)

    def update_devices_start_capture(self, devid, channel):
        if devid not in self.devices:
            return None
        self.devices[devid][2] = newstatus
        self.devices[devid][3] = channel

    # Add a new network to the DB
    def store_networks(self, key, spanid, source, channel, packet):
        if channel not in self.channels:
            return None
        self.channels[channel] = (key, spanid, source, packet)

    # Return the channel of the network identified by key,
    # or None if it doesn't exist in the DB.
    def get_networks_channel(self, key):
        #print "Looking up channel for network with key of %s" % (key)
        for chan, data in self.channels:
            if data[0] == key: return chan
        return None

    def channel_status_logging(self, chan):
        '''Returns False if we have not seen the network or are not currently logging it's channel, and returns True if we are currently logging it.'''
        if chan == None: raise Exception("None given for channel number")
        elif chan not in self.channels: raise Exception("Invalid channel")
        for dev in self.devices:
            if dev[3] == chan and dev[2] == 'Capture':
                return True
# end of ZBScanDB class

def toHex(bin):
    return ''.join(["%02x" % ord(x) for x in bin])
