import time
from wlm import *
import numpy as np

    
wlm = WavelengthMeter()
time.sleep(0.2)
    
f = wlm.frequency
print(f)

# set exposure time
wlm.SetExposure(150)

time.sleep(1)

# calibrate with HeNe
cal = wlm.Calibration(473.612512)

print(cal)



