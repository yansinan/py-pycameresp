# This file is executed on every boot (including wake-boot from deepsleep)
#import esp
#esp.osdebug(None)
#import webrepl
#webrepl.start()
import gc
from sys import modules

def reload(inStr):
    import sys
    if (inStr in modules) :
        #mod.__name__
        #mod_name = inStr 
        del modules[inStr]
        gc.collect()
    return __import__(inStr)

def reboot():
    import machine
    machine.reset()
    