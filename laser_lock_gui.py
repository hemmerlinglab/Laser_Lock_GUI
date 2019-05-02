##################################
# Imports
##################################

#from wlm import *

import sys
from PyQt5.QtWidgets import QLineEdit, QTabWidget, QSizePolicy, QTextEdit, QMainWindow, QApplication, QWidget, QAction, QTableWidget,QTableWidgetItem,QSpinBox,QVBoxLayout,QPushButton, QHBoxLayout
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import pyqtSlot, QTimer
import numpy as np
import scipy
import datetime
import fileinput
from scipy.interpolate import interp1d


from matplotlib.backends.qt_compat import QtCore, QtWidgets, is_pyqt5
if is_pyqt5():
    from matplotlib.backends.backend_qt5agg import (
        FigureCanvas, NavigationToolbar2QT as NavigationToolbar)
else:
    from matplotlib.backends.backend_qt4agg import (
        FigureCanvas, NavigationToolbar2QT as NavigationToolbar)
from matplotlib.figure import Figure

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

        self.tabs.addTab(self.tab_main, "Laser")

        self.laser_scan = QSpinBox()
        self.laser_offset = QLineEdit('391.01617')
        self.laser_set_point = QLineEdit('391.016170')
        self.single_step = QLineEdit('10')

        self.tab_main.layout = QVBoxLayout()
        self.tab_main.layout.addWidget(self.laser_offset)
        self.tab_main.layout.addWidget(self.laser_scan)
        self.tab_main.layout.addWidget(self.single_step)
        self.tab_main.layout.addWidget(self.laser_set_point)
        self.tab_main.setLayout(self.tab_main.layout)

        self.layout = QHBoxLayout()
        self.layout.addWidget(self.tabs) 
        self.setLayout(self.layout) 
 
        self.laser_scan.valueChanged.connect(self.set_point_update)
        self.laser_scan.valueChanged.connect(self.single_step_update)
               
        # properties
        self.laser_offset.text
        self.laser_scan.setSuffix(' MHz')
        self.laser_scan.setMinimum(-1000)
        self.laser_scan.setMaximum(1000)
        self.laser_scan.setSingleStep(np.int(self.single_step.text()))
        # Show widget
      
        self.show()

    def single_step_update(self):
        self.laser_scan.setSingleStep(np.int(self.single_step.text()))
        return

    def set_point_update(self):
        
        self.set_point = np.float(self.laser_offset.text()) + np.float(self.laser_scan.value())*1e-6
        # update set point
        file = open("setpoint.txt", "w")
        file.write(str(self.set_point))
        file.close()

        self.laser_set_point.setText(str(self.set_point))

        return


if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = App()
    sys.exit(app.exec_())

