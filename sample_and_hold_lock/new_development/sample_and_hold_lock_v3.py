from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (QWidget, QCheckBox, QRadioButton, QHBoxLayout, QVBoxLayout,
                             QButtonGroup, QLabel, QApplication)

import sys

class Laser_Lock(QWidget):



    def __init__(self):
        super().__init__()

        self.initUI()


    def initUI(self):

        vbox = QVBoxLayout()
        hbox = QHBoxLayout()

        fs_group = QButtonGroup(self)

        self.fiber_switch_channel_buttons = []

        self.no_of_fiber_channels = 5

        for k in range(self.no_of_fiber_channels):

            hlp = QRadioButton(str(k), self)

            fs_group.addButton(hlp)

            vbox.addWidget(hlp)

            self.fiber_switch_channel_buttons.append(hlp)


        cb = QCheckBox('Show title', self)
        cb.toggle()
        cb.stateChanged.connect(self.changeTitle)

        hbox.addLayout(vbox)

        #rb1.toggled.connect(self.updateLabel1)

        #rb2 = QRadioButton('Middle', self)
        #rb2.toggled.connect(self.updateLabel1)

        #rb3 = QRadioButton('Small', self)
        #rb3.toggled.connect(self.updateLabel1)

        #hbox2 = QHBoxLayout()
        #bg2 = QButtonGroup(self)

        #rb4 = QRadioButton('Red', self)
        #rb4.toggled.connect(self.updateLabel2)

        #rb5 = QRadioButton('Green', self)
        #rb5.toggled.connect(self.updateLabel2)

        #rb6 = QRadioButton('Blue', self)
        #rb6.toggled.connect(self.updateLabel2)

        #self.label1 = QLabel('', self)
        #self.label2 = QLabel('', self)

        #bg1.addButton(rb1)
        #bg1.addButton(rb2)
        #bg1.addButton(rb3)

        #bg2.addButton(rb4)
        #bg2.addButton(rb5)
        #bg2.addButton(rb6)

        #hbox1.addWidget(rb1)
        #hbox1.addWidget(rb2)
        #hbox1.addWidget(rb3)

        #hbox2.addWidget(rb4)
        #hbox2.addWidget(rb5)
        #hbox2.addWidget(rb6)

        #vbox.addLayout(hbox1)
        #vbox.addLayout(hbox2)
        #vbox.addWidget(self.label1)
        #vbox.addWidget(self.label2)

        self.setLayout(hbox)

        self.setGeometry(300, 300, 350, 250)
        self.setWindowTitle('QRadioButton')
        self.show()

    def changeTitle(self, state):

        if state == Qt.CheckState.Checked.value:
            
            for k in range(len(self.fiber_switch_channel_buttons)):

                if self.fiber_switch_channel_buttons[k].isChecked():
                    self.setWindowTitle('QCheckBox' + str(k))
        else:
            self.setWindowTitle(' ')

    def updateLabel1(self, _):

        rbtn = self.sender()

        if rbtn.isChecked() == True:
            self.label1.setText(rbtn.text())

    def updateLabel2(self, _):

        rbtn = self.sender()

        if rbtn.isChecked() == True:
            self.label2.setText(rbtn.text())


    def getData(self):
        self.data = random.gauss(10,0.1)
        self.ValueTotal.append(self.data)
        self.updateData()

    def updateData(self):
        if not hasattr(self, 'line'):
            # this should only be executed on the first call to updateData
            self.ui.graph.axes.clear()
            self.ui.graph.axes.hold(True)
            self.line = self.ui.graph.axes.plot(self.ValueTotal,'r-')
            self.ui.graph.axes.grid()
        else:
            # now we only modify the plotted line
            self.line.set_xdata(np.arange(len(self.ValueTotal)))
            self.line.set_ydata(self.ValueTotal)
        self.ui.graph.draw()




def main():

    app = QApplication(sys.argv)
    ex = Laser_Lock()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()




