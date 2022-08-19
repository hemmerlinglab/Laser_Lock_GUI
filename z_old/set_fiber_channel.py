from Fiber import *
import sys

f = Fiber('COM1')

f.setchan(int(sys.argv[1]))

#f.close()

