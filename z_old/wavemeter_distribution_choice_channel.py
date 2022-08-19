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



CURR_CHANNEL = 1


def init_distribution_servers(opts):
    
    # connect to wavelength meter
    wlm = WavelengthMeter()

    # init fiber switcher
    fib = Fiber('COM1')
    
    dist_sockets = []
    for k in range(len(opts['dist_sockets'])):

    	# Create a TCP/IP socket
    	sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    	# Bind the socket to the port
    	server_address = (opts['server_ip'], opts['dist_sockets'][k]['port'])
    	print('starting up on %s port %s' % server_address)
    	sock.bind(server_address)

    	# Listen for incoming connections
    	sock.listen(1)

    	dist_sockets.append(sock)

    return (wlm, fib, dist_sockets)



def run_dist_server(q, sock):    

    while True:
        # Wait for a connection
        #print('waiting for a connection')
        connection, client_address = sock.accept()

        try:            
            request = connection.recv(7).decode()
            print(request[0:5])
            print('chann' == request[0:5])

            if request == 'request':
                freq = q.get()

                freq = ",".join(freq)
                msg = str(freq).encode()

                len_msg = "{0:2d}".format(len(msg))
                # send the amount of data first
                connection.sendall(len_msg.encode())

            	# send the data
                connection.sendall(msg)

            elif 'chann' == request[0:5]:

                CURR_CHANNEL = int(request[-1])
                fib.setchan(CURR_CHANNEL)

            else:
                print('no more data from', client_address)
                break						
            
        finally:
            # Clean up the connection
            connection.close()
        

        


def wavemeter_readout(q, wlm, fib, opts):

	# reads out wavemeter continuously and saves the results in the q-variables

	#wavemeter_channels = opts['wavemeter_channels']

	act_values = ['  0.000000'] #* len(wavemeter_channels)

	try_trig = wlm.Trigger(3)

	new_freq = wlm.frequency


	while True:
	    #for l in range(len(wavemeter_channels)):
                wlm.Trigger(0)
                
                # obtains the actual frequency value
                
                ## set fiber switcher to new channel
                #fib.setchan(wavemeter_channels[l])
                                			
                #time.sleep(0.20)                
				
                try_trig = wlm.Trigger(3)
                
                new_freq = wlm.frequency               
                                
                if new_freq < 0:
                	new_freq = 0.0

                act_values[0] = "{0:1d}:{1:10.6f}".format(CURR_CHANNEL, new_freq)

                #print(act_values)


                for k in range(len(q)):
                	q[k].put(act_values)
                
                


###############################################################################
# main
###############################################################################

# some options
opts = {
	'server_ip' : '192.168.42.20',
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
(wlm, fib, dist_sockets) = init_distribution_servers(opts)

q = []
for n in range(len(opts['dist_sockets'])):

	q.append(queue.Queue())

	# distribution server 
	dist_server_thread = threading.Thread(target=run_dist_server, args=(q[n], dist_sockets[n],), daemon = True)
	dist_server_thread.start()


# readout wavemeter
readout_thread = threading.Thread(target=wavemeter_readout, args=(q, wlm, fib, opts), daemon = True)
readout_thread.start()


while True:
    pass
	
	





