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


def init_distribution_servers():
    # create conex objects
    wlm = WavelengthMeter()

    #fib = Fiber('COM1')
    
    fib = None

    # Create a TCP/IP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # Bind the socket to the port
    server_address = ('192.168.42.20', 62500)
    print('starting up on %s port %s' % server_address)
    sock.bind(server_address)

    # Listen for incoming connections
    sock.listen(1)



    # Create a TCP/IP socket
    sock2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # Bind the socket to the port
    server_address = ('192.168.42.20', 62200)
    print('starting up on %s port %s' % server_address)
    sock2.bind(server_address)

    # Listen for incoming connections
    sock2.listen(1)

    return (wlm, sock, sock2, fib)



def run_dist_server(q, sock):    

    while True:
        # Wait for a connection
        #print('waiting for a connection')
        connection, client_address = sock.accept()

        try:            
            data = connection.recv(21)            

            if data:
                freq = q.get()

                freq = ",".join(freq)
            
                connection.sendall(str(freq).encode())
            else:
                print('no more data from', client_address)
                break						
            
        finally:
            # Clean up the connection
            connection.close()
        

def run_dist_server2(q, sock):    

    while True:
        # Wait for a connection
        #print('waiting for a connection')
        connection, client_address = sock.accept()

        try:            
            data = connection.recv(21)            

            if data:
                freq = q.get()

                freq = ",".join(freq)
            
                connection.sendall(str(freq).encode())
            else:
                print('no more data from', client_address)
                break                       
            
        finally:
            # Clean up the connection
            connection.close()
        


def wavemeter_readout(q, q2, wlm, fib):

	chans = [5]
	act_values = [0] * len(chans)

	try_trig = wlm.Trigger(3)

	new_freq = wlm.frequency

	while True:
	    for l in range(len(chans)):
                wlm.Trigger(0)
                
                # obtains the actual frequency value
                #fib.setchan(chans[l])
                                
				
                time.sleep(0.6)
                #print(chans[l])
				
                try_trig = wlm.Trigger(3)
                #time.sleep(.01)
                new_freq = wlm.frequency               
                
                act_values[l] = "{0:.6f}".format(new_freq)
                #if new_freq >= 0:

                #elif new_freq == -3.0:
                #    act_values[l] = 'UNDER     '
                #elif new_freq == -4.0:
                #    act_values[l] = 'OVER      '
                #else:
                #    act_values[l] = 'ERROR   ' 

                #print(act_values)

                q.put(act_values)
                q2.put(act_values)

                #print(len(act_values))


###############################################################################
# main
###############################################################################

(wlm, sock, sock2, fib) = init_distribution_servers()

q = queue.Queue()
q2 = queue.Queue()

# distribution server 1
dist_server_thread = threading.Thread(target=run_dist_server, args=(q, sock,), daemon = True)
dist_server_thread.start()


# distribution server 2
dist_server2_thread = threading.Thread(target=run_dist_server2, args=(q2, sock2,), daemon = True)
dist_server2_thread.start()

# readout wavemeter
readout_thread = threading.Thread(target=wavemeter_readout, args=(q, q2, wlm, fib), daemon = True)
readout_thread.start()


while True:
    pass
	
	





