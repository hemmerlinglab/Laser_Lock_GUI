import serial
import os
import datetime
import time
from simple_pid import PID
from wlm import *
from Fiber import *
import socket
import sys
import numpy as np
import threading

import queue

from base_functions import switch_fiber_channel

def init_distribution_servers(opts):
    # create conex objects
    wlm = WavelengthMeter()

    fib = Fiber('COM1')

    # init wavemeter servers
    dist_sockets = []
    for k in range(len(opts['dist_sockets'])):    

        # Create a TCP/IP socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # Bind the socket to the port
        server_address = (opts['wavemeter_server_ip'], opts['dist_sockets'][k]['port'])
        print('starting up on %s port %s' % server_address)
        sock.bind(server_address)

        # Listen for incoming connections
        sock.listen(1)

        dist_sockets.append(sock)


    # socket for fiber switcher server
    # Create a TCP/IP socket
    sock_fiber = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # Bind the socket to the port
    server_address = (opts['fiber_server_ip'], opts['fiber_server_port'])
    print('starting up on %s port %s' % server_address)
    sock_fiber.bind(server_address)

    # Listen for incoming connections
    sock_fiber.listen(1)


    return (wlm, dist_sockets, sock_fiber, fib)


def run_dist_server(opts, wlm, q, sock):    

    while True:
        # Wait for a connection
        #print('waiting for a connection')
        connection, client_address = sock.accept()

        try:            
            request = connection.recv(7).decode()

            # Frequency of the wavemeter is requested and send back
            if request == 'request':
                freq = q.get()

                freq = ",".join(freq)
                msg = str(freq).encode()

                len_msg = "{0:2d}".format(len(msg))
                # send the amount of data first
                connection.sendall(len_msg.encode())

                # send the data
                connection.sendall(msg)

            # Calibration of the wavemeter is initiated
            elif request == 'henecal':
                
                # receive hene freq
                hene_freq = float(connection.recv(10).decode())
                chan_hene = 4

                switch_fiber_channel(opts, chan_hene, wait_time = 3)
    
                wlm.SetExposure(100)
                time.sleep(1)
                wlm.Calibration(hene_freq)

                # switch back to previous channel
                # wait since the wvemeter server will readout the hene frequency
                # ideally this readout would be stopped while calibrating
                switch_fiber_channel(opts, 0, wait_time = 3)

            else:
                print('no more data from', client_address)
                break                       
            
        finally:
            # Clean up the connection
            connection.close()
        




def wavemeter_readout(q, wlm, fib):

	chans = [0]
	act_values = [0] * len(chans)

	try_trig = wlm.Trigger(3)

	new_freq = wlm.frequency

	while True:
	    for l in range(len(chans)):
                wlm.Trigger(0)
                				
                try_trig = wlm.Trigger(3)

                # obtains the actual frequency value
                new_freq = wlm.frequency               
                
                act_values[l] = "{0:10.6f}".format(new_freq)

                for k in range(len(q)):
                    q[k].put(act_values)
                
                #q.put(act_values)




#########################
# Fiber Switcher
#########################

def run_fiber_switcher_server(sock, fib, wlm):

    # switches the fiber switcher between channels 1-8
    # if chan = 0, then it switches to the previous channel

    previous_channel = 1
    current_channel = 1

    channel_exposures = {
            1 : 100,
            2 : 150,
            3 : 100,
            4 : 100, # HeNe channel
            5 : 450,
            6 : 450            
    }

    while True:
        # Wait for a connection
        #print('waiting for a connection')
        connection, client_address = sock.accept()

        try:
            data = connection.recv(1)

            if data:
                chan = int(data.decode())

                #print("Previous: " + str(previous_channel))
                #print(current_channel)
                #print(chan)
                #print()
              
                if chan == 0:
                    # if chan == 0, then switch to previous channel
                    chan = previous_channel
                    
                    previous_channel = current_channel
                    current_channel = chan
                else:
                    previous_channel = current_channel
                    current_channel = chan

                # set exposure time
                wlm.SetExposure(channel_exposures[chan])

                # switch channel
                fib.setchan(chan)


            else:
                print('no more data from', client_address)
                break
            
            
            
        finally:
            # Clean up the connection
            connection.close()
        #except:
        #    print('Issue')


###############################################################################
# main
###############################################################################


# some options
opts = {
    'fiber_server_ip' : '192.168.42.20',
    'fiber_server_port' : 65000,
    'wavemeter_server_ip' : '192.168.42.20',
    'dist_sockets' : [
        {
            'port' : 62500
        },
        {
            'port' : 62200
        }
        ]
}


# init server and sockets
(wlm, dist_sockets, sock_fiber, fib) = init_distribution_servers(opts)

#(wlm, sock, sock_fiber, fib) = init_wavemeter()

q_arr = []
for n in range(len(opts['dist_sockets'])):

    q_arr.append(queue.Queue())

    # distribution server 
    dist_server_thread = threading.Thread(target=run_dist_server, args=(opts, wlm, q_arr[n], dist_sockets[n],), daemon = True)
    dist_server_thread.start()



#q = queue.Queue()
current_channel = queue.Queue()

## start PID thread
#wavemeter_server_thread = threading.Thread(target=run_wavemeter_server, args=(q, sock,), daemon = True)
#wavemeter_server_thread.start()


fiber_switcher_thread = threading.Thread(target=run_fiber_switcher_server, args=(sock_fiber, fib, wlm,), daemon = True)
fiber_switcher_thread.start()


readout_thread = threading.Thread(target=wavemeter_readout, args=(q_arr, wlm, fib,), daemon = True)
readout_thread.start()


while True:
    pass
	
	





