#!/usr/bin/env python3
from bcoding import bencode, bdecode
import hashlib
import requests
import secrets
import struct
import socket

# Peer class
class Peer:
	def __init__(self, ip, port):
		self.ip = ip
		self.port = port

# Parsing the .torrent file
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
		self.peerList = []

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

	def parsePeers(self):
		qParams = {
		"info_hash": self.infoHash,
		"peer_id": self.peer_id,
		"port": "6881",
		"uploaded": "0",
		"downloaded": "0",
		"left": self.length,
		"compact": "0"
		}
		# response = bdecode(requests.get(self.announce, params = qParams).content)
		response = bdecode(requests.get(self.announce, params = qParams).content)
		peers = response['peers']
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
			self.peerList.append(Peer(ip, port))

#Testing
def main():
	tor1 = TorrentFile("Ahiru33.mkv.torrent")
	tor1.parsePeers()
	for peer in tor1.peerList:
		print("IP: {}, Port: {}".format(peer.ip, peer.port))

if __name__ == "__main__":
	main()
