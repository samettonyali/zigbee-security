README: tools_killerbee_extras

This directory contains tools developed on the KillerBee framework,
but which may have extra requirements, are in alpha, or otherwise 
do not belong in the main KillerBee repository.

= openear =

OpenEar seeks to assist in data capture where devices are operating
on multiple channels, or fast-frequency-hopping, etc. It expects
multiple interfaces, preferably one per 802.15.4 channel, to use
and assigns them sequentially across all channels. It optionally
interfaces with a gpsd daemon (reading from a standard serial GPS
device) to add GPS data. Please note that the device name of the
GPS device must be passed to Killerbee using the -g option, 
so that it may be ignored, as otherwise the device initializing 
process will "fuzz" the gps device and daemon. Running it with 
the -d option attempts to log data to a database using the Killerbee 
DBLogger (killerbee/dblog.py). Running it with the -p option includes 
location information in the PCAP using the CACE PPI standard.

Example usage:
sudo python scanner.py -d /dev/ttyUSB0 -p

= zbwardrive =

zbWarDrive is a tool that seeks to achieve optimal coverage of networks
with using only the available capture interfaces. It discovers
available interfaces and uses one to inject beacon requests
and listen for respones across channels. Once a network is found
on a channel, it assigns another device to continuously capture
traffic on that channel to a PCAP file.

Running it with the -d option attempts to log data to a database using
the KillerBee DBLogger (killerbee/dblog.py). This takes connection 
information for a pre-configured MySQL database from killerbee/config.py.
zbWarDrive will always try to write PCAP files (one per channel) locally
as well, and if -d is not defined, the PCAPS are the only output written.

GPS data logging support to be added.
