/******************************************************************/
/* 
  Chibi Web Server
  This is a modification of the original web server file that comes
  in the Arduino Ethernet library. Its purpose is to demonstrate how
  to use the Chibi library with the Arduino Ethernet library.

  We're only checking analog channels 0, 1, 4, and 5. Analog channels
  2 and 3 are being used for the wireless radio.  

  In order to run both libraries at the same time, either 
  CHB_RX_POLLING_MODE needs to be set to 1 in chibiUsrCfg.h or the
  Arduino ethernet code needs to be changed to protect the Wiznet
  chip accesses from interrupts. A tutorial on how to do this should
  be available soon on the FreakLabs site. 

  -- Akiba
*/
/******************************************************************/

/*
  Web  Server
 
 A simple web server that shows the value of the analog input pins.
 using an Arduino Wiznet Ethernet shield. 
 
 Circuit:
 * Ethernet shield attached to pins 10, 11, 12, 13
 * Analog inputs attached to pins A0 through A5 (optional)
 
 created 18 Dec 2009
 by David A. Mellis
 modified 4 Sep 2010
 by Tom Igoe
 
 */

#include <SPI.h>
#include <Ethernet.h>
#include <chibi.h>

// Enter a MAC address and IP address for your controller below.
// The IP address will be dependent on your local network:
byte mac[] = { 0xDE, 0xAD, 0xBE, 0xEF, 0xFE, 0xED };
byte ip[] = { 192,168,0, 30 };

// Initialize the Ethernet server library
// with the IP address and port you want to use 
// (port 80 is default for HTTP):
Server server(80);

// We're only checking analog channels 0, 1, 4, and 5. Channels
// 2 and 3 are being used for the wireless radio. 
byte channel[] = {0, 1, 4, 5};

static int prev;

void setup()
{
    // Initialize the chibi command line and set the speed to 57600 bps
  chibiCmdInit(57600);
  
  // Initialize the chibi wireless stack
  chibiInit();
  
  
  // start the Ethernet connection and the server:
  Ethernet.begin(mac, ip);
  server.begin();
}

void loop()
{
  // listen for incoming clients
  Client client = server.available();
  if (client) {
 
    // an http request ends with a blank line
    boolean currentLineIsBlank = true;
    while (client.connected()) {
      if (client.available()) {
        
        // We're adding the chibi receive function here as well as in the
	// main loop. Otherwise, when a client (browser) connects, then its possible
	// that a long time can elapse before we exit this loop. This means
	// that there's a high potential to lose data. 
        chibiRcv();
        
        char c = client.read();
        // if you've gotten to the end of the line (received a newline
        // character) and the line is blank, the http request has ended,
        // so you can send a reply
        if (c == '\n' && currentLineIsBlank) {
          // send a standard http response header
          client.println("HTTP/1.1 200 OK");
          client.println("Content-Type: text/html");
          client.println();

          // output the value of each analog input pin
          for (int analogChannel = 0; analogChannel < 4; analogChannel++) {
            client.print("analog input ");
            client.print(channel[analogChannel], DEC);
            client.print(" is ");
            client.print(analogRead(channel[analogChannel]));
            client.println("<br />");
          }
          break;
        }
        if (c == '\n') {
          // you're starting a new line
          currentLineIsBlank = true;
        } 
        else if (c != '\r') {
          // you've gotten a character on the current line
          currentLineIsBlank = false;
        }
      }
      
    }
    // give the web browser time to receive the data
    delay(1);
    // close the connection:
    client.stop();
  }
  
  // Poll the command line to check if any new data has arrived via the
  // serial interface. 
  chibiCmdPoll();

  // Handle any received data on the wireless interface. 
  chibiRcv();

}

/**************************************************************************/
/*!
    The Chibi receive function has been moved into this function since we're
    using it in two places. That way, it removes the need to duplicate code
    and is also better in terms of flash usage. 
*/
/**************************************************************************/
void chibiRcv()
{
  if (chibiDataRcvd() == true)
  { 
     byte buf[100];
     int len = chibiGetData(buf); 
     int rssi = chibiGetRSSI();
        
     // Print out the message and the signal strength
     Serial.print("Message received: "); Serial.print((char *)buf);
     Serial.print(", RSSI = 0x"); Serial.println(rssi, HEX);
  }
}


