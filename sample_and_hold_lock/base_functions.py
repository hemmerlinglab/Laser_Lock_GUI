import socket
import serial
import time
from simple_pid import PID
import threading
import queue
import numpy as np


def get_frequencies(opts):

    # Create a TCP/IP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # Connect the socket to the port where the server is listening
    server_address = (opts['wavemeter_server_ip'], opts['wavemeter_server_port'])
    sock.connect(server_address)

    try:
        # Send data
        message = 'request'
        #print('sending "%s"' % message)
        sock.sendall(message.encode())

        len_msg = int(sock.recv(2).decode())

        data = sock.recv(len_msg)
        
        data = data.decode()
        
        output = float(data)

    finally:
        #print('closing socket')
        sock.close()

    return output


###################################################################
# Arduino Control Functions
###################################################################


def init_arduino(com_port, init_output = False):

    serial_port = com_port #'COM14'; #pid lock arduino port

    baud_rate = 9600 #; #In arduino, Serial.begin(baud_rate)

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

    if init_output:
        send_arduino_control(ser, 0.0, 1)
        send_arduino_control(ser, 0.0, 2)

    return ser




def send_arduino_control(ser, control, channel, max_output = 4095.0):

    #MAX_ARDUINO_SIGNAL = 4095.0
    #MAX_ARDUINO_SIGNAL_390 = 4095.0

    # channel = which arduino DAC channel

    ard_mess =  int(max_output/20.0 * control + max_output/2.0)*10 + channel

    mystr = '{:05d}'.format(ard_mess).encode('utf-8')
    ser.write(mystr) # converts from unicode to bytes        

    return



#############################################################
# Switch Fiber Channel
#############################################################

def switch_fiber_channel(opts, channel, wait_time = None):

    # Create a TCP/IP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # Bind the socket to the port
    server_address = (opts['fiber_server_ip'], opts['fiber_server_port'])
    print('Switching fiber channel on {0} port {1} to channel {2}'.format(server_address[0], server_address[1], channel))
    #sock.bind(server_address)

    sock.connect(server_address)

    sock.sendall(str(channel).encode())
    sock.close()

    #print(wait_time)

    if not wait_time == None:
        time.sleep(wait_time)

    return 



#############################################################
# Server to receive new setpoint
#############################################################


def setup_setpoint_server(opts):
    # Create a TCP/IP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # Bind the socket to the port
    server_address = (opts['setpoint_server_ip'], opts['setpoint_server_port'])
    print('starting up set point server on %s port %s' % server_address)
    sock.bind(server_address)

    # Listen for incoming connections
    sock.listen(1)

    return sock



def run_setpoint_server(q_arr, sock):
    while True:
        # Wait for a connection
        #print('waiting for a connection')
        connection, client_address = sock.accept()

        try:
            # Receive the data in small chunks and retransmit it
            
            # data = 3,374.123456789,1,1234  = <wavemeter_channel>,<new set point>,<switch_to_channel>,<wait_time (ms)>

            data = connection.recv(22)
            
            #print(data)
            
            data = data.decode()
            data = data.split(',')

            data = {
                    "channel" : int(data[0]), 
                    "frequency" : float(data[1]), 
                    "switch_channel" : int(data[2]),
                    "wait_time" : int(data[3])
            }


            q_arr.put(data)

        finally:
            connection.close()




##################################################################
# PID
##################################################################


def init_pid(opts):

    act_values = {}

    pid_arr = {}

    init_setpoints = {}

    for k in opts['pids'].keys():

        curr_pid = opts['pids'][k]
    
        switch_fiber_channel(opts, curr_pid['wavemeter_channel'], wait_time = 1)

        act_values[curr_pid['wavemeter_channel']] = get_frequencies(opts)
        
        setpoint = act_values[curr_pid['wavemeter_channel']]

        init_setpoints[curr_pid['wavemeter_channel']] = setpoint

        pid = PID(curr_pid['Kp'], curr_pid['Ki'], 0.0, setpoint, sample_time = 0.001, output_limits = [-10, 10])
    
        pid_arr[curr_pid['wavemeter_channel']] = pid

    return pid_arr, init_setpoints




def run_pid(q_arr, ser, pid_arr, current_channel, init_setpoints, opts):

    # q_arr : setpoints
    # pid_arr : pids

    act_values = {}
    setpoints = init_setpoints
    
    last_output = {}

    while True:        

        # check if there is a new setpoint
        try:
            var = q_arr.get(block = False)

            chan = var['channel']
            freq = var['frequency']
            switch_channel = var['switch_channel']
            wait_time = var['wait_time'] # 3300 = 3.3 seconds

            if switch_channel == 1:
                
                # set current PID on hold
                pid_arr[current_channel].set_auto_mode(False) #, last_output = last_output[current_channel])

                # switch to new fiber channel
                switch_fiber_channel(opts, chan, wait_time = wait_time/1000.0)

                # switch current_channel to new channel
                current_channel = chan
                
                # activate PID of new channel
                pid_arr[current_channel].set_auto_mode(True, last_output = last_output[current_channel])

            # get specific setpoint of channel                
            if chan in setpoints.keys():

                 setpoints[chan] = freq
                
                 print()
                 print('New setpoint ... ' + str(setpoints))

    
        except queue.Empty:            
            #print('error2')
            pass


        # loop over all channels
        for c in pid_arr.keys():
    
            # run PID
            if (setpoints[c] > 0) and (pid_arr[c].auto_mode == True):

                pid_arr[c].setpoint = float(setpoints[c]) 
                act_values = get_frequencies(opts)

                #if c == 6:
                #    print("{0}, {1}, {2}".format(act_values, pid_arr[c].setpoint, control))

                last_output[c] = pid_arr[c](act_values)
    
                # send control voltage to Arduino
                send_arduino_control(ser, last_output[c], opts['pids'][c]['DAC_chan'])

   
                #print(act_values)

            #else:
            elif (setpoints[c] <= 0) and (pid_arr[c].auto_mode == True):
                last_output[c] = 0.0

            #print(new_setpoint)

    return


#################################################################
# Init servers
#################################################################

def init_all(opts):

    print('Init ...')
    ser = init_arduino(com_port = opts['arduino_com_port'])
    
    sock = setup_setpoint_server(opts)
    
    print('Init PID ...')
    pid_arr, init_setpoints = init_pid(opts)
    
    # init fiber switcher
    switch_fiber_channel(opts, opts['fiber_switcher_init_channel'], wait_time = 0)
    
    # Queue allows for communicating between threads
    q_arr = queue.Queue()
    
    # start PID thread
    pid_thread = threading.Thread(target=run_pid, args=(q_arr, ser, pid_arr, opts['fiber_switcher_init_channel'], init_setpoints, opts), daemon = True)
    pid_thread.start()
    
    # start socket thread
    setpoint_thread = threading.Thread(target=run_setpoint_server, args=(q_arr, sock,), daemon = True)
    setpoint_thread.start()


