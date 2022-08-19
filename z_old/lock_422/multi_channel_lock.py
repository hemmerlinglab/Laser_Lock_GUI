import sys
import serial
import time
import socket
from simple_pid import PID
import threading
import queue
import numpy as np

MAX_ARDUINO_SIGNAL = 4095.0
MAX_ARDUINO_SIGNAL_390 = 3250.0

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

        #print(len_msg)
        # Look for the response
        #amount_received = 0
        #amount_expected = len(message)
    
        data = sock.recv(len_msg)
        
        #while amount_received < amount_expected:
        #    #data = sock.recv(21)
        #    data = sock.recv(len_msg)
        #    amount_received += len(data)
        #    #print('received "%s"' % data)

        data = data.decode()

        data = data.split(',')

        output = {}
        for k in range(len(data)):
            hlp = data[k].split(':')
            output[int(hlp[0])] = float(hlp[1])


    finally:
        #print('closing socket')
        sock.close()

    return output


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

    send_arduino_control(ser, 0.0, 1)

    return ser


def send_arduino_control(ser, control, channel):

    # channel 1 : 422
    # channel 2 : 390

    if channel == 1:

        ard_mess =  int(MAX_ARDUINO_SIGNAL/20 * control + MAX_ARDUINO_SIGNAL/2.0)*10 + channel

    elif channel == 2:
               
        #control = control - 2.5
        #control = np.max([control, -10.0])

        ard_mess =  int(MAX_ARDUINO_SIGNAL_390/20 * control + MAX_ARDUINO_SIGNAL_390/2.0)*10 + channel
        
    mystr = '{:05d}'.format(ard_mess).encode('utf-8')
    ser.write(mystr) # converts from unicode to bytes        

    return



##################################################################
# PID
##################################################################


def init_pid(opts):

    act_values = get_frequencies(opts)

    pid_arr = {}
    for k in opts['pids'].keys():

        curr_pid = opts['pids'][k]
        setpoint = act_values[curr_pid['wavemeter_channel']]

        pid = PID(curr_pid['Kp'], curr_pid['Ki'], 0.0, setpoint, sample_time = 0.001, output_limits = [-10, 10])
    
        pid_arr[curr_pid['wavemeter_channel']] = pid

    return pid_arr


def loop_pid(ser, new_setpoint, pid_arr, act_values, opts):

    DAC_chan = 2 # 2 is 390
    
    if DAC_chan == 1:
        invert_pid = 1
    elif DAC_chan == 2:
        invert_pid = -1

    time.sleep(.01)

    #try:
    #    pids.setpoint = float(new_setpoint)        
    #except:
    #    pass
    
    if new_setpoint > 0:
        pids.setpoint = float(new_setpoint)        
        act_values = get_frequencies(opts)
        control = invert_pid * pids(act_values)
        
        send_arduino_control(ser, control, DAC_chan)

        if control == MAX_ARDUINO_SIGNAL or control == 0.0:
            print(control)
        #try:
        #    print("{0:4f} {3:5d} {1:.6f} {2:.6f}".format(control, act_values, new_setpoint, ard_mess))
        #except:
        #    print("error {0} {3} {1} {2}".format(control, act_values, new_setpoint, ard_mess))
                
    return act_values


def run_pid(q_arr, ser, pid_arr, opts):

    # q_arr : setpoints
    # pid_arr : pids

    got_new_setpoint = 0
    control = 0

    setpoints = get_frequencies(opts)
    #act_values = new_setpoint
    #print(setpoints.keys())
    while True:        

        # check if there is a new setpoint
        try:
            var = q_arr.get(block = False)

            for c in var.keys():
                # get specific setpoint of channel                
                if c in setpoints.keys():
                    setpoints[c] = var[c]
                
                    print()
                    print('New setpoint ... ' + str(setpoints))

                    got_new_setpoint = 20
                    pid_arr[c].set_auto_mode(True)
    
        except queue.Empty:            
            #print('error2')
            pass


        # loop over all channels
        for c in pid_arr.keys():
    
            # run PID
            if setpoints[c] > 0:


                got_new_setpoint -= 1

                pid_arr[c].setpoint = float(setpoints[c]) 
                act_values = get_frequencies(opts)
                

                if got_new_setpoint > 0:
                
                    control = opts['pids'][c]['sign'] * pid_arr[c](act_values[c])
    
                    # send control voltage to Arduino
                    send_arduino_control(ser, control, opts['pids'][c]['DAC_chan'])

                else:

                    pid_arr[c].set_auto_mode(False, last_output = control)
        

                #act_values[c] = loop_pid(ser, new_setpoint[c], pid_arr[c], act_values[c], opts['pids'][c])
   
                print(act_values)

            ##print(new_setpoint)

    return



#############################################################
# Server to receive new setpoint
#############################################################


def setup_setpoint_server():
    # Create a TCP/IP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # Bind the socket to the port
    server_address = ('192.168.42.136', 63700)
    print('starting up on %s port %s' % server_address)
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
            #print('connection from', client_address)

            # Receive the data in small chunks and retransmit it
            
            # data = 3:374.123456789 = <wavemeter_channel>:<new set point>

            data = connection.recv(15)
            
            data = data.decode()
            data = data.split(':')

            data = {int(data[0]) : float(data[1])}
            #str(data.decode())

            q_arr.put(data)

            #print(data)
            
        finally:
            connection.close()


###################################
# main
###################################


#while True:
#    data = get_frequencies(opts)

#    print(data)


opts = {
        'wavemeter_server_ip' : '192.168.42.20',
        'wavemeter_server_port' : 62500,
        'pids' : {
            5 : {'laser' : 422, 'wavemeter_channel' : 5, 'Kp' : 1, 'Ki' : 500, 'sign' : 1, 'DAC_chan' : 1},
            #6 : {'laser' : 390, 'wavemeter_channel' : 6, 'Kp' : 2, 'Ki' : 5000, 'sign' : -1, 'DAC_chan' : 2},
            }
        }


   
print('Init ...')
ser = init_arduino()

sock = setup_setpoint_server()

print('Init PID ...')
pid_arr = init_pid(opts)



# Queue allows for communicating between threads
q_arr = queue.Queue()

#[]

#for k in range(len(opts['pids'])):
#        q_arr.append(queue.Queue())

#        #q_arr.put(0.0)


# start PID thread
pid_thread = threading.Thread(target=run_pid, args=(q_arr, ser, pid_arr, opts), daemon = True)
pid_thread.start()


# start socket thread
socket_thread = threading.Thread(target=run_setpoint_server, args=(q_arr, sock,), daemon = True)
socket_thread.start()



# keep deamons running
while True:
    pass




