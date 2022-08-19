import serial
import os
import datetime
import time
from simple_pid import PID
from wlm import *
from Fiber import *
import curses
import socket



MAX_ARDUINO_SIGNAL = 3500.0
MAX_ARDUINO_SIGNAL_390 = 3250.0

def get_frequencies():

    # Create a TCP/IP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # Connect the socket to the port where the server is listening
    #server_address = ('localhost', 10000)
    server_address = ('192.168.42.20', 62500)
    print('connecting to %s port %s' % server_address)
    sock.connect(server_address)

    try:
    
        # Send data
        message = 'request'
        print('sending "%s"' % message)
        sock.sendall(message.encode())

        # Look for the response
        amount_received = 0
        amount_expected = len(message)
    
        while amount_received < amount_expected:
            data = sock.recv(21)
            amount_received += len(data)
            print('received "%s"' % data)

        data = data.decode().split(',')
        data = list(map(float,data))

    finally:
        print('closing socket')
        sock.close()

    return data


def main(stdscr):

    ###
    stdscr.nodelay(True)
    curses.noecho()
    stdscr.keypad(True)
    curses.curs_set(0)
    scrx = [5,25,45,65]
    scry = 15
    if curses.has_colors:
        curses.start_color()
        curses.init_pair(1,curses.COLOR_WHITE,curses.COLOR_BLUE) #loading, labels
        curses.init_pair(2,curses.COLOR_WHITE,curses.COLOR_RED) #disabled
        curses.init_pair(3,curses.COLOR_BLACK,curses.COLOR_GREEN) #endabled
    stdscr.addstr(0,0,'Starting...',curses.color_pair(1))
    stdscr.refresh()
   # time.sleep(2)
    ###
    stdscr.addstr(1,0,'Opening Arduino COM port...',curses.color_pair(1))
    stdscr.refresh()
    n = 80
    serial_port  = 'COM5'; #pid lock arduino port

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

    stdscr.addstr(4,0,'Initializing variables...',curses.color_pair(1))
    stdscr.refresh()
    chans = [1,2]
    DAC_chans = [1,2]
    setpoint_files = ['422_setpoint.txt','390_setpoint.txt']
    setpoints = [0,0,0,0]
    act_values = [0,0,0,0]
    ard_values = [0,0,0,0]
    ard_mess = [20481,20482,20483,20484]
    names = ['422','390','ARYA','HeNe']
    time.sleep(1)
    stdscr.clear()

    ###
    stdscr.addstr(0,0,'-'*n)
    stdscr.addstr(1,5,'DUAL LASER LOCK')
    stdscr.addstr(2,0,'-'*n)
    stdscr.addstr(3,5,'Setpoint files in Z:\\Logs')
    incr = 100
    stdscr.addstr(4,5,'Increment: '+str(incr)+'       ')
    stdscr.refresh()
    ###

    for i in range(len(chans)):
        file = open("z:\\Logs\\"+setpoint_files[i], "r")
        setpoints[i] = file.readline().strip()
        file.close()
    pids = ['','','','']
    Kps = [10,400,100,100]
    Kis = [500,10000,100,1000]
    Kds = [0,0,0,0]

    invert_pid = [1, -1]

    for i in range(len(chans)):
        ###
        stdscr.addstr(i+5,5,'Ch {}    File: {}    P: {}   I: {}   D: {}        '.format(chans[i],setpoint_files[i],Kps[i],Kis[i],Kds[i]))
        ###
        pid = PID(Kps[i],Kis[i],Kds[i],setpoints[i],sample_time = 0.01, output_limits = [-10, 10])
        pids[i] = pid
        #fib1.setchan(chans[i])
    #print('-'*n)
    ###
    stdscr.addstr(10,0,'-'*n)
    stdscr.addstr(scry+11,0,"Press # for Ch #")
    stdscr.addstr(scry+12,0,"Press a for All")
    stdscr.addstr(scry+9,0,"PID params only change in single channel mode")
    stdscr.addstr(scry+10,25,"Press r/f to increase/decrease P")
    stdscr.addstr(scry+11,25,"Press t/g to increase/decrease I")
    stdscr.addstr(scry+12,25,"Press y/h to increase/decrease D")
    stdscr.addstr(scry+13,25,"Press u/j to increase/decrease increment")
    stdscr.refresh()
    NO_KEY_PRESSED = -1
    key_pressed = NO_KEY_PRESSED
    chan_mode = 0
    stdscr.addstr(scry+5,scrx[1],'ENABLED ',curses.color_pair(3))
    stdscr.addstr(scry+5,scrx[0],'ENABLED ',curses.color_pair(3))
    stdscr.addstr(scry+5,scrx[2],'ENABLED ',curses.color_pair(3))
    stdscr.addstr(scry+5,scrx[3],'ENABLED ',curses.color_pair(3))

    ###


    # get frequency


    while key_pressed != ord('q'):
        stdscr.refresh()
        key_pressed = stdscr.getch()
        if key_pressed == ord('1'):
            #fib1.setchan(1)
            #fib1.write('I1 1\r'.encode('ascii'))
            time.sleep(.1)
            #wlm.Trigger(0)
            chan_mode = 1
            stdscr.addstr(scry+5,scrx[0],'ENABLED ',curses.color_pair(3))
            stdscr.addstr(scry+5,scrx[1],'DISABLED',curses.color_pair(2))
            stdscr.addstr(scry+5,scrx[2],'DISABLED',curses.color_pair(2)) 
            stdscr.addstr(scry+5,scrx[3],'DISABLED',curses.color_pair(2))

        elif key_pressed == ord('2'):
            #fib1.setchan(2)
            #fib1.write('I1 2\r'.encode('ascii'))
            time.sleep(.1)
            #wlm.Trigger(0)
            chan_mode = 2
            stdscr.addstr(scry+5,scrx[1],'ENABLED ',curses.color_pair(3))
            stdscr.addstr(scry+5,scrx[0],'DISABLED',curses.color_pair(2))            
            stdscr.addstr(scry+5,scrx[2],'DISABLED',curses.color_pair(2))
            stdscr.addstr(scry+5,scrx[3],'DISABLED',curses.color_pair(2))

        elif key_pressed == ord('3'):
            #fib1.setchan(3)
            #fib1.write('I1 3\r'.encode('ascii'))
            time.sleep(.1)
            #wlm.Trigger(0)
            chan_mode = 3
            stdscr.addstr(scry+5,scrx[1],'DISABLED',curses.color_pair(2))
            stdscr.addstr(scry+5,scrx[0],'DISABLED',curses.color_pair(2))
            stdscr.addstr(scry+5,scrx[2],'ENABLED ',curses.color_pair(3))
            stdscr.addstr(scry+5,scrx[3],'DISABLED',curses.color_pair(2))

        elif key_pressed == ord('4'):
            #fib1.setchan(4)
            #fib1.write('I1 3\r'.encode('ascii'))
            time.sleep(.1)
            #wlm.Trigger(0)
            chan_mode = 4
            stdscr.addstr(scry+5,scrx[1],'DISABLED',curses.color_pair(2))
            stdscr.addstr(scry+5,scrx[0],'DISABLED',curses.color_pair(2))
            stdscr.addstr(scry+5,scrx[2],'DISABLED',curses.color_pair(2))
            stdscr.addstr(scry+5,scrx[3],'ENABLED ',curses.color_pair(3))

        elif key_pressed == ord('r'):
            #increase p
            if chan_mode != 0:
                new_p = Kps[chan_mode-1]+incr
                Kps[chan_mode-1] = new_p
                pids[chan_mode-1].Kp = new_p
                stdscr.addstr(chan_mode+4,5,'Ch {}    File: {}    P: {}   I: {}   D: {}       '.format(chans[chan_mode-1],setpoint_files[chan_mode-1],Kps[chan_mode-1],Kis[chan_mode-1],Kds[chan_mode-1]))
                stdscr.refresh()

        elif key_pressed == ord('f'):
            #decrease p
            if chan_mode != 0:
                new_p = Kps[chan_mode-1]-incr
                if new_p >= 0:
                    Kps[chan_mode-1] = new_p
                    pids[chan_mode-1].Kp = new_p
                    stdscr.addstr(chan_mode+4,5,'Ch {}    File: {}    P: {}   I: {}   D: {}       '.format(chans[chan_mode-1],setpoint_files[chan_mode-1],Kps[chan_mode-1],Kis[chan_mode-1],Kds[chan_mode-1]))
                    stdscr.refresh()

        elif key_pressed == ord('t'):
            #increase i
            if chan_mode != 0:
                new_i = Kis[chan_mode-1]+incr
                Kis[chan_mode-1] = new_i
                pids[chan_mode-1].Ki = new_i
                stdscr.addstr(chan_mode+4,5,'Ch {}    File: {}    P: {}   I: {}   D: {}       '.format(chans[chan_mode-1],setpoint_files[chan_mode-1],Kps[chan_mode-1],Kis[chan_mode-1],Kds[chan_mode-1]))
                stdscr.refresh()

        elif key_pressed == ord('g'):
            #decrease i
            if chan_mode != 0:
                new_i = Kis[chan_mode-1]-incr
                if new_i >= 0:
                    Kis[chan_mode-1] = new_i
                    pids[chan_mode-1].Ki = new_i
                    stdscr.addstr(chan_mode+4,5,'Ch {}    File: {}    P: {}   I: {}   D: {}       '.format(chans[chan_mode-1],setpoint_files[chan_mode-1],Kps[chan_mode-1],Kis[chan_mode-1],Kds[chan_mode-1]))
                    stdscr.refresh()

        elif key_pressed == ord('y'):
            #increase d
            if chan_mode != 0:
                new_d = Kds[chan_mode-1]+incr
                Kds[chan_mode-1] = new_d
                pids[chan_mode-1].Kd = new_d
                stdscr.addstr(chan_mode+4,5,'Ch {}    File: {}    P: {}   I: {}   D: {}       '.format(chans[chan_mode-1],setpoint_files[chan_mode-1],Kps[chan_mode-1],Kis[chan_mode-1],Kds[chan_mode-1]))
                stdscr.refresh()

        elif key_pressed == ord('h'):
            #decrease d
            if chan_mode != 0:
                new_d = Kds[chan_mode-1]-incr
                if new_d >= 0:
                    Kds[chan_mode-1] = new_d
                    pids[chan_mode-1].Kd = new_d
                    stdscr.addstr(chan_mode+4,5,'Ch {}    File: {}    P: {}   I: {}   D: {}       '.format(chans[chan_mode-1],setpoint_files[chan_mode-1],Kps[chan_mode-1],Kis[chan_mode-1],Kds[chan_mode-1]))
                    stdscr.refresh()


        elif key_pressed == ord('u'):
            #increase incr
            incr += 10
            stdscr.addstr(4,5,'Increment: '+str(incr)+'       ')
            stdscr.refresh()

        elif key_pressed == ord('j'):
            #decrease incr
            if incr-10 > 0:
                incr -= 10
                stdscr.addstr(4,5,'Increment: '+str(incr)+'       ')
                stdscr.refresh()
            else:
                pass



        elif key_pressed == ord('a'):
            chan_mode = 0
            stdscr.addstr(scry+5,scrx[1],'ENABLED ',curses.color_pair(3))
            stdscr.addstr(scry+5,scrx[0],'ENABLED ',curses.color_pair(3))
            stdscr.addstr(scry+5,scrx[2],'ENABLED ',curses.color_pair(3))
            stdscr.addstr(scry+5,scrx[3],'ENABLED ',curses.color_pair(3))
        else:
            pass

        if chan_mode == 0:
            
            act_values = get_frequencies()
            for l in range(len(chans)):
                newset = ''
                
                file = open("z:\\Logs\\"+setpoint_files[l], "r")
                newset = file.readline().strip()
                file.close()
                try:
                        pids[l].setpoint = float(newset)
                except:
                        pass


                new_freq = act_values[l]
                if new_freq >= 0:
                    control = invert_pid[l] * pids[l](act_values[l])
                    
                    if chans[l] == 1:
                        # 422
                        ard_mess[l] =  int(MAX_ARDUINO_SIGNAL/20 * control + MAX_ARDUINO_SIGNAL/2.0)*10+DAC_chans[l]
                    elif chans[l] == 2:
                        # 390
                        ard_mess[l] =  int(MAX_ARDUINO_SIGNAL_390/20 * control + MAX_ARDUINO_SIGNAL_390/2.0)*10+DAC_chans[l]
                   
                    mystr = '{:05d}'.format(ard_mess[l]).encode('utf-8')
                    ser.write(mystr) # converts from unicode to bytes
                    

                elif new_freq == -3.0:
                    act_values[l] = 'UNDER     '
                elif new_freq == -4.0:
                    act_values[l] = 'OVER      '
                else:
                    act_values[l] = 'ERROR     '

            
                stdscr.addstr(scry-1,scrx[l],names[l],curses.color_pair(1))
                stdscr.addstr(scry,scrx[l],'CTL: '+str(format(int((ard_mess[l]-chans[l])/10),'04d')))
                stdscr.addstr(scry+1,scrx[l],'SET: '+"{0:.6f}".format(pids[l].setpoint))
                try:
                    stdscr.addstr(scry+2,scrx[l],'ACT: '+"{0:.6f}".format(act_values[l]))
                except:
                    stdscr.addstr(scry+2,scrx[l],'ACT: '+act_values[l]+'     ')
                stdscr.refresh()
                #logfile.write('l: {}  CTL: {}  SET: {}  ACT: {}\n'.format(l,format(int((ard_mess[l]-chans[l])/10),'04d'),pids[l].setpoint,act_values[l]))
                ###
        else:
            newset = ''
            l = chan_mode-1
            file = open("z:\\Logs\\"+setpoint_files[l], "r")
            newset = file.readline().strip()
            file.close()
            try:
                    pids[l].setpoint = float(newset)
            except:
                    pass

            # obtains the actual frequency value
            act_values = get_frequencies()
            new_freq = act_values[l]

            if new_freq >= 0:
                control = invert_pid[l] * pids[l](act_values[l])
                #ard_mess[l] =  int(MAX_ARDUINO_SIGNAL/20 * control + MAX_ARDUINO_SIGNAL/2.0)*10+DAC_chans[l]
                if chans[l] == 1:
                     # 422
                     ard_mess[l] =  int(MAX_ARDUINO_SIGNAL/20 * control + MAX_ARDUINO_SIGNAL/2.0)*10+DAC_chans[l]
                elif chans[l] == 2:
                     # 390
                     ard_mess[l] =  int(MAX_ARDUINO_SIGNAL_390/20 * control + MAX_ARDUINO_SIGNAL_390/2.0)*10+DAC_chans[l]
                 
                mystr = '{:05d}'.format(ard_mess[l]).encode('utf-8')
                ser.write(mystr) # converts from unicode to bytes
                

            elif new_freq == -3.0:
                act_values[l] = 'UNDER     '
            elif new_freq == -4.0:
                act_values[l] = 'OVER      '
            else:
                act_values[l] = 'ERROR     '

        
            # for k in range(len(chans)):
            #     print('CTL {}:'.format(chans[k]),format(int((ard_mess[k]-chans[k])/10)hhh,'04d'),end='  ')
            #     print('SET {}:'.format(chans[k]),str(pids[k].setpoint)[:10],end='  ')
            #     print('ACT {}:'.format(chans[k]),str(act_values[k])[:10],end='  ')
            ###
            stdscr.addstr(scry-1,scrx[l],names[l],curses.color_pair(1))
            stdscr.addstr(scry,scrx[l],'CTL: '+str(format(int((ard_mess[l]-chans[l])/10),'04d')))
            stdscr.addstr(scry+1,scrx[l],'SET: '+"{0:.6f}".format(pids[l].setpoint))
            try:
                stdscr.addstr(scry+2,scrx[l],'ACT: '+"{0:.6f}".format(act_values[l]))
            except:
                stdscr.addstr(scry+2,scrx[l],'ACT: '+act_values[l]+'       ')
            stdscr.refresh()

               #print('            \r',end='')
        time.sleep(0.001)



curses.wrapper(main)
