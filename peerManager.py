import struct
import socket
import concurrent.futures
import colorama
import os

import peer as p

DEFAULT_TIMEOUT_VALUE = 3

PSTRLEN = 19
PSTR = "BitTorrent protocol"

class peerManager:
	def __init__(self, peers, torMan):
		colorama.init()
		self.peerList = [] # Complete peer list
		self.activePeerList = [] # Peers with which handshake was completed successfully
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

		#Status
		"""
		Oldest Status (lower index) → Newest Status (higher index)
		"""
		self.statusList = []
		for _ in range(self.tManager.NUM_STATUS):
			self.statusList.append("None")

		"""
			Implementer's Note: Even 30 peers is plenty, the official client version 3 in fact only
			actively forms new connections if it has less than 30 peers and will refuse connections
			if it has 55.
		"""

		# Start thread for all peers
		executor = concurrent.futures.ThreadPoolExecutor(max_workers=50)
		# Attempt handshake with all peers
		for index in range(len(self.peerList)):
			executor.submit(self.peerList[index].mainLoop)


	#Change Status
	def changeStatus(self, newStatus):
		for i in range(len(self.statusList) - 1):
			self.statusList[i] = self.statusList[i + 1]

		self.statusList[len(self.statusList) - 1] = newStatus

	# Print Status
	def printStatus(self):
		print("PEER MANAGER")
		for s in self.statusList:
			print("[{}]".format(s), end='')
		for s in self.statusList:
			s = ""
		print("")

	def loop(self):
		if (self.tManager.DISPLAY_STATUS):
			self.printStatus()
			print("PEER STATUS")
			for peer in self.peerList:
				peer.printStatus()