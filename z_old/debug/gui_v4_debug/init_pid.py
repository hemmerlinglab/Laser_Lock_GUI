import socket
from simple_pid import PID
import time

opts = {
                'arduino_com_ports': {0: 'COM5'},
                'wavemeter_server_ip': '192.168.42.20',
                'wavemeter_server_port': 62500,
                'setpoint_server_ip': '192.168.42.136',
                'setpoint_server_port': 63700,
                'fiber_server_ip': '192.168.42.20',
                'fiber_server_port': 65000,
                'pids': {
                    5: {'laser': '422', 'wavemeter_channel': 5, 'Kp': 10, 'Ki': 1200, 'arduino_no': 0, 'DAC_chan': 1, 'DAC_max_output': 4095.0},
                    6: {'laser': '390', 'wavemeter_channel': 6, 'Kp': -10, 'Ki': -3000, 'arduino_no': 0, 'DAC_chan': 2, 'DAC_max_output': 3250.0}},
                'lasers': [
                    {'id': '422', 'init_freq': '709.078680', 'channel': 5, 'step_size': '10'},
                    {'id': '390', 'init_freq': '766.817850', 'channel': 6, 'step_size': '10'},
                    ],
                'fiber_switcher_init_channel': 6 # Mod: not sure if this is really needed, if not, delete this
                }


def get_frequencies():

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_address = (opts['wavemeter_server_ip'], opts['wavemeter_server_port'])
    sock.connect(server_address)

    try:
        # Send data
        message = 'request'
        #print('sending "%s"' % message)
        sock.sendall(message.encode())

        len_msg = int(sock.recv(2).decode())
        data = sock.recv(len_msg)
        data = data.decode()
        output = float(data)

        laserid = process_frequency(output)

    finally:
        #print('closing socket')
        sock.close()

    return laserid, output

def process_frequency(freq):

    # Frequency is for 422
    if (freq > 708) and (freq < 710):
        laserid = '422'

    # Frequency is for 390
    elif (freq > 766) and (freq < 770):
        laserid = '390'

    # Underexposed, overexposed or other abnormal value
    else:
        laserid = 0

    return laserid


def init_pid():

    act_values = {}
    pid_arr = {}
    init_setpoints = {}

#    while True:
#        
#        laserid, freq = get_frequencies()
#
#        for k in opts['pids'].keys():
#            
#            curr_pid = opts['pids'][k]
#
#            if laserid == curr_pid['laser']:
#                act_values[curr_pid['laser']] = freq
#                setpoint = act_values[curr_pid['laser']]
#                init_setpoints[curr_pid['laser']] = setpoint
#                print('PID on channel ' + str(laserid) + ' initialized! Initial setpoint: ' + str(setpoint))
#                break
#
#            else:
#                continue
#
#        pid = PID(curr_pid['Kp'], curr_pid['Ki'], 0.0, setpoint, sample_time = 0.001, output_limits = [-10, 10])
#        pid_arr[curr_pid['wavemeter_channel']] = pid
#

    for k in opts['pids'].keys():

        curr_pid = opts['pids'][k]
        print('Initializing PID on laser ' + str(curr_pid['laser']) + ', please unblock this laser.')

        while True:

            laserid, freq = get_frequencies()

            if laserid == curr_pid['laser']:
                act_values[curr_pid['laser']] = freq
                setpoint = act_values[curr_pid['laser']]
                init_setpoints[curr_pid['laser']] = setpoint
                print('PID on laser ' + str(laserid) + ' initialized! Initial setpoint: ' + str(setpoint))
                break

            else:
                continue

        pid = PID(curr_pid['Kp'], curr_pid['Ki'], 0.0, setpoint, sample_time = 0.001, output_limits = [-10, 10])
        pid_arr[curr_pid['laser']] = pid

    return pid_arr, init_setpoints

if __name__ == '__main__':

#    while True:
#        chan, freq = get_frequencies()
#        print('channel: ' + str(chan) + ', frequency: ' + str(freq))
#        time.sleep(0.5)

    pids, sets = init_pid()
    print(pids)
    print(sets)
