/*
Capture Packets Promiscously and Store into EEPROM
Supports the Dartmouth Freakduino Shield for EEPROM, button configuration, and GPS.
*/

#include <chibi.h>
#include <Wire.h>
#include "TinyGPS.h"
#include "NewSoftSerial.h"

#define GPS_NSS_RX          2    //GPS communication software serial pins RX
#define GPS_NSS_TX          3    //GPS communication software serial pins TX
#define LIVE_LOG_SWITCH     6    //switch to toggle between logging or sending via serial
#define GPS_LED             7    //led to show if GPS has a fix
#define LOGGING_LED         8    //led to show logging status (on if sniffer_on)
#define LOGGING_SWITCH      9    //push button pin to toggle sniffer_on variable
#define VERSION             0xB3 //software type/version number
#define EEPROM_PAGE_LENGTH  128  //number of bytes in one page
#define EEPROM_CONSEC_PAGES 512  //number of consecutive pages in EEPROM
#define EEPROM_MAX_PAGE_WRITE 30 //limited by Wire library buffer size
#define EEPROM_DEV_COUNT    2    //number of installed EEPROM devices (when add one, update cmdLoggingReset)
#define EEPROM_DEV_0        0x50 //i2c address of EEPROM first device (where config lives)
//CHB_MAX_PAYLOAD defines maximum number of bytes in a packet
#define MAX_PACKET_HEADER   20   //max bytes used to store information associated with a packet
#define LOC_STRING_LEN      23   //length of location string L!long!lati!alti!date;\0

boolean sniffer_on = false; //initialize capture forwarding to off
boolean log_led    = false; //log status LED starts off
int     live_log_val;

char recdString[CHB_MAX_PAYLOAD + MAX_PACKET_HEADER];
char locString[LOC_STRING_LEN];
byte len;                   //stores length of recd data
byte buf[CHB_MAX_PAYLOAD];  //stores recd data

NewSoftSerial nss(GPS_NSS_RX, GPS_NSS_TX);  //NSS object for GPS communication
TinyGPS gps;                //GPS parser object
long lat, lon, alt, oldlat, oldlon, oldalt;
unsigned long fix_age = TinyGPS::GPS_INVALID_AGE;
unsigned long date, time, olddate;

/**************************************************************************/
// Initialize
/**************************************************************************/
void setup()
{
  chibiCmdInit(57600);  //command line interface
  chibiInit();          //wireless stack
  Wire.begin();         //join i2c bus
  nss.begin(38400);     //start software serial for GPS data
  
  pinMode(LOGGING_LED, OUTPUT);
  pinMode(LOGGING_SWITCH, INPUT);
  digitalWrite(LOGGING_SWITCH, HIGH);  //pullup resistor so defaults to HIGH
  pinMode(GPS_LED, OUTPUT);
  pinMode(LIVE_LOG_SWITCH, INPUT);
  digitalWrite(LIVE_LOG_SWITCH, HIGH); //pullup resistor so defaults to HIGH
  
  //declare the commands for the command line (alias, function)
  chibiCmdAdd("SC!N", cmdSnifferOn);
  chibiCmdAdd("SC!F", cmdSnifferOff);
  chibiCmdAdd("SC!C", cmdSetChannel);
  chibiCmdAdd("SC!V", cmdGetVersion);
  chibiCmdAdd("SC!R", cmdLoggingReset);
  chibiCmdAdd("SC!D", cmdLoggingDump);
  
  chibiCmdAdd("gps", cmdGPSStatus);
  //chibiCmdAdd("read", cmdEEPROMRead);
  chibiCmdAdd("eeprom", cmdEEPROMStatus);
  chibiCmdAdd("eepromreset", cmdLoggingReset);
}

/**************************************************************************/
// Loop
/**************************************************************************/
void loop()
{
  chibiCmdPoll(); //Check for serial commands
  
  // Check for GPS updates and process
  while (nss.available())
  {
    if (gps.encode(nss.read()) == true)
    {
      oldlat = lat;
      oldlon = lon;
      oldalt = alt;
      olddate = date;
      gps.get_position(&lat, &lon, &fix_age);
      gps.get_datetime(&date, &time, &fix_age);
      alt = gps.altitude();
      break;  //stop when we get a valid sentence
    }
  }

  // Handle indicator lights / switches to change settings
  // Switch between logging to serial (high, switch off) or EEPROM (low, switch on)
  live_log_val = digitalRead(LIVE_LOG_SWITCH);
  // Sense a push of the logging button to toggle state
  if (digitalRead(LOGGING_SWITCH) == LOW) {
    sniffer_on = !sniffer_on;
    delay(300);
  }
  // Update the logging status LED if needed
  if (sniffer_on && !log_led) {
    digitalWrite(LOGGING_LED, HIGH);
    log_led = true;
  } else if (!sniffer_on && log_led) {
    digitalWrite(LOGGING_LED, LOW);
    log_led = false;
  }
  // Update the GPS status light
  if (fix_age == TinyGPS::GPS_INVALID_AGE) {
    digitalWrite(GPS_LED, LOW);  //no fix
  } else {
    digitalWrite(GPS_LED, HIGH); //fix
  }
  
  // Check if any data was received from the radio. If so, then handle it.
  if (chibiDataRcvd() == true)
  {
    // retrieve the data and the signal strength
    len = chibiGetData(buf);
    
    if (sniffer_on == true)
    {
      //Create location record if lon/lat/alt/date have changed
      int locStrLen = 0;
      if ((oldlon != lon) || (oldlat != lat) || (oldalt != alt) || (olddate != date))
      {
        locStrLen = makeLocString();
      }
      
      //Atmel AT86RF230 p51 says range is 0 to 28, in steps of 3db, covering 81dB, minimum sensitivity is -91dBm
      //PHYrf = RSSI_BASE_VAL + 3*(RSSI-1)
      //RSSI 0 is <=-91dBm; 28 is >= -10dBm
      //LQI indicator can also be requested (see p53)
      byte rssi = chibiGetRSSI();

      int strLen = makeRecdString(rssi, time, len, buf);

      if (live_log_val == HIGH)
      {
        //Send data live over serial
        if (locStrLen > 0)
        {
          Serial.write((byte*)locString, locStrLen);
        }
        Serial.write((byte*)recdString, strLen);
      } else {
        //Store data to external EEPROM for logging
        if ((locStrLen > 0) && (!i2c_eeprom_log(locString, locStrLen))) {
          sniffer_on = false;
          Serial.println("Memory has been filled. Stopped capture.");
        }
        else if (!i2c_eeprom_log(recdString, strLen)) {
          sniffer_on = false; //we don't have more memory to store captures in
          Serial.println("Memory has been filled. Stopped capture.");
        }
      }
    }
  }
}

int makeLocString()
{
  //Format L!long!lati!alti!date;\0
  int i=0;
  locString[i++] = 'L';  
  locString[i++] = '!';
  locString[i++] = (lon >> 24) & 0xFF;
  locString[i++] = (lon >> 16) & 0xFF;
  locString[i++] = (lon >> 8) & 0xFF;
  locString[i++] = (lon) & 0xFF;
  locString[i++] = (lat >> 24) & 0xFF;
  locString[i++] = (lat >> 16) & 0xFF;
  locString[i++] = (lat >> 8) & 0xFF;
  locString[i++] = (lat) & 0xFF;
  locString[i++] = (alt >> 24) & 0xFF;
  locString[i++] = (alt >> 16) & 0xFF;
  locString[i++] = (alt >> 8) & 0xFF;
  locString[i++] = (alt) & 0xFF;
  locString[i++] = (date >> 24) & 0xFF;
  locString[i++] = (date >> 16) & 0xFF;
  locString[i++] = (date >> 8) & 0xFF;
  locString[i++] = (date) & 0xFF;
  locString[i++] = ';';
  locString[i] = '\0';
  return i;
}

int makeRecdString(byte rssi, unsigned long time, byte len, byte* buf)
{
  // Format: R!<rssi>!<time>!<pktlength>!<pktdata>;\0
  // Define length needed in formatting for nonpacket data in MAX_PACKET_HEADER.
  int i=0;
  recdString[i++] = 'R';
  recdString[i++] = '!';
  recdString[i++] = rssi;
  recdString[i++] = '!'; //Time unsigned long into bytes
  recdString[i++] = (time >> 24) & 0xFF;
  recdString[i++] = (time >> 16) & 0xFF;
  recdString[i++] = (time >> 8) & 0xFF;
  recdString[i++] = time & 0xFF;
  recdString[i++] = '!';
  recdString[i++] = len;
  recdString[i++] = '!';
  for (int j=1; j<len+1; j++) { recdString[i+j-1] = buf[j]; }
  i += len;
  recdString[i++] = ';';
  recdString[i]   = '\0';
  return i;
}

/*
  Take given data of length i and write each byte, individually, to EEPROM.
  Roll over to new pages as needed, in a consecutive manner.
*/
boolean i2c_eeprom_log(char *data, int i)
{
  //Fill temp logging status variables from EEPROM
  byte logPosPageIndex = i2c_log_pageIndex_get();
  unsigned int logPosPage = i2c_log_pageNum_get();
  byte logPosDeviceIndex = i2c_log_deviceIndex_get();
  byte logPosCurrDevice = i2c_log_deviceAddr_get(logPosDeviceIndex);
  
  byte dataIndex = 0;
  while ((logPosPageIndex < EEPROM_PAGE_LENGTH) && (dataIndex < i))
  {
    //As space permits, write byte to EEPROM
    unsigned int cureeaddr = (logPosPage * EEPROM_PAGE_LENGTH) + logPosPageIndex;
    i2c_eeprom_write_byte(logPosCurrDevice, cureeaddr, data[dataIndex]);
    logPosPageIndex++;
    dataIndex++;

    //If we filled a page, reset to prepare for the next page
    if (logPosPageIndex >= EEPROM_PAGE_LENGTH)
    {
      //Reset variables to prepare for next page
      logPosPageIndex = 0;
      if (++logPosPage >= EEPROM_CONSEC_PAGES) {
        //Roll on to next EEPROM device in the array of devices
        if (++logPosDeviceIndex >= EEPROM_DEV_COUNT) {
          i2c_log_state_set(logPosDeviceIndex, logPosPage, logPosPageIndex);
          return false; //if are out of devices, aka we are out of memory!
        }
        logPosPage = 0;
      }

      //If didn't save all of data, keep saving it
      if (dataIndex < i) {
        int remainingLength = 0;
        char remainingData[i - dataIndex];
        while (dataIndex < i) { remainingData[remainingLength++] = data[dataIndex++]; }
        if ( ! i2c_eeprom_log(remainingData, remainingLength) ) {
          i2c_log_state_set(logPosDeviceIndex, logPosPage, logPosPageIndex);
          return false;  //if a recursive call returned failure
        }
      }
    }
  }
  //Update I2C log variables into EEPROM before exiting.
  i2c_log_state_set(logPosDeviceIndex, logPosPage, logPosPageIndex);
  return true;
}


/**************************************************************************/
// CHIBI COMMAND LINE FUNCTIONS
/**************************************************************************/

void cmdSnifferOn(int arg_cnt, char **args)
{
  sniffer_on = true;
  Serial.println("&C!N;");
}

void cmdSnifferOff(int arg_cnt, char **args)
{
  sniffer_on = false;
  Serial.println("&C!F;");
}

/*
void flash(int count) {
   for (int i=0; i<count; i++) {
     digitalWrite(LOGGING_LED, HIGH);
     delay(500);
     digitalWrite(LOGGING_LED, LOW);
     delay(500);
   } 
}
*/

void cmdSetChannel(int arg_cnt, char **args)
{
  int chan;
  chan = chibiCmdStr2Num(args[1], 10);
  if ((chan > 26) || (chan < 11)) {
    Serial.print("&C!EchanOutOfRange");
    Serial.print(chan, DEC);
    Serial.println(";");
  }
  chibiSetChannel(chan);
  Serial.println("&C!C;");
}

void cmdGetVersion(int arg_cnt, char **args)
{
  Serial.print("&C!V");
  Serial.write(VERSION);
  Serial.println(";");
}

//Logging Position Device Index (which device in the devices array)
// is stored in EEPROM EEPROM_DEV_0, byte 0.
void i2c_log_deviceIndex_set(byte deviceIndex) {
  i2c_eeprom_write_byte(EEPROM_DEV_0, 0, deviceIndex);
}
byte i2c_log_deviceIndex_get() {
  return i2c_eeprom_read_byte(EEPROM_DEV_0, 0);
}
//Logging Position Address of Device at Given Index
byte i2c_log_deviceAddr_get(byte deviceIndex) {
  if (deviceIndex > EEPROM_DEV_COUNT) { return 0xFF; }
  return i2c_eeprom_read_byte(EEPROM_DEV_0, deviceIndex+1);
}
//Logging Position Page Number (which page of the current device we're on)
// is stored in EEPROM EEPROM_DEV_0, bytes 9 and 10
void i2c_log_pageNum_set(unsigned int pospage) {
  i2c_eeprom_write_byte(EEPROM_DEV_0, 9,  (byte)(pospage >> 8));
  i2c_eeprom_write_byte(EEPROM_DEV_0, 10, (byte)(pospage & 0xFF));
}
unsigned int i2c_log_pageNum_get() {
  unsigned int val = i2c_eeprom_read_byte(EEPROM_DEV_0, 9) << 8;
  val |= i2c_eeprom_read_byte(EEPROM_DEV_0, 10);
  return val;
}
//Logging Position Page Index (index 0 to 128 within a page of next place to write)
// is stored in EEPROM EEPROM_DEV_0, byte 11.
void i2c_log_pageIndex_set(byte pageIndex) {
  i2c_eeprom_write_byte(EEPROM_DEV_0, 11, pageIndex);
}
byte i2c_log_pageIndex_get() {
  return i2c_eeprom_read_byte(EEPROM_DEV_0, 11);
}
//Set all 3 variables at once
void i2c_log_state_set(byte deviceIndex, unsigned int posPage, byte pageIndex) {
  i2c_log_deviceIndex_set(deviceIndex);
  i2c_log_pageNum_set(posPage);
  i2c_log_pageIndex_set(pageIndex);
}

void cmdLoggingReset(int arg_cnt, char **args)
{
  //Clears to default settings the EEPROM bytes that store the current logging state
  //logPosDevices[0], page 0 is reserved for logging state information
  //Set deviceIndex to zero (byte logPosDeviceIndex = 0;)
  i2c_log_deviceIndex_set(0x00);
  //Fill device array (8 spots max) (byte logPosDevices[2] = {0x50, 0x54};)
  // Addressing of 24LC1025 module is 1010[block select][addr 1][addr 0]
  // So a chip with addr0 & addr1 grounded has 2 blocks, addressed as 1010000 & 1010100
  i2c_eeprom_write_byte(EEPROM_DEV_0, 1, EEPROM_DEV_0); //device 0 (chip 1 part 1)
  i2c_eeprom_write_byte(EEPROM_DEV_0, 2, 0x54);         //device 1 (chip 1 part 2)
//  i2c_eeprom_write_byte(EEPROM_DEV_0, 3, 0x00);       //device 2 (chip 2 part 1)
//  i2c_eeprom_write_byte(EEPROM_DEV_0, 4, 0x00);       //device 3 (chip 2 part 2)
//  i2c_eeprom_write_byte(EEPROM_DEV_0, 5, 0x00);       //device 4 (chip 3 part 1)
//  i2c_eeprom_write_byte(EEPROM_DEV_0, 6, 0x00);       //device 5 (chip 3 part 2)
//  i2c_eeprom_write_byte(EEPROM_DEV_0, 7, 0x00);       //device 6 (chip 4 part 1)
//  i2c_eeprom_write_byte(EEPROM_DEV_0, 8, 0x00);       //device 7 (chip 4 part 2)
  //Store starting page number (unsigned int logPosPage = 1;)
  // (b/c on deviceZero, we want to start at page 1, as page 0 is reserved)
  i2c_log_pageNum_set(1);
  //Store the starting index for a page (byte logPosPageIndex = 0;)
  i2c_log_pageIndex_set(0);

  Serial.println("&C!R;");
}

void cmdLoggingDump(int arg_cnt, char **args)
{
  Serial.println("&C!D;");
  
  //Fill logging status variables from EEPROM
  // These represent the next space that would be logged to.
  byte logPosPageIndex = i2c_log_pageIndex_get();
  unsigned int logPosPage = i2c_log_pageNum_get();
  byte logPosDeviceIndex = i2c_log_deviceIndex_get();
  //Variables to keep track of where we currently are in walk through logging.
  // Initialized to the start of the logging space.
  byte curDeviceIndex = 0;
  unsigned int curPageNum = 1;
  byte curPageIndex = 0;
  
  while (curDeviceIndex <= logPosDeviceIndex)
  {
    byte curDeviceAddr = i2c_log_deviceAddr_get(curDeviceIndex);
    while (curPageNum <= logPosPage) {
      unsigned int pageOffset = curPageNum * EEPROM_PAGE_LENGTH;
      //Read through all valid pageIndex's on the current page:
      while (curPageIndex < EEPROM_PAGE_LENGTH) {
        if ((curDeviceIndex == logPosDeviceIndex) && (curPageNum == logPosPage) && (curPageIndex >= logPosPageIndex)) {
          Serial.println("[{[ DONE READING BACK ALL LOGGED DATA ]}]");
          return;
        }
        Serial.print(i2c_eeprom_read_byte(curDeviceAddr, pageOffset+curPageIndex));
        curPageIndex++;
      }
      //We read a page, so move onto next page:
      curPageNum++;
      curPageIndex = 0;
      if (curPageNum >= EEPROM_CONSEC_PAGES) { break; } //just bail out of inner while loop!
    }
    //We read a through all consecutive pages, move onto the next device:
    curDeviceIndex++;
    curPageNum = 0;
  }

  Serial.println("[{[ WE SHOULDN'T EXIT HERE ]}]");
}

void cmdGPSStatus(int arg_cnt, char **args)
{
  Serial.print("GPS Loc: lon="); Serial.print(lon);
  Serial.print(" lat="); Serial.print(lat);
  Serial.print(" alt="); Serial.print(alt);
  Serial.print(" age="); Serial.print(fix_age);
  Serial.print(" date="); Serial.print(date);
  Serial.print(" time="); Serial.println(time);
}

void cmdEEPROMStatus(int arg_cnt, char **args)
{
  Serial.print("EEPROM device 0x"); Serial.print(i2c_log_deviceAddr_get(i2c_log_deviceIndex_get()), HEX);
  Serial.print("; page "); Serial.print(i2c_log_pageNum_get(), DEC);
  Serial.print(" of "); Serial.print(EEPROM_CONSEC_PAGES, DEC);
  Serial.print("; pageIndex "); Serial.print(i2c_log_pageIndex_get(), DEC);
  Serial.print(" of "); Serial.println(EEPROM_PAGE_LENGTH, DEC);
}

//Read value from External (Logging) EEPROM
//Usage: read 0x50 0
void cmdEEPROMRead(int arg_cnt, char **args)
{
  int devaddr;
  unsigned int eeaddr;
  byte data;
  Serial.print("Reading from I2C addr 0x");
  devaddr = chibiCmdStr2Num(args[1], 16);
  Serial.print(devaddr, HEX);
  Serial.print(" at memory addr ");
  eeaddr = chibiCmdStr2Num(args[2], 10);
  Serial.println(eeaddr, DEC);
  data = i2c_eeprom_read_byte(devaddr, eeaddr);
  Serial.print("Got value: 0x");
  Serial.println(data, HEX);
}

/****************************************************************/
// I2C/TWI UTILITY FUNCTIONS
/****************************************************************/
byte i2c_eeprom_read_byte(int deviceaddress, unsigned int eeaddress )
{
  byte rdata = 0xFF;
  Wire.beginTransmission(deviceaddress);
  Wire.send((int)(eeaddress >> 8)); // MSB
  Wire.send((int)(eeaddress & 0xFF)); // LSB
  Wire.endTransmission();
  Wire.requestFrom(deviceaddress, 1);
  if (Wire.available()) rdata = Wire.receive();
  return rdata;
}

void i2c_eeprom_write_byte(int deviceaddress, unsigned int eeaddress, byte data)
{
  int rdata = data;
  Wire.beginTransmission(deviceaddress);
  Wire.send((int)(eeaddress >> 8)); // MSB
  Wire.send((int)(eeaddress & 0xFF)); // LSB
  //Serial.print("Write 0x"); Serial.print(rdata, HEX);
  //Serial.print(" at 0x"); Serial.print(deviceaddress, HEX);
  //Serial.print(" : 0x"); Serial.println(eeaddress, HEX);
  Wire.send(rdata);
  Wire.endTransmission();
  delay(5);
}
