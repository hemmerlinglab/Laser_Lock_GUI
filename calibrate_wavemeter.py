import sys
sys.path.append("sample_and_hold_lock")

from wlm import *
from base_functions import switch_fiber_channel


def calibrate_wavemeter(opts, wlm, hene_freq, chan_hene, chan_current):

        switch_fiber_channel(opts, chan_hene, wait_time = 3)

        wlm.SetExposure(200)
        time.sleep(1)
        wlm.Calibration(hene_freq)

        switch_fiber_channel(opts, chan_current, wait_time = None)

        return



opts = {
        'fiber_server_ip' : '192.168.42.20',
        'fiber_server_port' : 65000,
        }
   


wlm = WavelengthMeter()

#freq = 473.612512

freq = float(sys.argv[1])

calibrate_wavemeter(opts, wlm, freq, 4, 2)

	





