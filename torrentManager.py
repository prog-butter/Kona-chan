from bcoding import bencode, bdecode
import hashlib
import requests
import struct
import socket
import random
import threading
import os
import time

import peerManager as pm
import pieceManager as piem
import file as f

class torrentManager:
	def __init__(self, torrentpath):
		self.torrentpath = torrentpath
		self.announce = ""
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

		# Open .torrent file and decode data
		with open(torrentpath, "rb") as f:
			torrent = bdecode(f)

		# Single file
		self.announce = torrent['announce']
		if('length' in torrent['info'].keys()):
			self.length = torrent['info']['length']
			self.name = torrent['info']['name']
			# self.files.append(f.File(torrent['info']['name'], torrent['info']['name'], torrent['info']['length']))
			self.pieceLength = torrent['info']['piece length']
			self.pieces = torrent['info']['pieces']
			for index in range(0, len(self.pieces), 20):
				self.pieceHashes.append(self.pieces[index:index + 20])

			print("Torrent has {} pieces".format(len(self.pieceHashes)))
			# Calculate infohash
			encoded = bencode(torrent['info'])
			m = hashlib.sha1(encoded)
			self.infoHash = m.digest()

		else:
			# TO-DO
			# Multiple files
			print("Multi-file torrents not supported!")

	def initialAnnounce(self):
		print("Getting ready to send initial announce")
		qParams = {
			"info_hash": self.infoHash,
			"peer_id": self.local_peer_id,
			"port": "6882",
			"uploaded": "0",
			"downloaded": "0",
			"left": self.length,
			"compact": "1",
			"event": "started"
		}
		response = bdecode(requests.get(self.announce, params = qParams).content)
		# TO-DO
		# Handle other info received from response

		# Instantiate a peer manager for this torrent file
		print("Creating peer manager and piece manager for this torrent")
		self.pieManager = piem.pieceManager(self)
		self.pManager = pm.peerManager(response['peers'], self)

	# Timer for re-announce
	def loop(self):
		while(self.shouldLoop):
			_=os.system("cls")
			self.pieManager.loop()
			self.pManager.loop()
			time.sleep(2)
			#self.shouldLoop = 0
