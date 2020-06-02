#!/usr/bin/env python3
from bcoding import bencode, bdecode
import hashlib
import requests
import secrets

#Parsing the .torrent file
class TorrentFile:
	def __init__(self, filepath):
		self.filepath = filepath
		self.announce = ""
		self.infoHash = ""
		self.pieceHashes = []
		self.pieceLength = 0
		self.length = 0
		self.name = ""
		self.pieces = ""
		self.peer_id = secrets.token_bytes(20)

		# Open .torrent file and decode data
		with open(filepath, "rb") as f:
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
				# print(self.pieceHashes[index % 20])

			# Calculate infohash
			encoded = bencode(torrent['info'])
			m = hashlib.sha1(encoded)
			self.infoHash = m.digest()

		else:
			# TO-DO
			# Multiple files
			print("Multi-file torrents not supported!")

	def getPeers(self):
		qParams = {
		"info_hash": self.infoHash,
		"peer_id": self.peer_id,
		"port": "6881",
		"uploaded": "0",
		"downloaded": "0",
		"left": self.length
		}
		response = bdecode(requests.get(self.announce, params = qParams).content)
		return response

#Testing
def main():
	tor1 = TorrentFile("Ahiru33.mkv.torrent")
	response = tor1.getPeers()
	
	# print(tor1.pieceHashes)

if __name__ == "__main__":
	main()
