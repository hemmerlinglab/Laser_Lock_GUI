import socket
import numpy as np
import sys


def set_laser_setpoint(chan, freq):

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    server_address = ('192.168.42.136', 63700)

    print('Sending new setpoint: ' + str(freq))

    sock.connect(server_address)

    my_str = "{0:1d}:{1:.9f}".format(int(chan), np.float(freq))

    try:
        sock.sendall(my_str.encode())

    finally:

        sock.close()

    return



chan = sys.argv[1]
freq = sys.argv[2]

set_laser_setpoint(chan, freq)



