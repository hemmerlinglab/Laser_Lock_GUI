from base_functions import *



def send_setpoint(channel, frequency, do_switch = False, wait_time = 0, addr = '192.168.42.20', port = 63700):

        if do_switch:
            switch = 1
        else:
            switch = 0

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        server_address = (addr, port)

        print('Sending new setpoint for channel {1}: {0:.6f}'.format(frequency, channel))
        sock.connect(server_address)

        message = "{0:1d},{1:.9f},{2:1d},{3:3d}".format(int(channel), float(frequency), int(switch), int(wait_time))
        print(message)

        sock.sendall(message.encode())

        sock.close()

        return




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
        'fiber_switcher_init_channel' : 1
        }
   


init_all(opts)



chan_davos = 1
chan_daenerys = 3
freq_davos = 391.016055
freq_daenerys = 286.58281



while True:

    # switch to Davos and relock
    send_setpoint(chan_davos, freq_davos, do_switch = True, wait_time = 500)
    
    # wait
    time.sleep(2)

    send_setpoint(chan_daenerys, freq_daenerys, do_switch = True, wait_time = 500)

    # wait
    time.sleep(2)

   


# keep deamons running
while True:
    pass




