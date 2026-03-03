##################################
# Imports
##################################

import sys
from PyQt5.QtWidgets import QWidget, QApplication, QHBoxLayout, QVBoxLayout, QLineEdit, QSpinBox, QLabel
import socket

from simple_pid import PID
import serial
import queue
import threading

from functools import partial

class LaserLocker(QWidget):

#################################
###   Basic Initializations   ###
#################################

    def __init__(self):

        super().__init__()

        self.initOpts()
        self.initThreads()
        self.initUI()

    def initOpts(self):

        # MOD: eliminate laser server addr and port outside opts
        self.opts = {
                'arduino_com_ports': {0: 'COM5'},
                'wavemeter_server_ip': '192.168.42.20',
                'wavemeter_server_port': 62500,
                'setpoint_server_ip': '192.168.42.136',
                'setpoint_server_port': 63700,
                'pids': {
                    '422': {'laser': '422', 'Kp': 10, 'Ki': 1200, 'arduino_no': 0, 'DAC_chan': 1, 'DAC_max_output': 4095.0},
                    '390': {'laser': '390', 'Kp': -10, 'Ki': -3000, 'arduino_no': 0, 'DAC_chan': 2, 'DAC_max_output': 3250.0}},
                'lasers': [
                    {'id': '422', 'init_freq': '709.078380', 'step_size': '10'},
                    {'id': '390', 'init_freq': '766.817850', 'step_size': '10'},
                    ]
                }

        self.laser_server_addr = '192.168.42.136'
        self.laser_server_port = 63700

        self.title = 'Laser Lock'
        self.left = 0
        self.top = 0
        self.width = 400
        self.height = 290

        return

    def initThreads(self):

        # For PID monitor
        self.last_output = {'422': None, '390': None}
        self.last_pterm = {'422': None, '390': None}
        self.last_iterm = {'422': None, '390': None}

        print('Init Threads ...')
        ser = self.init_arduinos(com_ports = self.opts['arduino_com_ports'])
        sock = self.setup_setpoint_server()

        print('Init PID ...')
        self.pid_arr, init_setpoints = self.init_pid()

        q_arr = queue.Queue()

        pid_thread = threading.Thread(target=self.run_pid, args=(q_arr,ser,init_setpoints), daemon=True)
        pid_thread.start()

        setpoint_thread = threading.Thread(target=self.run_setpoint_server, args=(q_arr,sock,), daemon=True)
        setpoint_thread.start()

    def initUI(self):

        self.setWindowTitle(self.title)
        self.setGeometry(self.left, self.top, self.width, self.height)
        self.layout = QVBoxLayout()

        hbox_freq_monitor = self.init_freqMonitorUI()
        hbox_lasers = self.init_laserUI()
        vbox_PID_monitor = self.init_PIDMonitorUI()

        self.layout.addLayout(hbox_freq_monitor)
        self.layout.addLayout(hbox_lasers)
        self.layout.addLayout(vbox_PID_monitor)
        self.setLayout(self.layout)
        self.show()

################################
###   Frequency Monitor UI   ###
################################

    def init_freqMonitorUI(self):

        hbox = QHBoxLayout()

        self.freqMonitorLines = {'422': {}, '390': {}}

        for k in range(len(self.opts['lasers'])):

            laser = self.opts['lasers'][k]
            self.freqMonitorLines[laser['id']] = QLineEdit('None')
            self.freqMonitorLines[laser['id']].setReadOnly(True)

            vbox = QVBoxLayout()
            vbox.addWidget(QLabel('Act Frequency (Laser ' + str(laser['id']) + '):'))
            vbox.addWidget(self.freqMonitorLines[laser['id']])

            hbox.addLayout(vbox)

        return hbox

    def freqMonitor_update(self, laserid, freq):

        self.freqMonitorLines[laserid].setText('{:.5f}'.format(freq))

        return

####################################################
###   Laser UI and functions called by this UI   ###
####################################################

    def init_laserUI(self):

        hbox = QHBoxLayout()

        for k in range(len(self.opts['lasers'])):

            laser = self.opts['lasers'][k]

            single_step = QLineEdit(laser['step_size'])
            set_point = QLineEdit(laser['init_freq'])
            set_point.setReadOnly(True)
            laser_scan = QSpinBox()
            laser_offset = QLineEdit(laser['init_freq'])

            vbox = QVBoxLayout()

            vbox.addWidget(QLabel('Frequency Offset (THz)'))
            vbox.addWidget(laser_offset)
            vbox.addWidget(QLabel('Frequency Shift (MHz)'))
            vbox.addWidget(laser_scan)
            vbox.addWidget(QLabel('Step Size (MHz)'))
            vbox.addWidget(single_step)
            vbox.addWidget(QLabel('Frequency Set Point(THz)'))
            vbox.addWidget(set_point)

            laser_scan.valueChanged.connect(partial(self.single_step_update, single_step))
            laser_scan.valueChanged.connect(partial(self.set_point_update, laser['id'], set_point, laser_offset, laser_scan))

            laser_scan.setSuffix(' MHz')
            laser_scan.setMinimum(-100000)
            laser_scan.setMaximum(100000)
            laser_scan.setSingleStep(int(single_step.text()))

            hbox.addLayout(vbox)

        return hbox

    def single_step_update(self, single_step):

        btn = self.sender()
        btn.setSingleStep(int(single_step.text()))

        return

    def set_point_update(self, laserid, set_point, laser_offset, laser_scan):

        new_set_point = float(laser_offset.text()) + float(laser_scan.value()) * 1e-6
        self.send_setpoint(laserid, new_set_point)

        set_point.setText(str(new_set_point))

        return

    def send_setpoint(self, laserid, frequency):

        message = laserid + ',{0:.9f}'.format(float(frequency))
        
        print('Sending new setpoint for laser ' + laserid + ': {0:.6f}'.format(frequency))
        self.send_message_via_socket(message, self.opts['setpoint_server_ip'], self.opts['setpoint_server_port'])

        return

    def send_message_via_socket(self, message, addr, port):

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_address = (addr, port)

        sock.connect(server_address)
        sock.sendall(message.encode())
        sock.close()

        return

##########################
###   PID Monitor UI   ###
##########################

    def init_PIDMonitorUI(self):

        vbox = QVBoxLayout()

        self.PIDMonitorLines = {'422': {}, '390': {}}

        for k in self.opts['pids'].keys():
            pid = self.opts['pids'][k]
            self.PIDMonitorLines[k]['output'] = QLineEdit('None')
            self.PIDMonitorLines[k]['output'].setReadOnly(True)
            self.PIDMonitorLines[k]['pterm'] = QLineEdit('None')
            self.PIDMonitorLines[k]['pterm'].setReadOnly(True)
            self.PIDMonitorLines[k]['iterm'] = QLineEdit('None')
            self.PIDMonitorLines[k]['iterm'].setReadOnly(True)
            
            hbox = QHBoxLayout()
            hbox.addWidget(QLabel(str(pid['laser']) + ' Output:'))
            hbox.addWidget(self.PIDMonitorLines[k]['output'])
            hbox.addWidget(QLabel(str('P:')))
            hbox.addWidget(self.PIDMonitorLines[k]['pterm'])
            hbox.addWidget(QLabel(str('I:')))
            hbox.addWidget(self.PIDMonitorLines[k]['iterm'])

            vbox.addLayout(hbox)

        return vbox

    def PIDMonitor_update(self):

        for k in self.opts['pids'].keys():
            try:
                self.PIDMonitorLines[k]['output'].setText('{:.6f}'.format(self.last_output[k]))
                self.PIDMonitorLines[k]['iterm'].setText('{:.6f}'.format(self.last_iterm[k]))
                self.PIDMonitorLines[k]['pterm'].setText('{:.6f}'.format(self.last_pterm[k]))
            except:
                continue
                
        return


###########################
###   Get Frequencies   ###
###########################

    def get_frequencies(self):
    
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_address = (self.opts['wavemeter_server_ip'], self.opts['wavemeter_server_port'])
        sock.connect(server_address)
    
        try:
            # Send data
            message = 'request'
            sock.sendall(message.encode())
    
            len_msg = int(sock.recv(2).decode())
            data = sock.recv(len_msg)
            data = data.decode()
            output = float(data)
    
            laserid = self.process_frequency(output)
                
        finally:
            #print('closing socket')
            sock.close()
    
        return laserid, output

    def process_frequency(self, freq):

        # Frequency is for 422
        if (freq > 708) and (freq < 710):
            laser = '422'

        # Frequency is for 390
        elif (freq > 766) and (freq < 770):
            laser = '390'

        # Underexposed, overexposed or other abnormal value
        else:
            laser = 0

        return laser
        
#####################################
###   Arduino Control Functions   ###
#####################################

    def init_arduinos(self, com_ports, init_output = False):

        ser_connections = {}
        for port in com_ports.keys():
            serial_port = com_ports[port] #'COM14'; #pid lock arduino port
            baud_rate = 9600 #; #In arduino, Serial.begin(baud_rate)

            try:
                ser = serial.Serial(serial_port, baud_rate, 
                                    bytesize=serial.SEVENBITS, 
                                    parity=serial.PARITY_ODD, 
                                    stopbits=serial.STOPBITS_ONE, 
                                    timeout=1)
            except:
                try:
                    ser.close()
                except:
                    print ("Serial port already closed" )
                ser = serial.Serial(serial_port, baud_rate, 
                                    bytesize=serial.SEVENBITS, 
                                    parity=serial.PARITY_ODD, 
                                    stopbits=serial.STOPBITS_ONE, 
                                    timeout=1)
    
            if init_output:
                send_arduino_control(ser, 0.0, 1)
                send_arduino_control(ser, 0.0, 2)
    
            ser_connections[port] = ser

        #print(ser_connections)
        return ser_connections

    def send_arduino_control(self, ser, control, DAC_chan, max_output=4095.0):

        ard_mess =  int(max_output/20.0 * control + max_output/2.0) * 10 + DAC_chan
        mystr = '{:05d}'.format(ard_mess).encode('utf-8')
        ser.write(mystr)

        return

##################################
###   Setpoint Server Thread   ###
##################################

    def setup_setpoint_server(self):

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_address = (self.opts['setpoint_server_ip'], self.opts['setpoint_server_port'])
        sock.bind(server_address)
        sock.listen(1)

        return sock
        
    def run_setpoint_server(self, q_arr, sock):

        while True:
            connection, client_address = sock.accept()

            try:
                data = connection.recv(22)
                data = data.decode()
                data = data.split(',')
                data = {
                        'laserid': data[0],
                        'frequency': float(data[1]),
                        }
                
                q_arr.put(data)

            finally:
                connection.close()

######################
###   PID Thread   ###
######################

    def init_pid(self):

        act_values = {}
        pid_arr = {}
        init_setpoints = {}

        for k in self.opts['pids'].keys():

            curr_pid = self.opts['pids'][k]
            print('Initializing PID on laser ' + str(curr_pid['laser']) + ', please unblock this laser.')

            while True:

                laserid, freq = self.get_frequencies()

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

    def run_pid(self, q_arr, ser, init_setpoints):

        act_values = {}
        setpoints = init_setpoints
        last_id = '390'
        
        while True:

            try:
                var = q_arr.get(block=False)

                laser = var['laserid']
                freq = var['frequency']
                
                if laser in setpoints.keys():
                    setpoints[laser] = freq
                    print('New setpoints on laser ' + laser + ': ' + str(setpoints))

            except queue.Empty:
                pass

            laserid, act_values = self.get_frequencies()
            
            if laserid == 0:
                self.pid_arr['422'].set_auto_mode(False)
                self.pid_arr['390'].set_auto_mode(False)
            
            elif laserid == last_id:
                self.pid_arr[laserid].setpoint = float(setpoints[laserid])
                self.last_output[laserid] = self.pid_arr[laserid](act_values)
                self.last_pterm[laserid], self.last_iterm[laserid], _ = self.pid_arr[laserid].components

                self.PIDMonitor_update()
                self.freqMonitor_update(laserid, act_values)

                self.send_arduino_control(ser[self.opts['pids'][laserid]['arduino_no']], self.last_output[laserid], self.opts['pids'][laserid]['DAC_chan'], max_output=self.opts['pids'][laserid]['DAC_max_output'])

            else:
                if last_id != 0:
                    self.pid_arr[last_id].set_auto_mode(False)
                self.pid_arr[laserid].set_auto_mode(True, last_output=self.last_iterm[laserid])

                self.pid_arr[laserid].setpoint = float(setpoints[laserid])
                self.last_output[laserid] = self.pid_arr[laserid](act_values)
                self.last_pterm[laserid], self.last_iterm[laserid], _ = self.pid_arr[laserid].components

                self.PIDMonitor_update()
                self.freqMonitor_update(laserid, act_values)

                self.send_arduino_control(ser[self.opts['pids'][laserid]['arduino_no']], self.last_output[laserid], self.opts['pids'][laserid]['DAC_chan'], max_output=self.opts['pids'][laserid]['DAC_max_output'])

            last_id = laserid

        return


if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = LaserLocker()
    sys.exit(app.exec_())

