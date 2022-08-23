from base_functions import *


###################################
# main
###################################

opts = {
        'arduino_com_port' : 'COM14',
        'wavemeter_server_ip' : '192.168.42.20',
        'wavemeter_server_port' : 62500,
        'setpoint_server_ip' : '192.168.42.136',
        'setpoint_server_port' : 63700,
        'fiber_server_ip' : '192.168.42.20',
        'fiber_server_port' : 65000,
        'pids' : {
            5 : {'laser' : 422, 'wavemeter_channel' : 5, 'Kp' : 1, 'Ki' : 500, 'DAC_chan' : 1, 'DAC_max_output' : 4095.0},
            6 : {'laser' : 390, 'wavemeter_channel' : 6, 'Kp' : -1, 'Ki' : -5000, 'DAC_chan' : 2, 'DAC_max_output' : 3250.0},
            },
        'fiber_switcher_init_channel' : 6
        }
   


init_all(opts)


# keep deamons running
while True:
    pass






