#import network as net
import uasyncio
import json
#from random import randint
#from machine import Pin
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

class WSCamera(AsyncWebsocketClient):
    url=""
    def __init__(self, url,ms_delay_for_read: int = 5):
        super(WSCamera, self).__init__(ms_delay_for_read)
        
        self.idCamera=self.getStrMAC(machine.unique_id(),"")
        print(self.idCamera)
        self.url = url+"/?role=camera&id="+self.idCamera
        # this lock will be used for data interchange between loops --------------------
        # better choice is to use uasynio.queue, but it is not documented yet
        self.lock = self._lock_for_open
        # this array stores messages from server
        self.data_from_ws = []
        self.loop = uasyncio.get_event_loop()
        self.nic = network.WLAN(network.STA_IF)
        
        self.loop.create_task(self.read_loop())
        
    #获取字符串格式的mac,并分隔或不分割
    def getStrMAC(self,inByte,inSpliter=":"):
        d=bytearray(inByte)
        s="".join(inSpliter+"%02x" % i for i in d)
        return s[len(inSpliter):]

    # ------------------------------------------------------------------------------
    def getStrTimeNow(self):
        def dd(inI):
            i=inI/100
            return str(i)[2:4]
        rtc = machine.RTC()
        t=rtc.datetime()
        strTimeNow=str(t[0])+dd(t[1])+dd(t[2])+"_"+dd(t[4])+":"+dd(t[5])
        return strTimeNow

    
    def getStatusSummary(self):
        try:
            #hall=esp32.hall_sensor()   #这个会导致camera宕机，估计两种可能1.背后贴磁铁了.2.读pin导致冲突    #read the internal hall sensor 
            temperature=(esp32.raw_temperature()-32)/1.8 # read the internal temperature of the MCU, in Fahrenheit
            ''''''
            res={
                "id":self.idCamera,
                #"urlImgLatest":"192.168.1.159:81/camera/start?framesize=640x480", #要小写x
                "type":"event",
                "event":"UPDATE_STATUS",
                "data":{
                    "misc":{
                        "vBatt":"5",
                        "time" :self.getStrTimeNow(),
                        "temperature":temperature,
                        #"hall":hall,
                    },
                    "net":{
                        "state":"REGISTERED",
                    },
                    "pm":{
                        "isSleep":machine.wake_reason(),                   
                    }
                },
                "time":self.getStrTimeNow(),
            }
        
            #wifi info

            rssi=self.nic.status("rssi") #
            ip=self.nic.ifconfig()[0] #(ip, subnet, gateway, dns)
            mac=self.getStrMAC(self.nic.config("mac"),"")
            wifi={
                "essid":self.nic.config('essid'),
                "ip":ip,
                "mac":mac,
                "rssi":rssi
            }
            print("status.data.wifi",wifi)
            res["data"]["net"]["rssi"]=rssi
            res["data"]["net"]["wifi"]=wifi
            res["urlImgLatest"]=ip+":81/camera/start?framesize=640x480", #要小写x
        except Exception as ex:
            print("Exception:getStatusSummary {}".format(ex))
            print("no network.WLAN(network.STA_IF)")
            pass
        return res
    # ------------------------------------------------------
    # Deal with data_recv
    async def dealDataRecv(self,item):
        ws=self
        dicItem=json.loads(item)
        print("\nData from ws: {}".format(dicItem))
        # 处理
        if (dicItem["type"]=="command") and ("data" in dicItem) and (dicItem["type"] in dicItem["data"]) and (dicItem["data"][dicItem["type"]]) :
            command = dicItem["data"][dicItem["type"]]
            if command=="updateStatus" :
                await ws.send(json.dumps(self.getStatusSummary()))
    # Task for read loop
    async def read_loop(self):
        ws=self
        
        while True:
            #gc.collect()
            # 等待wifi链接wlan
            if not self.nic.isconnected():
                await uasyncio.sleep_ms(500)
                continue
            try:
                # connect to test socket server with random client number
                urlServer="ws://wx.z-core.cn:4000/?role=camera&id="+self.idCamera;
                print("before ws handshake",urlServer)
                if not await ws.handshake(urlServer):
                    raise Exception('Handshake error.')
                else :
                    jsonStatus=json.dumps(self.getStatusSummary())
                    print("ws opened",jsonStatus)
                    await ws.send(jsonStatus)
                while await ws.open():
                    data = await ws.recv()
                    if data is not None:
                        #await self.lock.acquire()
                        #self.data_from_ws.append(data)
                        #self.lock.release()
                        await self.dealDataRecv(data)
                    await uasyncio.sleep_ms(50)
            except Exception as ex:
                print("Exception:read_loop {}".format(ex))
                await uasyncio.sleep(1)
                self.stop()
                
                
    def kill(self):
        self.loop.stop()
        self.loop.close()
        self.stop()
    def stop(self):
        self.open(False)
        self.sock.close()

# ------------------------------------------------------
# Main loop function: blink and send data to server.
# This code emulates main control cycle for controller.
'''
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
                    await dealDataRecv(data)
                data_from_ws = []
            lock.release()
            #gc.collect()

        await uasyncio.sleep_ms(400)
'''
# ------------------------------------------------------
'''
def start(loop):    
    loop.create_task(read_loop())
    #loop.create_task(receive_loop())
    print("websocket start read_loop")

async def main():    
    tasks = [read_loop(),receive_loop()]
    await uasyncio.gather(*tasks)
    print("main.isEnd")
    

#uasyncio.run(main())
#loop = uasyncio.get_event_loop()
#loop.run_until_complete(main())
'''
#独立启动函数
if __name__=="__main__" :
    # create instance of websocket
    config={
        "server": "ws://wx.z-core.cn:4000",
        "socket_delay_ms": 5
        }
    ws = WSCamera(config['server'],config['socket_delay_ms'])
    #先检查并尝试联网
    if not ws.nic.isconnected():
        ws.nic.active(True)
        print('connecting to network...')
        ws.nic.connect('Kino', '5015025015')
        while not ws.nic.isconnected():
            pass
    print('network config:', ws.nic.ifconfig())
    
    loop=uasyncio.get_event_loop()
    #print("format=","{}{}".format(config["server"], str(idCamera)))
        
    #loop.run_until_complete(main())
    #while True:
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        print("websocket.test interrupted")
    except Exception as ex:
        print("Exception:runWS() {}".format(ex))
    ws.kill()
    
    print("test all closed")

