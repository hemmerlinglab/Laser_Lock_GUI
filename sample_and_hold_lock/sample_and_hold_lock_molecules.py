from base_functions import *






###################################
# main
###################################

opts = {
        'arduino_com_ports' : {0 : 'COM14', 1 : 'COM6'},
        'wavemeter_server_ip' : '192.168.42.20',
        'wavemeter_server_port' : 62500,
        'setpoint_server_ip' : '192.168.42.20',
        'setpoint_server_port' : 63700,
        'fiber_server_ip' : '192.168.42.20',
        'fiber_server_port' : 65000,
        'pids' : {
            1 : {'laser' : 391, 'wavemeter_channel' : 1, 'Kp' : -10, 'Ki' : -5000, 'arduino_no' : 0, 'DAC_chan' : 1, 'DAC_max_output' : 4095.0},
            2 : {'laser' : 398, 'wavemeter_channel' : 2, 'Kp' : -10, 'Ki' : -10000, 'arduino_no' : 0, 'DAC_chan' : 2, 'DAC_max_output' : 4095.0},
            3 : {'laser' : 1064, 'wavemeter_channel' : 3, 'Kp' : 10, 'Ki' : 100000, 'arduino_no' : 1, 'DAC_chan' : 2, 'DAC_max_output' : 4095.0},
            },
        'fiber_switcher_init_channel' : 2
        }
   


init_all(opts)


# keep deamons running
while True:
    pass




