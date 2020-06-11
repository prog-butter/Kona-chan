from bcoding import bencode, bdecode
import hashlib
import requests
import struct
import socket
import random
import threading
import os
import time
import colorama

import peerManager as pm
import pieceManager as piem
import torrent_file as file
import piece as p

class torrentManager:
	def __init__(self, torrentpath):
		colorama.init()
		self.torrentpath = torrentpath
		self.announceData = ""
		self.infoHash = ""
		self.pieceHashes = []
		self.pieceLength = 0

		# List of files in this torrent
		self.files = []
		self.length = 0
		self.name = ""

		self.pieces = ""
		self.local_peer_id = bytes("-KC0010-" + str(random.randint(100000000000, 999999999999)), 'utf-8')
		self.shouldLoop = 1
		# Lock to synchronize calling pieceManager methods from peers (or anywhere else)
		self.piemLock = threading.Lock()

		self.announceCount = 1
		self.trackerid = -1 # -1 means trackerid is not available
		self.announceTimer = 0
		self.announceInterval = 0 # -1 means interval is not available
		self.elapsed = 0

		#Status
		"""
		Oldest Status (lower index) → Newest Status (higher index)
		"""
		self.NUM_STATUS = 5
		self.DISPLAY_STATUS = 1
		self.statusList = []
		for _ in range(self.NUM_STATUS):
			self.statusList.append("None")

		# Open .torrent file and decode data
		with open(torrentpath, "rb") as f:
			torrent = bdecode(f)

		# Fields common to both single file and multi file torrents
		self.announceData = torrent['announce']
		self.pieceLength = torrent['info']['piece length']
		self.pieces = torrent['info']['pieces']
		for index in range(0, len(self.pieces), 20):
			self.pieceHashes.append(self.pieces[index:index + 20])

		# Single file
		if('length' in torrent['info'].keys()):
			print("\033[92mSingle file torrent\033[0m")
			self.length = torrent['info']['length']
			self.name = torrent['info']['name']
			# For single file torrents, filepath and name are both ['info']['name']
			self.files.append(file.File(torrent['info']['name'], torrent['info']['name'], torrent['info']['length']))
			# self.lastPieceLength = self.length % self.pieceLength
		else:
			self.length = 0 # For multi file case, equal to sum of length of all files
			print("\033[91mMulti file torrent\033[0m")
			masterDir = torrent['info']['name'] # The top folder in which to store all the other dirs/files
			for f in torrent['info']['files']:
				self.length += f['length']
				"""
				fp - filepath
				fn - filename
				"""
				fp = masterDir
				for t in f['path']: # A list
					fp += ("/" + t)
				fn = f['path'][-1]
				self.files.append(file.File(fp, fn, f['length']))

		# Create list of pieces to give to pieceManager
		self.pieceList = []
		# Add all pieces except last piece
		for i in range(len(self.pieceHashes) - 1):
			self.pieceList.append(p.Piece(i, self.length, self.pieceLength, 0, 0))

		# Add last piece
		self.pieceList.append(p.Piece(len(self.pieceHashes) - 1, self.length, self.pieceLength, 0, 1))

		# Display piece and block info
		print("TORRENT INFO")
		print("LENGTH: {}, PIECES: {}, PIECE LENGTH: {}".format(self.length, len(self.pieceHashes), self.pieceLength))
		print("{} pieces are {} long and have {} blocks each {} long"
			.format(len(self.pieceHashes) - 1, self.pieceLength, self.pieceList[-2].number_of_blocks, self.pieceList[-2].block_size))
		print("Last piece is {} long and have {} blocks with \"LAST\" block {} long"
			.format(self.pieceList[-1].piece_size, self.pieceList[-1].number_of_blocks, self.pieceList[-1].last_block_size))

		i = input()
		# Calculate infohash
		encoded = bencode(torrent['info'])
		m = hashlib.sha1(encoded)
		self.infoHash = m.digest()

		# Instantiate a piece manager for this torrent file
		self.changeStatus("Creating piece manager for this torrent")
		self.pieManager = piem.pieceManager(self, self.pieceList)

	#Change Status
	def changeStatus(self, newStatus):
		for i in range(len(self.statusList) - 1):
			self.statusList[i] = self.statusList[i + 1]

		self.statusList[len(self.statusList) - 1] = newStatus

	def announce(self, downloadedBytes = 0, announceEvent = "started"):
		print("About to send announce no. <{}>".format(self.announceCount))
		self.announceCount += 1

		qParams = {
			"info_hash": self.infoHash,
			"peer_id": self.local_peer_id,
			"port": "6882",
			"uploaded": "0",
			"downloaded": downloadedBytes,
			"left": (self.length - downloadedBytes),
			"compact": "1"
		}
		if (self.trackerid != -1):
			qParams["trackerid"] = self.trackerid
		if (announceEvent != "None"):
			qParams["event"] = announceEvent

		response = bdecode(requests.get(self.announceData, params = qParams).content)
		# TO-DO
		# Handle other info received from response
		if ('tracker id' in response.keys()):
			self.trackerid = response['tracker id']
		self.announceInterval = response['interval']

		# TO-DO
		# Handle new peer list from reannouncing

		# Instantiate a peer manager for this torrent file
		if (announceEvent == "started"): # Needs to be created only once
			self.changeStatus("Creating peer manager for this torrent")
			self.pManager = pm.peerManager(response['peers'], self)

		# Lastly start the timer
		self.announceTimer = time.monotonic()

	# Print Status
	def printStatus(self):
		print("TORRENT MANAGER [{}]".format(self.announceInterval - self.elapsed))
		for i in range(len(self.statusList)):
			print("[{}]".format(self.statusList[i]), end='')
			self.statusList[i] = ""
		print("")

	def loop(self):
		self.announce()
		while(self.shouldLoop):
			# Handle announcing
			if (self.announceTimer):
				self.elapsed = time.monotonic() - self.announceTimer
				if (self.elapsed >= self.announceInterval):
					self.announceTimer = 0
			if (self.announceTimer == 0):
				bdown = self.pieManager.getBytesDownloaded()
				# Get bytes downloaded from pieceManager, left is (total - downloaded), event is empty for intermediate announces
				self.announce(bdown, "None")

			# _=os.system("cls")
			if (self.DISPLAY_STATUS):
				self.printStatus()
			self.pieManager.loop()
			self.pManager.loop()
			time.sleep(1)
			#self.shouldLoop = 0
