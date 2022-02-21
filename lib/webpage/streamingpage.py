# Distributed under MIT License
# Copyright (c) 2021 Remi BERTHOLET
""" Function define the web page to see the camera streaming """
from server.httpserver  import HttpServer
from server.httprequest import *
from server.server      import Server
from htmltemplate       import *
from video              import Camera
import uasyncio
from tools              import useful, tasking

class Streaming:
	""" Management class of video streaming of the camera via an html page """
	streaming_id = [0]
	inactivity = [None]
	config = [None]
	durty = [False]

	@staticmethod
	def set_config(config):
		""" Set current configuration """
		Streaming.config[0] = config
		Streaming.durty[0] = True

	@staticmethod
	def get_config():
		""" Get current configuration """
		return Streaming.config[0]

	@staticmethod
	def is_durty():
		""" Indicates if the configuration changed """
		return Streaming.durty[0]

	@staticmethod
	def reset_durty():
		""" Reset the configuration changed flag """
		Streaming.durty[0] = False

	@staticmethod
	def get_html(request, width=None, height=None):
		""" Return streaming html part with javascript code """
		Streaming.activity()
		Streaming.streaming_id[0] += id(request)
		if width is not None and height is not None:
			size = b'width="%d" height="%d"'%(width, height)
		else:
			size = b""
		return Tag(b"""
		<p>
			<div style="position: relative;">
				<img id="video-stream" src="" %s/>
				<table id="zone_masking" style="position: absolute;top:0px" />
			</div>
		</p>
		<script>
			var streamUrl = document.location.protocol + "//" + document.location.hostname + ':%d';
			document.getElementById('video-stream').src = `${streamUrl}/camera/start?streaming_id=%d`;
		</script>"""%(size, request.port+1,Streaming.streaming_id[0]))

	@staticmethod
	def inactivity_timeout(timer):
		""" Suspend video streaming after delay """
		Streaming.streaming_id[0] += 1

	@staticmethod
	def activity():
		""" User activity detected """
		if Streaming.inactivity[0]:
			Streaming.inactivity[0].stop()
			Streaming.inactivity[0] = None
		Streaming.inactivity[0] = tasking.Inactivity(Streaming.inactivity_timeout, duration=tasking.LONG_WATCH_DOG, timer_id=1)

	@staticmethod
	def get_streaming_id():
		""" Return the current streaming id """
		return Streaming.streaming_id[0]

@HttpServer.add_route(b'/camera/start', available=useful.iscamera() and Camera.is_activated())
async def camera_start_streaming(request, response, args):
	""" Start video streaming """
	Server.slow_down()
	if request.name != "StreamingServer":
		return

	try:
		writer = None
		print("camera_start_streaming=>request.params=",request.params)
		if b"streaming_id" in request.params :
			currentstreaming_id = int(request.params[b"streaming_id"])
		else :
			#如果是直接读取图片，需要设置Streaming.streaming_id[0]
			Streaming.activity()
			currentstreaming_id=Streaming.streaming_id[0]
			#通过参数设置分辨率
			if b"framesize" in request.params :
				Camera.framesize(request.params[b"framesize"])
				config = Camera.get_config()
				Streaming.set_config(config)
		reserved = await Camera.reserve(request, timeout=20, suspension=15)
		print("Start streaming %d"%currentstreaming_id,"reserved",reserved,"Camera.is_activated()",Camera.is_activated())
		if reserved:
			isCameraOpenSuccess=Camera.open()
			print("isCameraOpenSuccess",isCameraOpenSuccess);
			response.set_status(b"200")
			response.set_header(b"Content-Type"               ,b"multipart/x-mixed-replace")
			response.set_header(b"Transfer-Encoding"          ,b"chunked")
			response.set_header(b"Access-Control-Allow-Origin",b"*")
			await response.serialize(response.streamio)
			writer = response.streamio
			identifier = b"\r\n%x\r\n\r\n--%s\r\n\r\n"%(len(response.identifier) + 6, response.identifier)
			frame = b'%s36\r\nContent-Type: image/jpeg\r\nContent-Length: %8d\r\n\r\n\r\n%x\r\n'

			if useful.ismicropython():
				micropython = True
			else:
				micropython = False
				
			if Streaming.is_durty():
				Camera.configure(Streaming.get_config())
				Streaming.reset_durty()
			
			image = Camera.capture()
			length = len(image)
			try:
				await writer.write(frame%(b"", length, length))
				await writer.write(image)
			except:
				currentstreaming_id = 0
			print("before while streaming %d"%currentstreaming_id,"Streaming.get_streaming_id=",Streaming.get_streaming_id())
			while currentstreaming_id == Streaming.get_streaming_id():
				if Streaming.is_durty():
					Camera.configure(Streaming.get_config())
					Streaming.reset_durty()
				try:
					image = Camera.capture()
					length = len(image)
				except Exception as err:
					useful.syslog(err)
					#不知道为什么这里一旦websocket就不能Camera了，Camera.open也无法恢复
					# hall传感器与Camera冲突
					print("err:Camera.get_stat()",Camera.get_stat(),"image=>",image)
					Camera.close()
					Camera.configure(Streaming.get_config())
					print("isCameraOpenSuccess",Camera.open());
					continue
				try:
					await writer.write(frame%(identifier, length, length))
					await writer.write(image)
					await uasyncio.sleep_ms(0)
				except:
					break
				if micropython is False:
					await uasyncio.sleep(0.1)
	except Exception as err:
		useful.syslog(err)
	finally:
		if reserved:
			# print("End streaming %d"%currentstreaming_id)
			await Camera.unreserve(request)
		if writer:
			await writer.close()
