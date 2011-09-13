README: platforms_killerbee_extras

This directory contains information on different platforms, 
which are not yet fully supported within the main KillerBee.
Many platforms are supported within KillerBee, with no extra
configuration. However, some need hardware setup or more 
extensive software configuration, and those are explained here.

== Supported within KillerBee Trunk ==
- Atmel RZUSBSTICK
- Tmote Sky / TelosB Mote


== Supported Here ==

=== Freakduino ===

Freakduino is an Arduino clone with an Atmel RF230 radio chip,
designed and sold by Akiba (Freaklabs). When this device is 
given the additional Api-do hardware shield, and supported by
KillerBee, it is refered to as the zbPlant platform.

This platform is supported to enable stand-alone data capture
(i.e. not requiring a computer to sniff). The device may be 
used USB attached to a computer, or independently logging to
memory (currently EEPROM is supported) and then downloaded 
at a later time. This logging functionality is added in an
external "shield" which snaps into place, and this shield also
provides hardware control switches and a GPS chip.

The layout and part list for the shield and other instructions
are in freakduino/hardware, and the freakduino/firmware folder
contains libraries and an Arduino "sketch" program which serves
as the firmware for this platform.


=== Other ===

The KillerBee driver design added by the Api-do project
allows KillerBee to easily support additional devices. If you
want to support another device, be in touch so we can help 
you support it, and include the driver in the respository.