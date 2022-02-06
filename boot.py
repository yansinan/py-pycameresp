# This file is executed on every boot (including wake-boot from deepsleep)
#import esp
#esp.osdebug(None)
'''
try:
	import uasyncio
except:
	sys.path.append("lib")
	sys.path.append("simul")
import uasyncio
'''
import webrepl
#await uasyncio.gather(*[webrepl.start()])
#if not webrepl.client_s
webrepl.start(password="wha5c215")
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
