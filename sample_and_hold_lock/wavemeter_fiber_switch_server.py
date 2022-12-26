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


def run_dist_server(q, sock):    

    while True:
        # Wait for a connection
        #print('waiting for a connection')
        connection, client_address = sock.accept()

        try:            
            request = connection.recv(7).decode()
            #print(request)

            if request == 'request':
                freq = q.get()

                freq = ",".join(freq)
                msg = str(freq).encode()

                len_msg = "{0:2d}".format(len(msg))
                # send the amount of data first
                connection.sendall(len_msg.encode())

                # send the data
                connection.sendall(msg)
            else:
                print('no more data from', client_address)
                break                       
            
        finally:
            # Clean up the connection
            connection.close()
        




def wavemeter_readout(q, wlm, fib, current_channel):

	chans = [0]
	act_values = [0] * len(chans)

	try_trig = wlm.Trigger(3)

	new_freq = wlm.frequency

	while True:
	    for l in range(len(chans)):
                wlm.Trigger(0)
                
                # obtains the actual frequency value
                #fib.setchan(chans[l])
                                
				
                #time.sleep(0.6)
                #print(chans[l])
				
                try_trig = wlm.Trigger(3)

                #time.sleep(.01)
                new_freq = wlm.frequency               
                
                
                #act_values[l] = "{0:1d}:{1:10.6f}".format(current_channel, new_freq)
                act_values[l] = "{0:10.6f}".format(new_freq)


                #print(act_values)
                for k in range(len(q)):
                    q[k].put(act_values)
                
                #q.put(act_values)




#########################
# Fiber Switcher
#########################

def run_fiber_switcher_server(sock, fib, wlm, current_channel):


    while True:
        # Wait for a connection
        #print('waiting for a connection')
        connection, client_address = sock.accept()

        try:
            data = connection.recv(1)

            if data:
                chan = int(data.decode())

                #print('Changing channel to ' + str(chan))
                # set exposure time
                if chan == 1:
                    wlm.SetExposure(100)
                elif chan == 2:
                    wlm.SetExposure(100)
                elif chan == 3:
                    wlm.SetExposure(100)
                elif chan == 4: # HeNe Channel
                    wlm.SetExposure(100)
                elif chan == 5:
                    wlm.SetExposure(450)
                elif chan == 6:
                    wlm.SetExposure(450)
                else:
                    wlm.SetExposure(100)

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
    dist_server_thread = threading.Thread(target=run_dist_server, args=(q_arr[n], dist_sockets[n],), daemon = True)
    dist_server_thread.start()



#q = queue.Queue()
current_channel = queue.Queue()

## start PID thread
#wavemeter_server_thread = threading.Thread(target=run_wavemeter_server, args=(q, sock,), daemon = True)
#wavemeter_server_thread.start()


fiber_switcher_thread = threading.Thread(target=run_fiber_switcher_server, args=(sock_fiber, fib, wlm, current_channel,), daemon = True)
fiber_switcher_thread.start()


readout_thread = threading.Thread(target=wavemeter_readout, args=(q_arr, wlm, fib, current_channel,), daemon = True)
readout_thread.start()


while True:
    pass
	
	





