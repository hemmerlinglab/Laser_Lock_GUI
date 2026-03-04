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
        print('starting up wavemeter server on %s port %s' % server_address)
        sock.bind(server_address)

        # Listen for incoming connections
        sock.listen(1)

        dist_sockets.append(sock)


    # socket for fiber switcher server
    # Create a TCP/IP socket
    sock_fiber = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # Bind the socket to the port
    server_address = (opts['fiber_server_ip'], opts['fiber_server_port'])
    print('starting up fiber switcher server on %s port %s' % server_address)
    sock_fiber.bind(server_address)

    # Listen for incoming connections
    sock_fiber.listen(1)


    return (wlm, dist_sockets, sock_fiber, fib)



def run_dist_server(sock):    

    while True:
        # Wait for a connection
        #print('waiting for a connection')
        connection, client_address = sock.accept()

        try:            
            request = connection.recv(7).decode()
            #print(request)

            if request == 'request':
                wlm.Trigger(0)                
                
                #try_trig = wlm.Trigger(3)
                
                new_freq = wlm.frequency               
                                
                act_values = "{0:10.6f}".format(new_freq)

                freq = act_values #",".join(act_values)
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

                # set exposure time
                if chan == 5:
                    wlm.SetExposure(200)
                elif chan == 6:
                    wlm.SetExposure(200)
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

for n in range(len(opts['dist_sockets'])):

    # distribution server 
    dist_server_thread = threading.Thread(target=run_dist_server, args=(dist_sockets[n],), daemon = True)
    dist_server_thread.start()



#q = queue.Queue()
current_channel = queue.Queue()

## start PID thread
#wavemeter_server_thread = threading.Thread(target=run_wavemeter_server, args=(q, sock,), daemon = True)
#wavemeter_server_thread.start()


fiber_switcher_thread = threading.Thread(target=run_fiber_switcher_server, args=(sock_fiber, fib, wlm, current_channel,), daemon = True)
fiber_switcher_thread.start()




while True:
    pass
	
	





