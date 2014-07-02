import socket
import struct
import thread
import select

## created by mail@qhduan.com http://qhduan.com
## socks5 reference: http://tools.ietf.org/html/rfc1928

def Encode(data):
	if (data is None) or (len(data) <= 0):
		return data
	ret = ""
	for i in data:
		t = struct.unpack("B", i)[0]
		a = t & 0x0F
		b = t & 0xF0
		t = (a << 4) | (b >> 4)
		ret = ret + struct.pack("B", t)
	return ret

def Decode(data):
	if (data is None) or (len(data) <= 0):
		return data
	ret = ""
	for i in data:
		t = struct.unpack("B", i)[0]
		a = t & 0x0F
		b = t & 0xF0
		t = (a << 4) | (b >> 4)
		ret = ret + struct.pack("B", t)
	return ret


def ClientHandle(conn, addr):
	remote = None
	for res in socket.getaddrinfo(SERVERADDR, SERVERPORT, socket.AF_UNSPEC, socket.SOCK_STREAM, 0, socket.AI_PASSIVE):
		af, socktype, proto, canonname, sa = res
		try:
			remote = socket.socket(af, socktype, proto)
		except socket.error as msg:
			#print "socket create error", msg
			remote = None
			continue
		try:
			remote.connect(sa)
		except socket.error as msg:
			#print "socket connect error", msg
			remote.close()
			remote = None
			continue
		break
	
	if remote is None:
		print "could not connect server"
		thread.exit_thread()
		return
	
	sockets = [conn, remote]
	while 1:
		rlist, _, _, = select.select(sockets, [], [])
		if conn in rlist: # client, eg. browser
			data = None
			try:
				# recv from client, so don't encode
				data = conn.recv(8192)
			except socket.error as msg:
				data = None
			if not data: break
			data = Encode(data)
			try:
				remote.send(data)
			except socket.error as msg:
				break
		if remote in rlist: # server, eg. vps
			data = None
			try:
				data = remote.recv(8192)
			except socket.error as msg:
				data = None
			data = Decode(data)
			if not data: break
			try:
				# send to client, eg. browser, so don't encode
				conn.send(data)
			except socket.error as msg:
				break
	
	thread.exit_thread()


# server's address
SERVERADDR = "127.0.0.1"
# server's port
SERVERPORT = 21080
# local's port
PORT = 58080

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind(("127.0.0.1", PORT))
s.listen(5)

print "Client running on %s:%d" % ("127.0.0.1", PORT)

while 1:
	conn, addr = s.accept()
	print "Connected by", addr
	thread.start_new_thread(ClientHandle, (conn, addr))

