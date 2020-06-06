from bcoding import bencode, bdecode
import hashlib
import requests
import struct
import socket
import random

import peerManager as pm

class torrentManager:
	def __init__(self, torrentpath):
		self.torrentpath = torrentpath
		self.announce = ""
		self.infoHash = ""
		self.pieceHashes = []
		self.pieceLength = 0
		self.length = 0
		self.name = ""
		self.pieces = ""
		self.local_peer_id = bytes("-KC0010-" + str(random.randint(100000000000, 999999999999)), 'utf-8')

		# Open .torrent file and decode data
		with open(torrentpath, "rb") as f:
			torrent = bdecode(f)

		# Single file
		self.announce = torrent['announce']
		if('length' in torrent['info'].keys()):
			self.length = torrent['info']['length']
			self.name = torrent['info']['name']
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
		print("Creating peer manager for this torrent")
		self.pManager = pm.peerManager(response['peers'], self)

	# Timer for re-announce
	def loop(self):
		pass
