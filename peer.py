import time

class Peer:
	def __init__(self, ip, port):
		self.ip = ip
		self.port = int(port)

		self.am_choking = 1 # this client is choking the peer
		self.am_interested = 0 # this client is interested in the peer
		self.peer_choking = 1 # peer is choking this client
		self.peer_interested = 0 # peer is interested in this client

	def start(self):
		print("Peer has started!")
		time.sleep(0.1)