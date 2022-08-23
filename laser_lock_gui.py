##################################
# Imports
##################################

#from wlm import *

import sys
from PyQt5.QtWidgets import QLineEdit, QTabWidget, QSizePolicy, QTextEdit, QMainWindow, QApplication, QWidget, QAction, QTableWidget,QTableWidgetItem,QSpinBox,QVBoxLayout,QPushButton,QLabel,QHBoxLayout,QRadioButton,QButtonGroup
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import pyqtSlot, QTimer
import numpy as np
import scipy
import datetime
import fileinput
from scipy.interpolate import interp1d
import socket

from matplotlib.backends.qt_compat import QtCore, QtWidgets, is_pyqt5
if is_pyqt5():
    from matplotlib.backends.backend_qt5agg import (
        FigureCanvas, NavigationToolbar2QT as NavigationToolbar)
else:
    from matplotlib.backends.backend_qt4agg import (
        FigureCanvas, NavigationToolbar2QT as NavigationToolbar)
from matplotlib.figure import Figure

from sample_and_hold_lock.base_functions import switch_fiber_channel

#from simple_pid import PID



class App(QWidget):
 
    def __init__(self):
        super().__init__()
        self.title = 'Logging Plots'
        self.left = 0
        self.top = 0
        self.width = 200
        self.height = 500
        self.no_of_rows = 20
        self.set_point = 0

        self.update_interval = 100 # ms
        self.no_of_points = 100

        self.initUI()        

        self.timer = QTimer()
        self.timer.timeout.connect(self.tick)
        self.timer.start(self.update_interval)

    def tick(self):
        return

    def initUI(self):
        self.setWindowTitle(self.title)
        self.setGeometry(self.left, self.top, self.width, self.height)
 
        self.tabs = QTabWidget()

        self.tab_main = QWidget()

        self.tabs.addTab(self.tab_main, "Davos")

        self.laser_scan = QSpinBox()
        self.laser_offset = QLineEdit('')
        self.laser_set_point = QLineEdit('')
        self.single_step = QLineEdit('10')

        self.tab_main.layout = QVBoxLayout()
        self.tab_main.layout.addWidget(QLabel('Frequency Offset (THz)'))
        self.tab_main.layout.addWidget(self.laser_offset)
        self.tab_main.layout.addWidget(QLabel('Frequency Shift (MHz)'))
        self.tab_main.layout.addWidget(self.laser_scan)
        self.tab_main.layout.addWidget(QLabel('Step Size (MHz)'))
        self.tab_main.layout.addWidget(self.single_step)
        self.tab_main.layout.addWidget(QLabel('Frequency Set Point (THz)'))
        self.tab_main.layout.addWidget(self.laser_set_point)
        self.tab_main.setLayout(self.tab_main.layout)

        self.laser_scan.valueChanged.connect(self.set_point_update)
        self.laser_scan.valueChanged.connect(self.single_step_update)
               
        # properties
        self.laser_offset.text
        self.laser_scan.setSuffix(' MHz')
        self.laser_scan.setMinimum(-100000)
        self.laser_scan.setMaximum(100000)
        self.laser_scan.setSingleStep(np.int(self.single_step.text()))
        # Show widget
      
        #self.read_set_point()
### Tab 2
        self.tab_main2 = QWidget()

        self.tabs.addTab(self.tab_main2, "Hodor")

        self.laser_scan2 = QSpinBox()
        self.laser_offset2 = QLineEdit('')
        self.laser_set_point2 = QLineEdit('')
        self.single_step2 = QLineEdit('10')

        self.tab_main2.layout = QVBoxLayout()
        self.tab_main2.layout.addWidget(QLabel('Frequency Offset (THz)'))
        self.tab_main2.layout.addWidget(self.laser_offset2)
        self.tab_main2.layout.addWidget(QLabel('Frequency Shift (MHz)'))
        self.tab_main2.layout.addWidget(self.laser_scan2)
        self.tab_main2.layout.addWidget(QLabel('Step Size (MHz)'))
        self.tab_main2.layout.addWidget(self.single_step2)
        self.tab_main2.layout.addWidget(QLabel('Frequency Set Point (THz)'))
        self.tab_main2.layout.addWidget(self.laser_set_point2)
        self.tab_main2.setLayout(self.tab_main2.layout)

        ### End laser 2
               
        self.r1 = QRadioButton('1')
        self.r2 = QRadioButton('2')
        self.r3 = QRadioButton('3')
        self.r4 = QRadioButton('4')
        self.r5 = QRadioButton('5')
        self.r6 = QRadioButton('6')

        self.r1.toggled.connect(self.update_switcher)
        self.r2.toggled.connect(self.update_switcher)
        self.r3.toggled.connect(self.update_switcher)
        self.r4.toggled.connect(self.update_switcher)
        self.r5.toggled.connect(self.update_switcher)
        self.r6.toggled.connect(self.update_switcher)

        self.switcher_group = QButtonGroup()

        self.switcher_group.addButton(self.r1)
        self.switcher_group.addButton(self.r2)
        self.switcher_group.addButton(self.r3)
        self.switcher_group.addButton(self.r4)
        self.switcher_group.addButton(self.r5)
        self.switcher_group.addButton(self.r6)

        #self.tabs.addTab(self.tab_switcher, "Fiber Switch")
        
        hbox = QHBoxLayout()
        hbox.addWidget(self.r1)
        hbox.addWidget(self.r2)
        hbox.addWidget(self.r3)
        hbox.addWidget(self.r4)
        hbox.addWidget(self.r5)
        hbox.addWidget(self.r6)
        
        self.layout = QVBoxLayout()

        self.layout.addLayout(hbox) 
        
        self.layout.addWidget(self.tabs) 
        self.setLayout(self.layout) 
 
        self.laser_scan2.valueChanged.connect(self.set_point_update2)
        self.laser_scan2.valueChanged.connect(self.single_step_update2)
               
        # properties
        self.laser_offset2.text
        self.laser_scan2.setSuffix(' MHz')
        self.laser_scan2.setMinimum(-100000)
        self.laser_scan2.setMaximum(100000)
        self.laser_scan2.setSingleStep(np.int(self.single_step2.text()))
        # Show widget
      
        #self.read_set_point2()

        self.r1.toggle()

        self.opts = {
                'fiber_server_ip' : '192.168.42.20',
                'fiber_server_port' : 65000
                }

        self.show()

    def update_switcher(self, _):

        btn = self.sender()
        if btn.isChecked():
            print('Switching fiber switch to channel ... ' + str(btn.text()))            

            switch_fiber_channel(self.opts, int(btn.text()), wait_time = None)

        return

    def single_step_update(self):
        self.laser_scan.setSingleStep(np.int(self.single_step.text()))
        return

    def single_step_update2(self):
        self.laser_scan2.setSingleStep(np.int(self.single_step2.text()))
        return

    def send_setpoint(self, which_laser, frequency, do_switch = False, wait_time = 0):
        if which_laser == 'Hodor':
            channel = 2
        elif which_laser == 'Daenerys':
            channel = 3
        else:
            print('Error: No laser to set or scan')
            asd

        if do_switch:
            switch = 1
        else:
            switch = 0

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        server_address = ('192.168.42.20', 63700)

        print('Sending new setpoint for {1}: {0:.6f}'.format(frequency, which_laser))
        sock.connect(server_address)

        message = "{0:1d},{1:.9f},{2:1d},{3:3d}".format(int(channel), float(frequency), int(switch), int(wait_time))

        sock.sendall(message.encode())

        sock.close()

        return

    def set_point_update(self):
        
        self.set_point = np.float(self.laser_offset.text()) + np.float(self.laser_scan.value())*1e-6
        
        # update set point
        self.send_setpoint('Hodor', self.set_point, do_switch = False)

        self.laser_set_point.setText(str(self.set_point))

        return

    def set_point_update2(self):
        
        self.set_point2 = np.float(self.laser_offset2.text()) + np.float(self.laser_scan2.value())*1e-6
        # update set point

        self.send_setpoint('Daenerys', self.set_point2, do_switch = False)

        self.laser_set_point2.setText(str(self.set_point2))

        return

    #def read_set_point(self):
    #    
    #    # update set point
    #    #file = open("../Prehistoric-Data-Acquisition/setpoint.txt", "r")
    #    file = open("y:\\setpoint.txt", "r")
    #    self.set_point = np.float(file.readline())
    #    file.close()

    #    self.laser_set_point.setText(str(self.set_point))
    #    self.laser_offset.setText(str(self.set_point))

    #    return

    #def read_set_point2(self):
    #    
    #    # update set point
    #    #file = open("../Prehistoric-Data-Acquisition/setpoint.txt", "r")
    #    file = open("y:\\setpoint2.txt", "r")
    #    self.set_point2 = np.float(file.readline())
    #    file.close()

    #    self.laser_set_point2.setText(str(self.set_point2))
    #    self.laser_offset2.setText(str(self.set_point2))

    #    return



if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = App()
    sys.exit(app.exec_())

