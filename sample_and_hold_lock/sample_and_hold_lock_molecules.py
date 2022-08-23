import sys
import serial
import time
import socket
from simple_pid import PID
import threading
import queue
import numpy as np

from base_functions import *






###################################
# main
###################################

opts = {
        'arduino_com_port' : 'COM14'
        'wavemeter_server_ip' : '192.168.42.20',
        'wavemeter_server_port' : 62500,
        'setpoint_server_ip' : '192.168.42.20',
        'setpoint_server_port' : 63700,
        'fiber_server_ip' : '192.168.42.20',
        'fiber_server_port' : 65000,
        'pids' : {
            2 : {'laser' : 398, 'wavemeter_channel' : 2, 'Kp' : -10, 'Ki' : -10000, 'DAC_chan' : 2},
            3 : {'laser' : 1064, 'wavemeter_channel' : 3, 'Kp' : 10, 'Ki' : 4000, 'DAC_chan' : 1},
            },
        'fiber_switcher_init_channel' : 2
        }
   


init_all(opts)


# keep deamons running
while True:
    pass




