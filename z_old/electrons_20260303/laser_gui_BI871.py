##################################
# Imports
##################################

import sys
import json
import os
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QWidget, QApplication, QHBoxLayout, QVBoxLayout, QLineEdit, QSpinBox, QLabel
import socket
from bristol_instruments import BI871

from simple_pid import PID
import serial
import queue
import threading
import time

from functools import partial

class LaserLocker(QWidget):

#################################
###   Basic Initializations   ###
#################################

    setpoint_changed = pyqtSignal(str, float)
    freq_changed = pyqtSignal(str, float)
    pid_changed = pyqtSignal(str, float, float, float)

    def __init__(self):

        super().__init__()

        self.initOpts()
        self.initUI()
        self.initSignals()
        self.initThreads()

    def initOpts(self):

        # MOD: eliminate laser server addr and port outside opts
        self.opts = {
                'arduino_com_ports': {0: 'COM5'},
                'wavemeter_ip': '192.168.42.168',
                'wavemeter_port': 23,
                'setpoint_server_ip': '192.168.42.26',
                'setpoint_server_port': 63700,
                'pids': {
                    '422': {'laser': '422', 'Kp': 10, 'Ki': 1200, 'arduino_no': 0, 'DAC_chan': 1, 'DAC_max_output': 4095.0},
                    '390': {'laser': '390', 'Kp': -10, 'Ki': -3000, 'arduino_no': 0, 'DAC_chan': 2, 'DAC_max_output': 3250.0}},
                'lasers': [
                    {'id': '422', 'init_freq': '709.078380', 'step_size': '10'},
                    {'id': '390', 'init_freq': '766.817850', 'step_size': '10'},
                    ],
                'last_pid_status': 'laserlock_last_pid_state.json'
                }

        self.title = 'Laser Lock'
        self.left = 0
        self.top = 0
        self.width = 400
        self.height = 290

        return

    def initSignals(self):

        self.setpoint_changed.connect(self._on_setpoint_changed)
        self.freq_changed.connect(self._on_freq_changed)
        self.pid_changed.connect(self._on_pid_changed)

        return

    def initThreads(self):

        # For PID monitor
        self.last_output = {'422': 0.0, '390': 0.0}
        self.last_pterm = {'422': None, '390': None}
        self.last_iterm = {'422': None, '390': None}

        # Calculate last status of PID from previous run to suppress initial frequency jump
        # Init this early to make sure it is available
        self.state_path = os.path.join(os.path.dirname(__file__), self.opts['last_pid_status'])
        try:
            with open(self.state_path, 'r', encoding='utf-8') as f:
                saved = json.load(f)
                for k in saved:
                    self.last_output[k] = float(saved[k])
        except Exception as e:
            pass

        # For Frequency monitor
        self.last_freq = {'422': None, '390': None}
        self.freq_lock = threading.Lock()

        print('Init Threads ...')
        self.serial_connections = self.init_arduinos(com_ports = self.opts['arduino_com_ports'])
        self.sock = self.setup_setpoint_server()

        print('Init Wavemeter ...')
        self.wlm_lock = threading.Lock()
        self.wavemeter = BI871(self.opts['wavemeter_ip'], self.opts['wavemeter_port'])

        print('Init PID ...')
        # Initialize PID
        self.pid_arr, init_setpoints = self.init_pid()
        for laserid, setpoint in init_setpoints.items():
            self.setpoint_changed.emit(laserid, setpoint)
        self.running = True

        q_arr = queue.Queue()

        pid_thread = threading.Thread(target=self.run_pid, args=(q_arr,self.serial_connections,init_setpoints), daemon=True)
        pid_thread.start()

        setpoint_thread = threading.Thread(target=self.run_setpoint_server, args=(q_arr,self.sock,), daemon=True)
        setpoint_thread.start()

    def initUI(self):

        # For recovering offset values when user made illegal inputs
        self.last_offset = {'422': None, '390': None}

        self.setWindowTitle(self.title)
        self.setGeometry(self.left, self.top, self.width, self.height)
        self.layout = QVBoxLayout()

        hbox_freq_monitor = self.init_FreqMonitorUI()
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

    def init_FreqMonitorUI(self):

        hbox = QHBoxLayout()

        self.FreqMonitorLines = {}

        for k in range(len(self.opts['lasers'])):

            laser = self.opts['lasers'][k]
            self.FreqMonitorLines[laser['id']] = QLineEdit('None')
            self.FreqMonitorLines[laser['id']].setReadOnly(True)

            vbox = QVBoxLayout()
            vbox.addWidget(QLabel('Act Frequency (Laser ' + str(laser['id']) + '):'))
            vbox.addWidget(self.FreqMonitorLines[laser['id']])

            hbox.addLayout(vbox)

        return hbox

    def _on_freq_changed(self, laserid, freq):
        try:
            self.FreqMonitorLines[laserid].setText(f'{freq:.6f}')
        except KeyError:
            pass

####################################################
###   Laser UI and functions called by this UI   ###
####################################################
# TCP Logic for in this part is for sending the remote client any
# manual update on setpoints from the GUI side. Not removable!

    def init_laserUI(self):

        hbox = QHBoxLayout()
        self.SetPointLines = {}

        for k in range(len(self.opts['lasers'])):

            laser = self.opts['lasers'][k]

            single_step = QLineEdit(laser['step_size'])
            set_point = QLineEdit(laser['init_freq'])
            set_point.setReadOnly(True)
            laser_scan = QSpinBox()
            laser_offset = QLineEdit(laser['init_freq'])

            # Record initial offset value for each laser
            self.last_offset[laser['id']] = float(laser['init_freq'])

            self.SetPointLines[laser['id']] = set_point

            vbox = QVBoxLayout()

            vbox.addWidget(QLabel('Frequency Offset (THz)'))
            vbox.addWidget(laser_offset)
            vbox.addWidget(QLabel('Frequency Shift (MHz)'))
            vbox.addWidget(laser_scan)
            vbox.addWidget(QLabel('Step Size (MHz)'))
            vbox.addWidget(single_step)
            vbox.addWidget(QLabel('Frequency Set Point(THz)'))
            vbox.addWidget(set_point)

            # Connecting modification on boxes to correct logic
            single_step.editingFinished.connect(partial(self.apply_single_step, laser_scan, single_step))
            laser_offset.editingFinished.connect(partial(self.apply_offset, laser['id'], laser_offset, laser_scan))
            laser_scan.valueChanged.connect(partial(self.set_point_update, laser['id'], laser_offset, laser_scan))

            laser_scan.setSuffix(' MHz')
            laser_scan.setMinimum(-100000)
            laser_scan.setMaximum(100000)
            laser_scan.setSingleStep(int(single_step.text()))

            hbox.addLayout(vbox)

        return hbox

    def apply_single_step(self, spin: QSpinBox, step_line: QLineEdit):

        try:
            v = int(step_line.text())
            if v <= 0: v = 1
        except ValueError:
            v = 10

        if step_line.text() != str(v):
            step_line.setText(str(v))
        spin.setSingleStep(v)

        return

    def apply_offset(self, laserid, laser_offset, laser_scan):

        try:
            offset = float(laser_offset.text())
            self.last_offset[laserid] = offset
            formatted_text = f'{offset:.6f}'
            if formatted_text != laser_offset.text():
                laser_offset.setText(formatted_text)
        except ValueError:
            laser_offset.setText(f"{self.last_offset[laserid]:.6f}")
            return

        self.set_point_update(laserid, laser_offset, laser_scan)

        return

    def _on_setpoint_changed(self, laserid, value):
        """
        Update setpoint monitor when setpoint was changed by remote
        """
        try:
            self.SetPointLines[laserid].setText(f"{value:.6f}")
        except KeyError:
            pass

    def set_point_update(self, laserid, laser_offset, laser_scan):

        new_setpoint = float(laser_offset.text()) + float(laser_scan.value()) * 1e-6
        self.send_setpoint(laserid, new_setpoint)

        return

    def send_setpoint(self, laserid, frequency):

        message = f'{laserid},{frequency:.9f}\n'
        print(f'[local_setpoint_client] Sending new setpoint for laser {laserid}: {frequency:.6f}')
        self.send_message_via_socket(message, self.opts['setpoint_server_ip'], self.opts['setpoint_server_port'])

        return

    def send_message_via_socket(self, message, addr, port):

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_address = (addr, port)

        try:
            # Connect to server
            sock.settimeout(1.0)
            sock.connect(server_address)
            sock.sendall(message.encode('utf-8'))
            
            try:
                # Get reply from server
                sock.settimeout(0.5)
                with sock.makefile('r', encoding='utf-8', newline='') as rf:
                    line = rf.readline()
                    if line:
                        resp = line.rstrip('\r\n')
                        if resp == '1':
                            print('[local_setpoint_client] setpoint is accepted by server.')
                        elif resp == '0':
                            print('[local_setpoint_client] setpoint update failed on server side.')
                        else:
                            print(f'[local_setpoint_client] server says: {resp}')
                    else: pass

            except socket.timeout:
                print('[local_setpoint_client] timeout while waiting for reply from server (possibly due to the remote client is taking control on the server)')
            except OSError as e:
                print('[local_setpoint_client] received error: {e}')

        except ConnectionRefusedError as e:
            print('[local_setpoint_client] connection refused: server is not listening ({e})')
        except socket.timeout:
            print('[local_setpoint_client] timeout while connection to the server (possibly due to the remote client is taking control on the server)')
        except OSError as e:
            print(f'[local_setpoint_client] socket error: {e}')
        finally:
            try: sock.close()
            except Exception: pass

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

    def _on_pid_changed(self, laserid, out, p, i):
        try:
            self.PIDMonitorLines[laserid]['output'].setText(f'{out:.6f}')
            self.PIDMonitorLines[laserid]['pterm'].setText(f'{p:.6f}')
            self.PIDMonitorLines[laserid]['iterm'].setText(f'{i:.6f}')
        except KeyError:
            pass

###########################
###   Get Frequencies   ###
###########################

    def get_frequencies(self):
    
        # Try to read laser frequency with BI871 wavemeter
        try:
            with self.wlm_lock:
                freq = self.wavemeter.get_frequency()
            laserid = self.process_frequency(freq)
            return laserid, freq
    
        # Handle the case the wavemeter is unexpectedly disconnected
        except (EOFError, OSError, ConnectionResetError, BrokenPipeError):
            print("Wavemeter disconnected, reconnecting ...")
            ok = self.wavemeter.reconnect()
            if ok:
                print("Reconnected!")
                return 0, 0
            else:
                raise

        # Handle RuntimeError
        except RuntimeError as e:
            print(e)
            return 0, 0

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

    def init_arduinos(self, com_ports, init_output = True):

        ser_connections = {}
        for port in com_ports.keys():
            serial_port = com_ports[port] #'COM14'; #pid lock arduino port
            baud_rate = 9600 #; #In arduino, Serial.begin(baud_rate)

            try:
                ser = serial.Serial()
                ser.port = serial_port
                ser.baudrate = baud_rate
                ser.bytesize = serial.SEVENBITS
                ser.parity = serial.PARITY_ODD
                ser.stopbits=serial.STOPBITS_ONE
                ser.timout=1

                # To avoid large frequency jump at program initialization
                ser.dtr = False
                
            except:
                try:
                    ser.close()
                except:
                    print ("Serial port already closed" )
                ser = serial.Serial()
                ser.port = serial_port
                ser.baudrate = baud_rate
                ser.bytesize = serial.SEVENBITS
                ser.parity = serial.PARITY_ODD
                ser.stopbits=serial.STOPBITS_ONE
                ser.timout=1
                
                # To avoid large frequency jump at program initialization
                ser.dtr = False

            ser.open()

            if init_output:
                time.sleep(0.2)
                self.send_arduino_control(ser, self.last_output['422'], 1, max_output=4095.0)
                self.send_arduino_control(ser, self.last_output['390'], 2, max_output=3250.0)
    
            ser_connections[port] = ser

        #print(ser_connections)
        return ser_connections

    def send_arduino_control(self, ser, control, DAC_chan, max_output=4095.0):

        #print(f"DAC_chan = {DAC_chan}, control = {control}")
        #time.sleep(0.05)
        ard_mess =  int(max_output/20.0 * control + max_output/2.0) * 10 + DAC_chan
        mystr = '{:05d}'.format(ard_mess).encode('utf-8')
        ser.write(mystr)

        return

##################################
###   Setpoint Server Thread   ###
##################################

    def setup_setpoint_server(self):

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # To make exit-restart safer
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_address = (self.opts['setpoint_server_ip'], self.opts['setpoint_server_port'])
        sock.bind(server_address)
        sock.listen(1)

        return sock
        
    def run_setpoint_server(self, q_arr, sock):

        while True:
            try:
                connection, client_address = sock.accept()
            except OSError as e:
                print(f"[setpoint_server] accept() error: {e}")
                continue

            print(f"[setpoint_server] connection from {client_address}")

            try:
                # Filewrapper for achieving convenient line I/O
                with connection.makefile('r', encoding='utf-8',newline='') as rf:
                    while True:
                        try:
                            line = rf.readline()
                            if not line: break
                            msg = line.rstrip('\r\n')

                            # Expected message formats:
                            # Setpoint Update: "422,709.078240\n"
                            # Act Freq Request: "422,?\n"
                            # Setpoint Request: "422,set?\n"
                            # Response for Setpoint Update: 0=Fail, 1=Success
                            # Response for Freq Req: "422,709.078380\n"

                            try:
                                laserid, arg = msg.split(',', 1)
                            except ValueError:
                                connection.sendall(b'0\n')
                                continue

                            # Actual Frequency Request
                            if arg == '?':
                                with self.freq_lock:
                                    val = self.last_freq.get(laserid)
                                if val is None:
                                    connection.sendall(b'0\n')
                                else:
                                    connection.sendall(f"{laserid},{val:.6f}\n".encode('utf-8'))

                            # Setpoint Request
                            elif arg == 'set?':
                                val = self.pid_arr[laserid].setpoint
                                connection.sendall(f"{laserid},{val:.6f}\n".encode('utf-8'))

                            # Setpoint Update
                            else:
                                try:
                                    freq = float(arg)
                                except ValueError:
                                    connection.sendall(b'0\n')
                                    continue
                                q_arr.put({'laserid': laserid, 'frequency': freq})
                                connection.sendall(b'1\n')

                        except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError) as e:
                            print(f"[setpoint_server] client {client_address} disconnected")
                            break
                        except OSError as e:
                            print(f"[setpoint_server] socket I/O error {e}")
                            break

            finally:
                try: connection.close()
                except Exception: pass

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

            seed = self.last_output.get(curr_pid['laser'], 0.0)
            print(f"current laser: {curr_pid['laser']}, seed: {seed}")
            pid = PID(curr_pid['Kp'], curr_pid['Ki'], 0.0, setpoint, sample_time = 0.001, output_limits = [-10, 10], starting_output=seed)
            #pid.set_auto_mode(True, last_output=seed)

            pid_arr[curr_pid['laser']] = pid

        return pid_arr, init_setpoints

    def run_pid(self, q_arr, ser, init_setpoints):

        setpoints = init_setpoints
        last_id = '390'

        while self.running:

            try:
                var = q_arr.get(block=False)

                laser = var['laserid']
                freq = var['frequency']
                
                if laser in setpoints.keys():
                    setpoints[laser] = freq
                    print(f'[PID_thread] New setpoints on laser {laser}: {setpoints[laser]:.6f} implemented.')

                    self.setpoint_changed.emit(laser, freq)

            except queue.Empty:
                pass

            laserid, act_freq = self.get_frequencies()
            if laserid in ('422', '390'):
                with self.freq_lock:
                    self.last_freq[laserid] = act_freq
            
            if laserid == 0:
                self.pid_arr['422'].set_auto_mode(False)
                self.pid_arr['390'].set_auto_mode(False)
            
            elif laserid == last_id:
                self.pid_arr[laserid].setpoint = float(setpoints[laserid])
                self.last_output[laserid] = self.pid_arr[laserid](act_freq)
                self.last_pterm[laserid], self.last_iterm[laserid], _ = self.pid_arr[laserid].components

                self.pid_changed.emit(laserid, self.last_output[laserid], self.last_pterm[laserid], self.last_iterm[laserid])
                self.freq_changed.emit(laserid, act_freq)

                self.send_arduino_control(ser[self.opts['pids'][laserid]['arduino_no']], self.last_output[laserid], self.opts['pids'][laserid]['DAC_chan'], max_output=self.opts['pids'][laserid]['DAC_max_output'])

            else:
                if last_id != 0:
                    self.pid_arr[last_id].set_auto_mode(False)
                self.pid_arr[laserid].set_auto_mode(True, last_output=self.last_output[laserid])

                self.pid_arr[laserid].setpoint = float(setpoints[laserid])
                self.last_output[laserid] = self.pid_arr[laserid](act_freq)
                self.last_pterm[laserid], self.last_iterm[laserid], _ = self.pid_arr[laserid].components

                self.pid_changed.emit(laserid, self.last_output[laserid], self.last_pterm[laserid], self.last_iterm[laserid])
                self.freq_changed.emit(laserid, act_freq)

                self.send_arduino_control(ser[self.opts['pids'][laserid]['arduino_no']], self.last_output[laserid], self.opts['pids'][laserid]['DAC_chan'], max_output=self.opts['pids'][laserid]['DAC_max_output'])

            last_id = laserid

        return
    
    def closeEvent(self, event):

        # Stop the PID thread
        self.running = False
        time.sleep(0.1)

        # Stop the serial connection with Arduino
        try:
            for ser in self.serial_connections:
                try: ser.close()
                except Exception: pass
        except Exception:
            pass

        # Stop the setpoint server
        #try: self.sock.close()
        #except Exception: pass

        # save current PID status
        try:
            with open(self.state_path, 'w', encoding='utf-8') as f:
                json.dump(self.last_output, f)
        except Exception: pass

        # close the wavemeter
        try: self.wavemeter.close()
        except Exception: pass

        # close the UI
        super().closeEvent(event)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = LaserLocker()
    sys.exit(app.exec_())

