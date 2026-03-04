import sys
from PyQt5.QtWidgets import QWidget, QApplication, QHBoxLayout, QVBoxLayout, QLineEdit, QSpinBox, QLabel

#from functools import partial

class GUI(QWidget):

    def __init__(self):

        super().__init__()
        self.initOpts()
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
                    5: {'laser': 422, 'wavemeter_channel': 5, 'Kp': 10, 'Ki': 1200, 'arduino_no': 0, 'DAC_chan': 1, 'DAC_max_output': 4095.0},
                    6: {'laser': 390, 'wavemeter_channel': 6, 'Kp': -10, 'Ki': -3000, 'arduino_no': 0, 'DAC_chan': 2, 'DAC_max_output': 3250.0}},
                'lasers': [
                    {'id': '422', 'init_freq': '709.078380', 'channel': 5, 'step_size': '10'},
                    {'id': '390', 'init_freq': '766.817850', 'channel': 6, 'step_size': '10'},
                    ],
                'fiber_switcher_init_channel': 6 # Mod: not sure if this is really needed, if not, delete this
                }

        self.laser_server_addr = '192.168.42.136'
        self.laser_server_port = 63700

        self.title = 'Laser Lock'
        self.left = 0
        self.top = 0
        self.width = 400
        self.height = 290

        return

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

            #self.laser_set_points[str(laser['channel'])] = set_point

            #laser_scan.valueChanged.connect(partial(self.single_step_update, single_step))
            #laser_scan.valueChanged.connect(partial(self.set_point_update, laser['channel'], set_point, laser_offset, laser_scan))

            laser_scan.setSuffix(' MHz')
            laser_scan.setMinimum(-100000)
            laser_scan.setMaximum(100000)
            laser_scan.setSingleStep(int(single_step.text()))

            hbox.addLayout(vbox)

        return hbox

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

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = GUI()
    sys.exit(app.exec_())
