import socket
import numpy as np
import sys


def set_laser_setpoint(chan, freq, wait_time = 1, switch_channel = 0):

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    server_address = ('192.168.42.136', 63700)

    print('Sending new setpoint: ' + str(freq))

    sock.connect(server_address)

    my_str = "{0:1d},{1:.9f},{2:1d},{3:4d}".format(int(chan), np.float(freq), int(switch_channel), int(wait_time))

    try:
        sock.sendall(my_str.encode())

    finally:

        sock.close()

    return



chan = sys.argv[1]
freq = sys.argv[2]

set_laser_setpoint(chan, freq)



