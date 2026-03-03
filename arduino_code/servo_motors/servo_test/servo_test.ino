#include <Servo.h>
Servo s_422, s_390;

void setup() {
  s_422.attach(9);
  s_390.attach(10);
}

void loop() {
  s_422.write(0);
  s_390.write(90);
  delay(2000);
  s_422.write(90);
  s_390.write(0);
  delay(2000);
}
