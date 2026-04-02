// Protocol: $channel,angle*checksum (NMEA-style, XOR checksum).
// Channel 1 -> pin 9, channel 2 -> pin 10. Angle 0-180.

#include <Servo.h>
Servo servo1, servo2;  // initialize the servo motors

char lineBuf[32];      // initialize the buffer for the incoming serial data

void setup() {
  servo1.attach(9);    // attach servo motor 1 to the pin 9
  servo2.attach(10);   // attach servo motor 2 to the pin 10
  Serial.begin(115200);  // start the serial communication at 9600 

  // initial state: block both 390 and 422
  servo1.write(0);
  servo2.write(0);
}

// xorChecksum function: calculate the XOR checksum of a string
uint8_t xorChecksum(const char* s, int len) {
  uint8_t c = 0;                                       // initialize the checksum
  for (int i = 0; i < len; i++) c ^= (uint8_t)s[i];    // XOR the bytes in the string
  return c;
}

// processLine function: process the incoming serial data
void processLine(const char* line) {
  if (line[0] != '$') return;
  const char* star = strchr(line, '*');
  if (!star || star - line < 4) return;
  int payloadLen = star - (line + 1);
  if (payloadLen >= (int)sizeof(lineBuf)) return;

  uint8_t expected = xorChecksum(line + 1, payloadLen);
  unsigned int rx = 0;
  if (sscanf(star + 1, "%03u", &rx) != 1) return;
  if ((uint8_t)rx != expected) return;

  int ch = 0, angle = 0;
  if (sscanf(line + 1, "%d,%d", &ch, &angle) != 2) return;
  if (ch < 1 || ch > 2) return;
  if (angle < 0 || angle > 180) return;

  if (ch == 1) servo1.write(angle);
  if (ch == 2) servo2.write(angle);
}

// loop() function: read the incoming serial data and process it
void loop() {
  if (Serial.available() > 0) {
    int n = Serial.readBytesUntil('\n', (uint8_t*)lineBuf, sizeof(lineBuf) - 1);
    if (n > 0) {
      lineBuf[n] = '\0';
      processLine(lineBuf);
    }
  }
  delay(2);
}
