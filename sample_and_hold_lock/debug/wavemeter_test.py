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


# create conex objects
wlm = WavelengthMeter()

wlm.SetExposure(150) # in ms


