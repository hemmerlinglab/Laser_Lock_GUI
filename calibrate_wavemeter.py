import time
from wlm import *
import numpy as np
from Fiber import *

fib = Fiber('COM1')
wlm = WavelengthMeter()
time.sleep(0.2)
    
f = wlm.frequency
print(f)


fib.setchan(4)

# set exposure time
wlm.SetExposure(200)

time.sleep(1)

# calibrate with HeNe
cal = wlm.Calibration(473.612512)

print(cal)



