##################################
# Imports
##################################

#from wlm import *

import sys
from PyQt5.QtWidgets import QLineEdit, QTabWidget, QSizePolicy, QTextEdit, QMainWindow, QApplication, QWidget, QAction, QTableWidget,QTableWidgetItem,QSpinBox,QVBoxLayout,QPushButton,QLabel,QHBoxLayout,QRadioButton,QButtonGroup,QCheckBox
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import pyqtSlot, QTimer
import numpy as np
import scipy
import datetime
import fileinput
from scipy.interpolate import interp1d
import socket

import serial
import time
from simple_pid import PID
import threading
import queue

from functools import partial

from matplotlib.backends.qt_compat import QtCore, QtWidgets, is_pyqt5
if is_pyqt5():
    from matplotlib.backends.backend_qt5agg import (
        FigureCanvas, NavigationToolbar2QT as NavigationToolbar)
else:
    from matplotlib.backends.backend_qt4agg import (
        FigureCanvas, NavigationToolbar2QT as NavigationToolbar)
from matplotlib.figure import Figure

# MOD: rename 'single_step' to 'step_size'

class LaserLocker(QWidget):

#################################
###   Basic Initializations   ###
#################################

    def __init__(self):

        self.debug_mode = False
        super().__init__()

        self.no_of_rows = 20 # MOD: maybe is not needed
        self.set_point = 0 # MOD: maybe is not needed

        self.no_of_points = 100 # MOD: maybe is not needed

        self.laser_set_points = {}
        self.laser_pids_status = {}

        # auto toggle lasers for sample and hold lock
        self.current_laser = 0
        self.channels_to_toggle_lasers = [1]

        self.initiating = True
        self.initOpts()
        self.initThreads()
        self.initUI()
        self.initiating = False

        self.timer_interval = 2000
        self.switch_wait_time = 500
        self.timer = QTimer()
        self.timer.timeout.connect(self.sample_and_lock_lasers)

    def initOpts(self):

        # MOD: eliminate laser server addr and port outside opts
        self.opts = {
                'arduino_com_ports': {0: 'COM5'},
                'wavemeter_server_ip': '192.168.42.20',
                'wavemeter_server_port': 62500,
                'setpoint_server_ip': '192.168.42.136',
                'setpoint_server_port': 63700,
                'fiber_server_ip': '192.168.42.20',
                'fiber_server_port': 65000,
                'pids': {
                    5: {'laser': 422, 'wavemeter_channel': 5, 'Kp': 1, 'Ki': 500, 'arduino_no': 0, 'DAC_chan': 1, 'DAC_max_output': 4095.0},
                    6: {'laser': 390, 'wavemeter_channel': 6, 'Kp': -1, 'Ki': -1000, 'arduino_no': 0, 'DAC_chan': 2, 'DAC_max_output': 3250.0}},
                'lasers': [
                    {'id': '422', 'init_freq': '709.078540', 'channel': 5, 'step_size': '10'},
                    {'id': '390', 'init_freq': '766.817660', 'channel': 6, 'step_size': '10'},
                    ],
                'fiber_switcher_init_channel': 6 # Mod: not sure if this is really needed, if not, delete this
                }

        self.laser_server_addr = '192.168.42.136'
        self.laser_server_port = 63700

        self.title = 'Laser Lock'
        self.left = 0
        self.top = 0
        self.width = 200
        self.height = 500

        return

    def initThreads(self):

        self.current_channel = self.opts['fiber_switcher_init_channel']
        self.last_output = {} # Last total output of PID
        self.last_pterm = {}
        self.last_iterm = {} # Last Ki term of PID

        print('Init Threads ...')
        ser = self.init_arduinos(com_ports = self.opts['arduino_com_ports'])
        sock = self.setup_setpoint_server()

        print('Init PID ...')
        self.pid_arr, init_setpoints = self.init_pid()

        self.switch_fiber_channel(self.opts['fiber_switcher_init_channel'], wait_time = 1)
        q_arr = queue.Queue()

        pid_thread = threading.Thread(target=self.run_pid, args=(q_arr,ser,init_setpoints,self.opts), daemon=True)
        pid_thread.start()

        setpoint_thread = threading.Thread(target=self.run_setpoint_server, args=(q_arr,sock,), daemon=True)
        setpoint_thread.start()

        return


    def initUI(self):

        self.setWindowTitle(self.title)
        self.setGeometry(self.left, self.top, self.width, self.height)

        hbox_fiber_switcher = self.init_switcherUI()
        hbox_lasers = self.init_laserUI()
        vbox_sample_and_hold = self.initUI_sample_and_hold()
        vbox_PID_monitor = self.init_PIDMonitorUI()

        self.layout.addLayout(vbox_sample_and_hold)
        self.layout.addLayout(hbox_fiber_switcher)
        self.layout.addLayout(hbox_lasers)
        self.layout.addLayout(vbox_PID_monitor)
        self.setLayout(self.layout)
        self.show()

#######################################
###   Sample and hold lock lasers   ###
#######################################

    def sample_and_lock_lasers(self):

        which_channel = self.channels_to_toggle_lasers[self.current_laser]
        set_point_widget = self.laser_set_points[str(which_channel)]
        new_setpoint = float(set_point_widget.text())

        self.send_setpoint(which_channel, new_setpoint, do_switch=True, wait_time = self.switch_wait_time)

        self.current_laser = (self.current_laser + 1) % len(self.channels_to_toggle_lasers)

        return

#############################################################
###   Sample and hold UI and function called by this UI   ###
#############################################################

    def initUI_sample_and_hold(self):

        self.layout = QVBoxLayout() # MOD: Why this is here instead of in initUI()?
        vbox = QVBoxLayout()

        self.switch_sample_and_hold = QPushButton('Switch on Sample and Hold')
        self.switch_sample_and_hold.setCheckable(True)
        self.switch_sample_and_hold.clicked.connect(self.do_sample_and_hold)
        
        self.timer_sample_and_hold = QLineEdit('2000')
        self.timer_sample_and_hold.textChanged.connect(self.update_timer)

        vbox.addWidget(self.switch_sample_and_hold)

        hbox = QHBoxLayout()
        hbox.addWidget(QLabel('Timer (ms):'))
        hbox.addWidget(self.timer_sample_and_hold)

        self.sampler_channels = []
        for k in range(6):
            hlp = QCheckBox(str(k+1))
            hlp.toggled.connect(self.update_sampling_channels)
            hbox.addWidget(hlp)
            self.sampler_channels.append(hlp)

        vbox.addLayout(hbox)

        return vbox

    def do_sample_and_hold(self, pressed):

        if pressed:
            print('Switching on sample and hold ...')
            self.timer.start(self.timer_interval)
            hlp = self.sender()
            hlp.setStyleSheet('QPushButton:checked {background-color: red;}')

        else:
            print('Switching off sample and hold')
            self.timer.stop()

    def update_timer(self):

        hlp = self.sender()
        self.timer_interval = int(hlp.text())
        self.restart_timer()

        return

    def update_sampling_channels(self):

        self.channels_to_toggle_lasers = []
        for ch in range(len(self.sampler_channels)):
            if self.sampler_channels[ch].isChecked():
                self.channels_to_toggle_lasers.append(ch+1)

        self.restart_timer()

        return

    def restart_timer(self):

        if self.timer.isActive():
            self.timer.stop()
            self.timer.start(self.timer_interval)

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

            hlp = QHBoxLayout()
            hlp.addWidget(QLabel('Laser: '+ str(laser['id'])))
            hlp.addWidget(QLabel('channel: ' + str(laser['channel'])))
            hlp.addWidget(QLabel('PID on?'))
            self.laser_pids_status[str(laser['channel'])] = QCheckBox()
            hlp.addWidget(self.laser_pids_status[str(laser['channel'])])

            vbox.addLayout(hlp)
            vbox.addWidget(QLabel('Frequency Offset (THz)'))
            vbox.addWidget(laser_offset)
            vbox.addWidget(QLabel('Frequency Shift (MHz)'))
            vbox.addWidget(laser_scan)
            vbox.addWidget(QLabel('Step Size (MHz)'))
            vbox.addWidget(single_step)
            vbox.addWidget(QLabel('Frequency Set Point(THz)'))
            vbox.addWidget(set_point)

            self.laser_set_points[str(laser['channel'])] = set_point

            laser_scan.valueChanged.connect(partial(self.single_step_update, single_step))
            laser_scan.valueChanged.connect(partial(self.set_point_update, laser['channel'], set_point, laser_offset, laser_scan))

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

    def set_point_update(self, which_channel, set_point, laser_offset, laser_scan):

        new_set_point = float(laser_offset.text()) + float(laser_scan.value()) * 1e-6

        if not self.switch_sample_and_hold.isChecked():
            self.send_setpoint(which_channel, new_set_point, do_switch = False)

        set_point.setText(str(new_set_point))

        return

    def send_setpoint(self, channel, frequency, do_switch = False, wait_time = 0):

        if do_switch:
            self.switch_fiber_channel(channel, wait_time=1)
#            switch = 1
#        else:
#            switch = 0
        switch = 0

        message = '{0:1d},{1:.9f},{2:1d},{3:3d}'.format(int(channel), float(frequency), int(switch), int(wait_time-1))
        
        print('Sending new setpoint for channel {1}: {0:.6f}'.format(frequency, channel))
        self.send_message_via_socket(message, self.laser_server_addr, self.laser_server_port)

        return

    def send_message_via_socket(self, message, addr, port):

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_address = (addr, port)

        sock.connect(server_address)
        sock.sendall(message.encode())
        sock.close()

        return

#######################################################
###   Switcher UI and functions called by this UI   ###
#######################################################

    def init_switcherUI(self, no_of_switcher_channels = 8):

        btn = []
        self.switcher_group = QButtonGroup()
        hbox = QHBoxLayout()
        hbox.addWidget(QLabel('Fiber Switcher'))

        for k in range(no_of_switcher_channels):
            btn = QRadioButton(str(k+1))
            
            if k == 5:
                btn.toggle()

            btn.toggled.connect(self.update_switcher)

            self.switcher_group.addButton(btn)
            hbox.addWidget(btn)

        return hbox

    def update_switcher(self, _):

        btn = self.sender()
        if btn.isChecked() and not self.debug_mode:
            print('Switching fiber switch to channel ...' + str(btn.text()))
            self.switch_fiber_channel(int(btn.text()), wait_time=1)

        return

##########################
###   PID Monitor UI   ###
##########################

    def init_PIDMonitorUI(self):

        vbox = QVBoxLayout()

        self.PIDMonitorLines = {5: {}, 6: {}}

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
            #print('sending "%s"' % message)
            sock.sendall(message.encode())

            len_msg = int(sock.recv(2).decode())
            data = sock.recv(len_msg)
            data = data.decode()
            output = float(data)

        finally:
            #print('closing socket')
            sock.close()

        return output

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

    def send_arduino_control(self, ser, control, channel, max_output=4095.0):

        ard_mess =  int(max_output/20.0 * control + max_output/2.0)*10 + channel
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

    def switch_fiber_channel(self, channel, wait_time=None):

        if not self.initiating:
            self.pid_arr[self.current_channel].set_auto_mode(False)
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_address = (self.opts['fiber_server_ip'], self.opts['fiber_server_port'])
        print('Switching fiber channel on {0} port {1} to channel {2}'.format(server_address[0], server_address[1], channel))
        sock.connect(server_address)
        sock.sendall(str(channel).encode())
        sock.close()

        print('sleeping for {}s, the PID is now disabled'.format(wait_time))
        time.sleep(1)
        print('Resuming PID')

        if not self.initiating:
            self.current_channel = channel
            # Notice that the last_output argument of the set_auto_mode() method sets the Ki term of the pid, instead of the total output to this value.
            self.pid_arr[self.current_channel].set_auto_mode(True, last_output=self.last_iterm[self.current_channel])

        try:
            time.sleep(wait_time-1)
        except:
            print('Wait time should be at least 1s!')

        return
        
    def run_setpoint_server(self, q_arr, sock):

        while True:
            connection, client_address = sock.accept()

            try:
                data = connection.recv(22)
                data = data.decode()
                data = data.split(',')
                data = {
                        'channel': int(data[0]),
                        'frequency': float(data[1]),
                        'switch_channel': int(data[2]),
                        'wait_time': int(data[3])
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

            self.switch_fiber_channel(curr_pid['wavemeter_channel'], wait_time = 1) 

            act_values[curr_pid['wavemeter_channel']] = self.get_frequencies()
            setpoint = act_values[curr_pid['wavemeter_channel']]
            init_setpoints[curr_pid['wavemeter_channel']] = setpoint

            pid = PID(curr_pid['Kp'], curr_pid['Ki'], 0.0, setpoint, sample_time = 0.001, output_limits = [-10, 10])
            pid_arr[curr_pid['wavemeter_channel']] = pid

        return pid_arr, init_setpoints

    def run_pid(self, q_arr, ser, init_setpoints, opts):

        act_values = {}
        setpoints = init_setpoints
        
        while True:

            try:
                var = q_arr.get(block=False)

                chan = var['channel']
                freq = var['frequency']
                switch_channel = var['switch_channel']
                wait_time = var['wait_time']
                # At least 1s wait time
                wait_time = max(wait_time, 1000)

                if switch_channel == 1:
                    self.switch_fiber_channel(chan, wait_time=wait_time/1000)

                if chan in setpoints.keys():
                    setpoints[chan] = freq
                    print()
                    print('New setpoints ... ' + str(setpoints))

            except queue.Empty:
                pass

            for c in self.pid_arr.keys():

                if (setpoints[c] > 0) and (self.pid_arr[c].auto_mode == True):

                    self.pid_arr[c].setpoint = float(setpoints[c])
                    act_values = self.get_frequencies()

                    # debug
#                    print('act_freq:', act_values)

                    self.last_output[c] = self.pid_arr[c](act_values)
                    self.last_pterm[c], self.last_iterm[c], _ = self.pid_arr[c].components
                    if not self.initiating:
                        self.PIDMonitor_update()

                    self.send_arduino_control(ser[opts['pids'][c]['arduino_no']], self.last_output[c], opts['pids'][c]['DAC_chan'], max_output=opts['pids'][c]['DAC_max_output'])

                elif (setpoints[c] <= 0) and (self.pid_arr[c].auto_mode == True):
                    self.last_output[c] = 0.0
                    self.last_iterm[c] = 0.0

        return


if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = LaserLocker()
    sys.exit(app.exec_())

