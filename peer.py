import time
import socket
import struct
import colorama

DEFAULT_TIMEOUT_VALUE = 3

PSTRLEN = 19
PSTR = "BitTorrent protocol"

class Peer:
	def __init__(self, ip, port, torMan):
		colorama.init()
		self.ip = ip
		self.port = int(port)
		self.tManager = torMan

		self.am_choking = 1 # this client is choking the peer
		self.am_interested = 0 # this client is interested in the peer
		self.peer_choking = 1 # peer is choking this client
		self.peer_interested = 0 # peer is interested in this client

	def mainLoop(self):
		print("{}:{} has started!".format(self.ip, self.port))
		time.sleep(0.1)
		print("{}:{} is closing!".format(self.ip, self.port))

	def handshake(self):
		isGoodPeer = 1
		try:
			# Establish TCP connection with peer
			s = socket.create_connection((self.ip, self.port), DEFAULT_TIMEOUT_VALUE)

			# Send handshakeString for BitTorrent Protocol
			handshakeString = bytes(chr(PSTRLEN) + PSTR + 8*chr(0), 'utf-8') + self.tManager.infoHash + bytes(self.tManager.local_peer_id, 'utf-8')
			print("Sending handshakeString: <{}>".format(handshakeString))
			s.send(handshakeString)

			"""
			1. Put each peer on it's own thread
			2. After handshake, peer will send an <id=5> packet telling which pieces that peer has. This message might not come at once.
				(NEED TO HANDLE THIS) Keep reading till complete message is received
			"""

			# Receive handshakeString from peer
			handshakeResponse = s.recv(1 + 19 + 8 + 20 + 20)
			if(len(handshakeResponse) == 0):
				print("\033[31mReceived an empty handshakeResponse\033[39m")
				isGoodPeer = 0
			else:
				print("Received handshakeResponse: <{}>".format(handshakeResponse))
				pstrlen = struct.unpack_from("B", handshakeResponse, 0)[0]
				if(pstrlen == PSTRLEN):
					print("\033[32mpstrlen matches!\033[39m")
				else:
					print("ERROR: pstrlen is not {}".format(PSTRLEN))
					isGoodPeer = 0

				pstr = handshakeResponse[1:20].decode('utf-8') #pstr is 19 bytes
				if(pstr == PSTR):
					print("\033[32mpstr matches!\033[39m")
				else:
					print("ERROR: pstr is not {}".format(PSTR))
					isGoodPeer = 0

				reservedBytes = struct.unpack_from("8s", handshakeResponse, 20)[0]
				print("Received reservedBytes: <{}>".format(reservedBytes))

				recInfoHash = struct.unpack_from("20s", handshakeResponse, 28)[0]
				if(self.tManager.infoHash == recInfoHash):
					print("\033[32minfoHash matches!\033[39m")
				else:
					print("ERROR: infoHash is not {}".format(self.tManager.infoHash))
					isGoodPeer = 0

				recPeerID = struct.unpack_from("20s", handshakeResponse, 48)[0]
				print("Received peerID: <{}>".format(recPeerID))

				# handshakeResponse = s.recv(2048)
				# lensecond = (len(handshakeResponse) - 5) * 8
				# print("length of second message: {}".format(lensecond))
				# if(len(handshakeResponse) == 0):
				# 	print("Nothing to read from this peer after initial receive")

		except socket.timeout:
			print("\033[31mSocket timed out!\033[39m")
			isGoodPeer = 0

		except socket.error:
			print("\033[31mConnection error!\033[39m")
			isGoodPeer = 0

		if(isGoodPeer):
			print("\033[32mFound a good peer!\033[39m")
			self.mainLoop()

		# Unsuccessful handshake, thread exits