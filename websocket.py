import network as net
import uasyncio as uasyncio
import json
from random import randint
from machine import Pin
import machine
import esp32 #温度，hall
import network

import gc

'''
def reload()
    try
        from sys import modules
        del AsyncWebsocketClient
        gc.collect()
        print("AsyncWebsocketClient del success")
    except Exception as ex:
        print("AsyncWebsocketClient not init".format(ex))
    return __import__("async_websocket_client.AsyncWebsocketClient")
 
AsyncWebsocketClient=reload()
'''
import sys
try:
    del sys.modules["AsyncWebsocketClient"]
    gc.collect()
    print("clear AsyncWebsocketClient done")
except:
    print("no AsyncWebsocketClient")
    pass
from async_websocket_client import AsyncWebsocketClient


def getStrMAC(inByte,inSpliter=":"):
    d=bytearray(inByte)
    s="".join(inSpliter+"%02x" % i for i in d)
    return s[len(inSpliter):]
    
# create instance of websocket
idCamera=getStrMAC(machine.unique_id(),"")
print(idCamera)
config={
    "server": "ws://wx.z-core.cn:4000/?role=camera&id="+idCamera,
    "socket_delay_ms": 5
    }

ws = AsyncWebsocketClient()

# this lock will be used for data interchange between loops --------------------
# better choice is to use uasynio.queue, but it is not documented yet
lock = uasyncio.Lock()
# this array stores messages from server
data_from_ws = []
loop = uasyncio.get_event_loop()
nic = network.WLAN(network.STA_IF)
# ------------------------------------------------------------------------------
def dd(inI):
    i=inI/100
    return str(i)[2:4]

def getStatusSummary():
    global idCamera
    global nic
    isShort=False;
    print("before RTC")
    rtc = machine.RTC()
    t=rtc.datetime()
    strTimeNow=str(t[0])+dd(t[1])+dd(t[2])+"_"+dd(t[4])+":"+dd(t[5])
    print("after RTC",strTimeNow)
    hall=esp32.hall_sensor()     # read the internal hall sensor
    temperature=esp32.raw_temperature() # read the internal temperature of the MCU, in Fahrenheit
    ''''''
    res={
        "id":idCamera,
        "urlImgLatest":"192.168.1.159:8081/camera/start",
        "type":"event",
        "event":"UPDATE_STATUS",
        "data":{
            "misc":{
                "vBatt":"5",
                "time" :strTimeNow,
                "temperature":temperature,
                "hall":hall,
            },
            "net":{
                "state":"REGISTERED",
            },
            "pm":{
                "isSleep":machine.wake_reason(),                   
            }
        },
        "time":strTimeNow,
    }
        #wifi info
    try:
        rssi=nic.status("rssi") #
        ip=nic.ifconfig()[0] #(ip, subnet, gateway, dns)
        mac=getStrMAC(nic.config("mac"),"")
        wifi={
            "essid":nic.config('essid'),
            "ip":ip,
            "mac":mac,
            "rssi":rssi
        }
        print("status.data.wifi",wifi)
        res["data"]["net"]["rssi"]=rssi
        res["data"]["net"]["wifi"]=wifi
    except Exception as ex:
        print("Exception:getStatusSummary {}".format(ex))
        print("no network.WLAN(network.STA_IF)")
        pass
    return res
# ------------------------------------------------------
# Task for read loop
async def read_loop():
    global idCamera
    global config
    global lock
    global data_from_ws
    global loop
    global nic

    while True:
        gc.collect()
        # 等待wifi链接wlan
        if not nic.isconnected():
            await uasyncio.sleep_ms(500)
            continue
        try:
            # connect to test socket server with random client number
            if not await ws.handshake("ws://wx.z-core.cn:4000/?role=camera&id="+idCamera):
                raise Exception('Handshake error.')
            else :
                jsonStatus=json.dumps(getStatusSummary())
                print("ws is open",jsonStatus)
                await ws.send(jsonStatus)
            while await ws.open():
                data = await ws.recv()
                if data is not None:
                    await lock.acquire()
                    data_from_ws.append(data)
                    lock.release()
                await uasyncio.sleep_ms(50)
        except Exception as ex:
            print("Exception:read_loop {}".format(ex))
            await uasyncio.sleep(1)
            loop.stop()
            loop.close()
            ws.sock.close()

# ------------------------------------------------------
# Main loop function: blink and send data to server.
# This code emulates main control cycle for controller.
async def receive_loop():
    global lock
    global data_from_ws
    global ws
    global nic

    # Main "work" cycle. It should be awaitable as possible.
    while True:
        if nic.isconnected() and ws is not None:
            # lock data archive
            await lock.acquire()
            if data_from_ws:
                for item in data_from_ws:
                    dicItem=json.loads(item)
                    print("\nData from ws: {}".format(dicItem))
                    # 处理
                    if (dicItem["type"]=="command") and ("data" in dicItem) and (dicItem["type"] in dicItem["data"]) and (dicItem["data"][dicItem["type"]]) :
                        command = dicItem["data"][dicItem["type"]]
                        if command=="updateStatus" :
                            await ws.send(json.dumps(getStatusSummary()))
                data_from_ws = []
            lock.release()
            gc.collect()

        await uasyncio.sleep_ms(400)
# ------------------------------------------------------
def start(loop):    
    loop.create_task(read_loop())
    loop.create_task(receive_loop())
    print("websocket start 2 tasks")
    
async def main():    
    tasks = [read_loop(),receive_loop()]
    await uasyncio.gather(*tasks)
    print("main.isEnd")
    
'''
#uasyncio.run(main())
#loop = uasyncio.get_event_loop()
#loop.run_until_complete(main())
'''
#独立启动函数
def runWS():
    global loop
    
    print("main.config",config)
    print("format=","{}{}".format(config["server"], str(idCamera)))
    
    start(loop)
    
    #loop.run_until_complete(main())
    #while True:
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        print("websocket.test interrupted")
    except Exception as ex:
        print("Exception:runWS() {}".format(ex))

    loop.stop()
    loop.close()
    ws.sock.close()
    
    print("test all closed")