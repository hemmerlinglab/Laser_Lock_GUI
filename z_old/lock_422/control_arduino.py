import serial
import os
import datetime
import time
import numpy as np
import sys


def send2ard(ser, voltage, chan):

    # converts -10V to 10V to 0 to 4095 for 12-bit analogwrite output of Arduino
    ard_mess =  int(3250.0/20 * voltage + 3250.0/2.0)*10 + chan
    
    #if voltage > 0:
    #    ard_mess =  int(1550) * 10 + chan
    #else:
    #    ard_mess =  int(1050) * 10 + chan

    mystr = '{:05d}'.format(ard_mess).encode('utf-8')
    ser.write(mystr) # converts from unicode to bytes


if True:
    serial_port  = 'COM5'; #pid lock arduino port    
    baud_rate = 9600; #In arduino, Serial.begin(baud_rate

    try:
        ser = serial.Serial(serial_port, baud_rate, 
                            bytesize=serial.SEVENBITS, 
                            parity=serial.PARITY_ODD, 
                           stopbits=serial.STOPBITS_ONE, 
                            timeout=1)
    except:
        try:
            ser.close()
        except:
            print ("Serial port already closed" )
        ser = serial.Serial(serial_port, baud_rate, 
                            bytesize=serial.SEVENBITS, 
                            parity=serial.PARITY_ODD, 
                            stopbits=serial.STOPBITS_ONE, 
                            timeout=1)

    delay = 0.02

    
    while True:
        send2ard(ser, np.float(sys.argv[1]), 2)
        time.sleep(delay)


