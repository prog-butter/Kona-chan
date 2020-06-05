import struct
import socket
import concurrent.futures
import colorama

import peer as p

DEFAULT_TIMEOUT_VALUE = 3
PSTRLEN = 19
PSTR = "BitTorrent protocol"

class peerManager:
	def __init__(self, peers, torMan):
		colorama.init()
		self.peerList = [] # Complete peer list
		self.goodPeerList = [] # Peers with which handshake was completed successfully
		self.tManager = torMan
		offset = 0
		while offset < len(peers):
			# Unpack bytes for IP from byte-string, as big-endian integers and get the first element from the tuple
			ip_unpacked = struct.unpack_from("!i", peers, offset)[0]
			# Pack read bytes into a single IP and convert to standard 32-bit IP notation
			ip = socket.inet_ntoa(struct.pack("!i", ip_unpacked))
			# Update offset to read the corresponding port
			offset += 4
			# Unpack bytes for port and join them as Big-endian uint16 to form port
			port = struct.unpack_from("!H", peers, offset)[0]
			# Update offset for next peer
			offset += 2
			# Add parsed peer to peerlist
			self.peerList.append(p.Peer(ip, port))

		# Sort out peers that reply
		peerCnt = 1
		for peer in self.peerList:
			isGoodPeer = 1
			print("Peer {}:".format(peerCnt))
			peerCnt += 1
			try:
				# Establish TCP connection with peer
				s = socket.create_connection((peer.ip, peer.port), DEFAULT_TIMEOUT_VALUE)

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

			# except Exception as e:
			# 	print(e)

			if(isGoodPeer):
				print("\033[32mFound a good peer!\033[39m")
				self.goodPeerList.append(peer)

			# TO-DO
			# Decide whether to remove this peer from the fullList

		"""
			Implementer's Note: Even 30 peers is plenty, the official client version 3 in fact only
			actively forms new connections if it has less than 30 peers and will refuse connections
			if it has 55.
		"""
		print("Good peers: {}".format(len(self.goodPeerList)))

		# Start thread for good peers
		with concurrent.futures.ThreadPoolExecutor(max_workers=30) as executor:
			for index in range(len(self.goodPeerList)):
				executor.submit(self.goodPeerList[index].start)

		print("All peer threads finished")