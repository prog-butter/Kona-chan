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
			self.peerList.append(p.Peer(ip, port, self.tManager))

		# Sort out peers that reply
		# peerCnt = 1
		# for peer in self.peerList:
		# 	if(peerCnt >= 21):
		# 		break
		# 	isGoodPeer = 1
		# 	print("Peer {}:".format(peerCnt))
		# 	peerCnt += 1

		# 	# except Exception as e:
		# 	# 	print(e)

		# 	if(isGoodPeer):
		# 		print("\033[32mFound a good peer!\033[39m")
		# 		self.goodPeerList.append(peer)

			# TO-DO
			# Decide whether to remove this peer from the fullList

		"""
			Implementer's Note: Even 30 peers is plenty, the official client version 3 in fact only
			actively forms new connections if it has less than 30 peers and will refuse connections
			if it has 55.
		"""
		#print("Good peers: {}".format(len(self.goodPeerList)))

		# Start thread for good peers
		executor = concurrent.futures.ThreadPoolExecutor(max_workers=50)
		f = []
		# Attempt handshake with all peers
		for index in range(len(self.peerList)):
			f.append(executor.submit(self.peerList[index].handshake))

		# Run start() for peers with successful handshake
		for index in range(len(self.peerList)):
			if(f[index].result()):
				executor.submit(self.peerList[index].start)

		print("Main thread continues...")

		executor.shutdown(wait = True)
		print("All peer threads finished")