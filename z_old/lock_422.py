import serial
import os
import datetime
import time
from simple_pid import PID
from wlm import *
from Fiber import *
import curses
import socket
import numpy as np

MAX_ARDUINO_SIGNAL = 3500.0
MAX_ARDUINO_SIGNAL_390 = 3250.0

def get_frequencies():

    # Create a TCP/IP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # Connect the socket to the port where the server is listening
    #server_address = ('localhost', 10000)
    server_address = ('192.168.42.20', 62500)
    #print('connecting to %s port %s' % server_address)
    sock.connect(server_address)

    try:
    
        # Send data
        message = 'request'
        #print('sending "%s"' % message)
        sock.sendall(message.encode())

        # Look for the response
        amount_received = 0
        amount_expected = len(message)
    
        while amount_received < amount_expected:
            data = sock.recv(21)
            amount_received += len(data)
            #print('received "%s"' % data)

        data = data.decode().split(',')
        data = list(map(float,data))

    finally:
        #print('closing socket')
        sock.close()

    return data[0]


def init_arduino():

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

    return ser


def get_setpoint(filename):

    file = open("z:\\Logs\\" + filename, "r")
    setpoint = file.readline().strip()
    file.close()

    try:
        a = np.float(setpoint)
    except:
        setpoint = 0.0
        #print(setpoint)
        print('cant convert')

    return np.float(setpoint)



if True:

    ser = init_arduino()


    setpoint_files = ['422_setpoint.txt','390_setpoint.txt']
    setpoints = [0,0,0,0]
    act_values = [0,0,0,0]
    ard_values = [0,0,0,0]
    ard_mess = [20481,20482,20483,20484]
    names = ['422','390','ARYA','HeNe']
    time.sleep(1)


    setpoints[0] = get_setpoint(setpoint_files[0])

    pids = ['','','','']
    Kps = [1,400,100,100]
    Kis = [300,10000,100,1000]
    Kds = [0,0,0,0]

    invert_pid = [1, -1]
    
    DAC_chans = [1,2]

    act_values[0] = get_frequencies()
    newset = ''



    # init PIDs
    i = 0
    pid = PID(Kps[i], Kis[i], Kds[i], setpoints[i], sample_time = 0.01, output_limits = [-10, 10])
    pids[i] = pid
              
    while True:
        
        newset = get_setpoint(setpoint_files[0])
        
        try:
                pids[l].setpoint = float(newset)
        except:
                pass

        act_values[0] = get_frequencies()


        l = 0
        new_freq = act_values[l]
        if new_freq >= 0:
            control = invert_pid[l] * pids[l](act_values[l])
            
            # 422
            ard_mess[l] =  int(MAX_ARDUINO_SIGNAL/20 * control + MAX_ARDUINO_SIGNAL/2.0)*10+DAC_chans[l]
           
            mystr = '{:05d}'.format(ard_mess[l]).encode('utf-8')
            ser.write(mystr) # converts from unicode to bytes
            

        elif new_freq == -3.0:
            act_values[l] = 'UNDER     '
        elif new_freq == -4.0:
            act_values[l] = 'OVER      '
        else:
            act_values[l] = 'ERROR     '

        if (int(ard_mess[l]/10)==0) or (int(ard_mess[l]/10)==3500):
            print('CTL: {0}'.format(int((ard_mess[l])/10)))
            print('SET: {0:.6f}'.format(pids[l].setpoint))
            print('ACT: {0:.6f}'.format(act_values[l]))



        time.sleep(0.01)


