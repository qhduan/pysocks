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

# a function receive exactly bytes(size) from sockets 'conn'
def RecvData(conn, size):
	data = None
	try:
		data = conn.recv(size)
		while len(data) < size:
			data = data + conn.recv(size - len(data))
	except socket.error as msg:
		return None
	return data

# close all sockets in 'list' and exit_thread
def ClientExit(list):
	for i in list:
		i.close()
	thread.exit_thread()

# thread function for one request
def ClientHandle(conn, addr):
	data = RecvData(conn, 2)
	data = Decode(data)
	if not data:
		conn.close()
		thread.exit_thread()
	
	VER, NMETHODS = struct.unpack("BB", data)
	
	data = RecvData(conn, NMETHODS)
	data = Decode(data)
	if not data:
		conn.close()
		thread.exit_thread()
	
	METHODS = struct.unpack("B" * NMETHODS, data)
	
	# only NO AUTHENTICATION REQUIRED
	data = struct.pack("BB", 5, 0)
	data = Encode(data)
	conn.send(data)

	data = RecvData(conn, 4)
	data = Decode(data)
	if not data: ClientExit([conn])
	VER, CMD, _, ATYP = struct.unpack("BBBB", data)
	
	# DST.ADDR
	DSTADDR = ""
	if ATYP == 1: # IPv4
		data = RecvData(conn, 4)
		data = Decode(data)
		if not data: ClientExit([conn])
		DSTADDR = "%d.%d.%d.%d" % struct.unpack("BBBB", data)
	elif ATYP == 3: # Domain
		data = RecvData(conn, 1)
		data = Decode(data)
		if not data: ClientExit([conn])
		length = struct.unpack("B", data)[0]			
		data = RecvData(conn, length)
		data = Decode(data)
		if not data: ClientExit([conn])
		DSTADDR = data
	elif ATYP == 4: # IPv6
		data = RecvData(conn, 16)
		data = Decode(data)
		if not data: ClientExit([conn])
		DSTADDr = "%x.%x.%x.%x.%x.%x.%x.%x" % struct.unpack("HHHHHHHH", data)
	else:
		# send X'08' Address type not supported
		conn.send(Encode(struct.pack("BBBBIH", 5, 8, 0, 1, 0, 0)))
		ClientExit([conn])
	# DST.PORT
	data = RecvData(conn, 2)
	data = Decode(data)
	DSTPORT = struct.unpack("BB", data)
	DSTPORT = DSTPORT[0] * (2**8) + DSTPORT[1]
	
	#print addr, VER, CMD, ATYP, DSTADDR, DSTPORT
	
	remote = None
	for res in socket.getaddrinfo(DSTADDR, DSTPORT, socket.AF_UNSPEC, socket.SOCK_STREAM, 0, socket.AI_PASSIVE):
		af, socktype, proto, canonname, sa = res
		try:
			remote = socket.socket(af, socktype, proto)
		except socket.error as msg:
			print "socket create error", msg
			remote = None
			continue
		try:
			remote.connect(sa)
		except socket.error as msg:
			print "socket connect error", msg
			remote.close()
			remote = None
			continue
		break
	
	if remote is None:
		#print "could not open socket"
		conn.send(Encode(struct.pack("BBBBIH", 5, 1, 0, 1, 0, 0)))
		conn.close()
		thread.exit_thread()
		return
	
	#print "OK", addr
	conn.send(Encode(struct.pack("BBBBIH", 5, 0, 0, 1, 0, 0)))
	
	sockets = [conn, remote]
	while True:
		rlist, _, _, = select.select(sockets, [], [])
		if conn in rlist: # client
			data = None
			try:
				data = conn.recv(8192)
				data = Decode(data)
			except socket.error as msg:
				data = None
			if not data: ClientExit([conn, remote])
			try:
				# send to remote, don't encode
				remote.send(data)
			except socket.error as msg:
				ClientExit([conn, remote])
		if remote in rlist: # remote host
			data = None
			try:
				data = remote.recv(8192)
			except socket.error as msg:
				data = None
			if not data: ClientExit([conn, remote])
			try:
				conn.send(Encode(data))
			except socket.error as msg:
				ClientExit([conn, remote])
	

# server's IP, for release
HOST = socket.gethostbyname(socket.gethostname())
# for debug
#HOST = "127.0.0.1"

# server's port
PORT = 21080

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind((HOST, PORT))
s.listen(5)

print "Server running on %s:%d" % (HOST, PORT)

while 1:
	conn, addr = s.accept()
	print "Connected by", addr
	thread.start_new_thread(ClientHandle, (conn, addr))

s.close()