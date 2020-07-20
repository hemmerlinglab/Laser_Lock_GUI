import serial
import time
import socket
from simple_pid import PID
from wlm import *
from Fiber import *
import threading
import queue
import numpy as np

########################################################

CALIBRATION_CHANNEL = 4 # fiber channel of HeNe laser

########################################################


def my_init():
    serial_port  = 'COM14'; #pid lock arduino port

    baud_rate = 9600; #In arduino, Serial.begin(baud_rate)

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

    print('Init wavemeter')    
    wlm = WavelengthMeter()
    time.sleep(0.1)
    print('Init fiberswitcher')
    fib1 = Fiber('COM1')
    time.sleep(0.1)

    return (wlm, fib1, ser)

def init_pid():

    setpoint_files = ['setpoint.txt','setpoint2.txt','setpoint3.txt','setpoint4.txt']

    setpoints = [0,0,0,0]
    pids = ['','','','']
    Kps = [10,400,100,100]
    Kis = [100,8000,100,1000]
    Kds = [0,0,0,0]

    for i in range(len(setpoints)):
        pid = PID(Kps[i], Kis[i], Kds[i], setpoints[i], sample_time = 0.01, output_limits = [-10, 10])
        pids[i] = pid
    
    return setpoint_files, pids

def setup_server():
    # Create a TCP/IP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # Bind the socket to the port
    server_address = ('192.168.42.20', 63800)
    print('starting up on %s port %s' % server_address)
    sock.bind(server_address)

    # Listen for incoming connections
    sock.listen(1)

    return sock


def loop_pid(channel, ser, wlm, new_setpoint, pids, act_values):

    invert_pid = -1
    setpoints = [0,0,0,0]
    ard_mess = [20481,20482,20483,20484]
    
    try_trig = wlm.Trigger(3)
    new_freq = wlm.frequency

    time.sleep(.01)
    wlm.Trigger(0)    

    l = channel - 1
    try:
        pids[l].setpoint = float(new_setpoint)        
    except:
        pass
    
    new_freq = wlm.frequency    
    
    if new_freq >= 0:
        act_values[l] = new_freq
        control = invert_pid * pids[l](act_values[l])
        ard_mess[l] = int(4095.0/20 * control + 4095.0/2.0)*10+channel
        mystr = '{:05d}'.format(ard_mess[l]).encode('utf-8')
        ser.write(mystr) # converts from unicode to bytes        
        
        # print if at limits
        feedback = control * 4095.0/20 + 4095.0/2.0     
        if feedback <= 0.0 or feedback >= 4095.0:
            print("{0:6.6f} : {1:6.6f}, {2:4.2f}, {3}".format(new_freq, new_setpoint, feedback, mystr))

    elif new_freq == -3.0:
        act_values[l] = 'UNDER     '
    elif new_freq == -4.0:
        act_values[l] = 'OVER      '
    else:
        act_values[l] = 'ERROR     '

        time.sleep(0.001)

    return act_values



def do_calibration(fib, wlm, channel, calibration_frequency = 473.612512):

        # set fiber switcher to calibration channel
        fib.setchan(CALIBRATION_CHANNEL)

        # set exposure time
        wlm.SetExposure(150)
        time.sleep(1)

        # calibrate with HeNe
        cal = wlm.Calibration(calibration_frequency)

        # reset exposure time
        wlm.SetExposure(20)

        # switch back to channel
        fib.setchan(channel)
        time.sleep(1)

        # check that calibration went ok

        return


def run_pid(q_var, ser, fib, wlm, pids):

    calibrate = False
    new_setpoint = 0.0
    act_values = [0,0,0,0]

    while True:        

        try:
            var = q_var.get(block = False)
            code = var[0]
            channel = var[1]

            if code == 1:
                calibrate = True
                calibration_frequency = var[2]
            else:
                new_setpoint = var[2]

        except queue.Empty:            
            pass

        if calibrate:
            do_calibration(fib, wlm, channel, calibration_frequency = calibration_frequency)

            calibrate = False
        else:
            # run PID
            act_values = loop_pid(channel, ser, wlm, new_setpoint, pids, act_values)



def run_server(q_var, sock):
    while True:
        # Wait for a connection
        print('waiting for a connection')
        connection, client_address = sock.accept()

        try:
            print('connection from', client_address)

            # Receive the data in small chunks and retransmit it
            
            # data = 0,4,374.123456 = code,channel,frequency
            # code = 0, measure
            # code = 1, calibrate

            data = connection.recv(14)
            data = str(data.decode()).split(',')

            q_var.put([np.int(data[0]), np.int(data[1]), np.float(data[1])])
            
        finally:
            connection.close()


###################################
# main
###################################

print('Init ...')
(wlm, fib, ser) = my_init()

sock = setup_server()

print('Init PID ...')
setpoint_files, pids = init_pid()

do_calibration = False

channel = 2
fib.setchan(channel)

# Queue allows for communicating between threads
q_var = queue.Queue()

q_var.put([channel, 0.0])

# start PID thread
pid_thread = threading.Thread(target=run_pid, args=(q_var, ser, fib, wlm, pids))
pid_thread.start()

# start socket thread
socket_thread = threading.Thread(target=run_server, args=(q_var, sock,))
socket_thread.start()





