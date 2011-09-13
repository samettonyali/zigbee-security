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
device) to add GPS data.

= zbwardrive =

zbWarDrive is a tool that seeks to achieve optimal coverage of networks
with using only the available capture interfaces. It discovers
available interfaces and uses one to inject beacon requests
and listen for respones across channels. Once a network is found
on a channel, it assigns another device to continuously capture
traffic on that channel to a PCAP file.