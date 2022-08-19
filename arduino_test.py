import serial
import os
import datetime
import time
from wlm import *
from Fiber import *
import numpy as np

def send2ard(ser, voltage, chan):

    # converts -10V to 10V to 0 to 4095 for 12-bit analogwrite output of Arduino
    ard_mess =  int(4095.0/20 * voltage + 4095.0/2.0)*10 + chan
    mystr = '{:05d}'.format(ard_mess).encode('utf-8')
    ser.write(mystr) # converts from unicode to bytes


if True:
    serial_port  = 'COM5'; #pid lock arduino port
    baud_rate = 9600; #In arduino, Serial.begin(baud_rate)

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

    #channel = 1
    delay = 0.1
	
    #wlm = WavelengthMeter()
    #time.sleep(1)
    
    #fib1 = Fiber('COM1')
    #fib1.setchan(channel)	
    
    #time.sleep(0.01)

    while True:
        for k in np.linspace(-10,10,100):
            print(k)
            send2ard(ser, k, 1)
            #send2ard(ser, k, 2)
            time.sleep(delay)
        #for k in np.linspace(10,-10,100):
        #    print(k)
        #    send2ard(ser, k, 1)
        #    send2ard(ser, k, 2)
        #    time.sleep(delay)



