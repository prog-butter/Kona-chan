import struct
import socket
import concurrent.futures
import colorama
import os
import time

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

		self.MAX_THREADS = 50
		# self.threadFutures = []

		self.connectTimer = time.monotonic()
		self.connectInterval = 30
		self.elapsed = 0

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

		self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=self.MAX_THREADS)

		# Start thread for all peers
		for index in range(len(self.peerList)):
			self.executor.submit(self.peerList[index].mainLoop)

	#Change Status
	def changeStatus(self, newStatus):
		for i in range(len(self.statusList) - 1):
			self.statusList[i] = self.statusList[i + 1]

		self.statusList[len(self.statusList) - 1] = newStatus

	# Print Status
	def printStatus(self):
		print("[{}] PEER MANAGER [{}]".format(len(self.activePeerList), self.connectInterval - self.elapsed))
		for i in range(len(self.statusList)):
			print("[{}]".format(self.statusList[i]), end='')
			self.statusList[i] = ""
		print("")

	def loop(self):
		# Update active peers
		self.activePeerList = []
		for peer in self.peerList:
			if (peer.readyToBeChecked == 0): # Cannot decide whether this peer is active or not
				self.activePeerList.append(peer)
			else:
				if (peer.isGoodPeer == 1): # Add to active peer list if this peer is good
					self.activePeerList.append(peer)

		# Timer to attempt connecting with inactive peers
		if (self.connectTimer):
			self.elapsed = time.monotonic() - self.connectTimer
			if (self.elapsed >= self.connectInterval):
				self.connectTimer = 0
		if (self.connectTimer == 0):
			# Try to re-connect with peers
			for peer in self.peerList:
				# Connect with peers not already connected to
				if (peer not in self.activePeerList):
					self.executor.submit(peer.mainLoop)

		# End of timer block
		if (self.tManager.DISPLAY_STATUS):
			self.printStatus()
			print("ACTIVE PEER STATUS")
			for peer in self.activePeerList:
				peer.printStatus()