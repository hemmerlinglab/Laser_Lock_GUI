// Protocol: $channel,value*checksum (NMEA-style, XOR checksum).
// Example: $1,2048*5F

int val = 0;        // initialize: value to write to DAC
int chan = 0;       // initialize: channel to write to (1 or 2)
char lineBuf[32];   // initialize: buffer for incoming serial data

// setup() function: initialize the serial port and the DAC
void setup() {
  analogWriteResolution(12);       // set the resolution of the DAC to 12 bits
  Serial.begin(9600);              // start the serial communication at 9600 baud
  pinMode(LED_BUILTIN, OUTPUT);    // set the LED pin as output
  digitalWrite(LED_BUILTIN, LOW);  // turn off the LED
}

// xorChecksum function: calculate the XOR checksum of a string
uint8_t xorChecksum(const char* s, int len) {
  uint8_t c = 0;                                       // initialize the checksum
  for (int i = 0; i < len; i++) c ^= (uint8_t)s[i];    // XOR the bytes in the string
  return c;
}

// processLine function: process the incoming serial data
void processLine(const char* line) {
/* 
  Protocol: $channel,value*checksum
  Example: $1,2048*5F
  channel: 1 or 2
  value: 0 to 4095
  checksum: XOR of the payload
*/

  // validate the basic format of the incoming serial data
  if (line[0] != '$') return;                            // if the incoming serial data does not start with $, return
  const char* star = strchr(line, '*');                  // find the position of the * in the incoming serial data
  if (!star || star - line < 4) return;                  // if the incoming serial data does not contain *, return
  int payloadLen = star - (line + 1);                    // get the length of the payload
  if (payloadLen >= sizeof(lineBuf)) return;             // if the payload is too long, return

  // perform error checking
  uint8_t expected = xorChecksum(line + 1, payloadLen);  // calculate the expected checksum
  unsigned int rx = 0;                                   // initialize the received checksum
  if (sscanf(star + 1, "%03u", &rx) != 1) return;        // if the checksum is not in the correct format, return
  if ((uint8_t)rx != expected) return;                   // if the checksum is not correct, return

  // parse the channel and value from the incoming serial data
  int ch = 0, v = 0;                                     // initialize the channel and value
  if (sscanf(line + 1, "%d,%d", &ch, &v) != 2) return;   // if the channel and value are not in the correct format, return
  if (ch < 1 || ch > 2) return;                          // if the channel is not 1 or 2, return
  if (v < 0 || v > 4095) return;                         // if the value is not between 0 and 4095, return

  // write DAC
  chan = ch;                                             // set the channel
  val = v;                                               // set the value
  if (chan == 1) analogWrite(DAC0, val);                 // if the channel is 1, write the value to the DAC0
  if (chan == 2) analogWrite(DAC1, val);                 // if the channel is 2, write the value to the DAC1
}

// loop() function: read the incoming serial data and process it
void loop() {
  if (Serial.available() > 0) {                        // if there is data available to read
    int n = Serial.readBytesUntil('\n', (uint8_t*)lineBuf, sizeof(lineBuf) - 1); // read the data into the buffer
    if (n > 0) {                                       // if the data was read successfully
      lineBuf[n] = '\0';                               // null terminate the buffer
      processLine(lineBuf);                            // process the data
    }
  }
  delay(2);                                            // delay for 2 milliseconds
}
