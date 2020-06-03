#!/usr/bin/env python3
from bcoding import bencode, bdecode
import hashlib
import requests
import random
import struct
import socket

# Globals
local_peer_id = "-KC0010-" + str(random.randint(100000000000, 999999999999))

# Peer class
class Peer:
	def __init__(self, ip, port):
		self.ip = ip
		self.port = int(port)

# Connect to a peer
class Connect:
	def __init__(self, peer, infoHash):
		try:
			# Establish TCP connection with peer
			s = socket.create_connection((peer.ip, peer.port), 5)

			# Send handshakeString for BitTorrent Protocol
			handshakeString = bytes(chr(19) + "BitTorrent protocol" + 8*chr(0), 'utf-8') + infoHash + bytes(local_peer_id, 'utf-8')
			print(handshakeString)
			s.send(handshakeString)

			"""
			1. Put each peer on it's own thread
			2. After handshake, peer will send an <id=5> packet telling which pieces that peer has. This message might not come at once.
				(NEED TO HANDLE THIS) Keep reading till complete message is received
			"""

			# Receive handshakeString from Peer
			handshakeResponse = s.recv(1 + 19 + 8 + 20 + 20)
			if(len(handshakeResponse) == 0):
				print("Ignoring empty reply")
			else:
				while(len(handshakeResponse) != 0):
					print("\n")
					print(handshakeResponse, end = '\n\n')
					protLen = struct.unpack_from("B", handshakeResponse, 0)[0]
					print(protLen)

					protName = handshakeResponse[1:20].decode('utf-8') #protName is 19 bytes
					print(protName, end="*\n")

					protExt = struct.unpack_from("8s", handshakeResponse, 20)[0]
					print(protExt)

					protHash = struct.unpack_from("20s", handshakeResponse, 28)[0]
					print("InfoHash: {}".format(infoHash))
					print(protHash)
					if(infoHash == protHash):
						print("HASHES MATCH!")
					else:
						print("DIFFERENT HASHES!")

					protID = struct.unpack_from("20s", handshakeResponse, 48)[0]
					print(protID)

					handshakeResponse = s.recv(2048)
					lensecond = (len(handshakeResponse) - 5) * 8
					print("length of second message: {}".format(lensecond))
					if(len(handshakeResponse) == 0):
						print("Nothing to read from this peer after initial receive")

		except socket.timeout:
			print("Socket timed out!")

		except socket.error:
			print("Connection error.")

		except Exception as e:
			print(e)

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
			print("No. of pieces: {}".format(len(self.pieceHashes)))
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
		"peer_id": local_peer_id,
		"port": "6882",
		"uploaded": "0",
		"downloaded": "0",
		"left": self.length,
		"compact": "1"
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
	tor1 = TorrentFile("Ahiru34.mkv.torrent")
	tor1.parsePeers()
	for peer in tor1.peerList:
		print("IP: {}, Port: {}".format(peer.ip, peer.port))
		Connect(peer, tor1.infoHash)


if __name__ == "__main__":
	main()
