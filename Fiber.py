import serial
import time
import wlm

# Commands: (for query)
#   ID?     Gets the switch's ID string
#   CF?     Gets the input/output dimensions
#   EO      Sets the echo option
#   ER?     Gets the system's error state
#       +0      All is well
#       001
#       002
#       003
#   I1 (n)  Sets the output channel (n within range of dimensions)
#   I1?     Gets the current output channel
#   PK      Sets the switch to parking state

class Fiber():
    def __init__(self,port):
        #print('Welcome to John\'s Dicon fiber switcher software!')
        self.bps = 115200 # bits per second (baud rate)
        self.dbs = 8 # data bits per baud
        self.sbs = 1 # stop bits
        self.term = b'\r' # terminator
        self.port = port # serial com port for motor
        self.ser = serial.Serial(self.port,baudrate=self.bps,timeout=1.0,parity=serial.PARITY_NONE,stopbits = serial.STOPBITS_ONE,bytesize=serial.EIGHTBITS)
        #print('Dicon Switcher Version:')
        #self.whatisyourname()
        #print('Switcher Size:')
        #self.whatisyourquest()
        #print('Current Output Channel:')
        #self.whatisyourfavoritecolor()
        #self.setchan(1)

        self.cycling = False

    def whatisyourname(self):
        #print('What is your name?')
        self.query('ID?')

    def whatisyourquest(self):
        #print('What is your quest?')
        self.query('CF?')

    def whatisyourfavoritecolor(self):
        #print('What is your favorite color?')
        self.query('I1?')

    def switch_test(self):
        for chan in channels:
            print('Setting output to channel {}'.format(chan))
            self.setchan(chan)
            time.sleep(1)
            print('Channel: ',end='')
            self.getchan()

        print('Test finished, parking...')
        self.setchan(0)

    def query(self,command):
        if type(command) != 'str':
            command = str(command)

        self.ser.write(command.encode('ascii')+self.term)
        time.sleep(0.005)
        if '?' in command:
            res = self.listen()
            return res

    def listen(self):
        try:
            ret = self.ser.read(4).decode()
            #print(ret)
            listening = True
            #time.sleep(0.005)
            while listening:
                #print(ret.encode())
                if '\r\n>' in ret:
                    listening = False
                    #print(type(ret))
                    return ret.split('\r\n>')[0][-1]
                else:
                    newret = self.ser.read(4).decode()
                    #print(newret)
                    ret = ret + newret
        except:
            print('you need new ears')

    def setchan(self,channel):
        self.query('I1 '+str(channel))

    def getchan(self):
        res = self.query('I1?')
        #print(res.encode())
        return res

    def cycle(self,channels):
        self.cycling = True
        print('Cycling {}'.format(channels))
        while self.cycling:
            for chan in channels:
                self.setchan(chan)
                time.sleep(.5)

    def close(self):
        self.setchan(1)






def testing():
    print('BEGIN FIBER SWITCHER TEST\n')
    fiber_port = 'COM1'
    fib1 = Fiber(fiber_port)
    running = True
    print('Ready for commands')
    while running:
        res = input('>>>')
        if res == 'quit':
            chk = input('Are you sure?\n>>>')
            if 'y' in chk:
                running = False
            elif 'n' in chk:
                pass
            else:
                print('I don\'t understand...')

        elif res == 'start':
            fib1.cycle((1,2))

        else:
            fib1.query(res)



    #fib1.switch_test()
    #fib1.whatisyourname()
    #fib1.whatisyourquest()
    #fib1.whatisyourfavoritecolor()
    print('END FIBER SWITCHER TEST')

if __name__ == '__main__':
    #testing()
    fib1 = Fiber('COM1')
    wlm1 = wlm.WavelengthMeter()
    time.sleep(2)
    fib1.setchan(3)
    time.sleep(2)
    #fib1.switch_test(range(17))
    #fib1.cycle((1,2))
    d = 0
    while True:
        for i in range(1,4):
            wlm1.Trigger(0)
            fib1.setchan(i)
            time.sleep(0.1)
            # rawch = fib1.getchan()
            # while int(rawch) != i:
            #     #stdscr.addstr(scry+4,(scrx[1]+scrx[0])//2,'Raw: '+str(rawch)+' ')
            #     #stdscr.refresh()
            #     if d == 1000:
            #         print('timeout')
            #         break
            #     time.sleep(0.001)
            #     d += 1
            #     rawch = fib1.getchan()
            #time.sleep(0.1)
            print('Channel: ',fib1.getchan(),' ', end='')
            wlm1.Trigger(3)
            #time.sleep(0.005)
            print(wlm1.frequency)
            time.sleep(.1)