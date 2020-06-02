from bcoding import bencode, bdecode

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

		with open(filepath, "rb") as f:
			torrent = bdecode(f)
			self.announce = torrent['announce']
			if('length' in torrent['info'].keys()):
				#Single file
				self.length = torrent['info']['length']
				self.name = torrent['info']['name']
				self.pieceLength = torrent['info']['piece length']
				self.pieces = torrent['info']['pieces']
				for index in range(0, len(self.pieces), 20):
					self.pieceHashes.append(self.pieces[index:index + 20])
					#print(self.pieceHashes[index % 20])
			else:
				#Multiple files
				print("Multi-file torrents not supported!")

#Testing
tor1 = TorrentFile("Ahiru33.mkv.torrent")
print(tor1.pieceHashes)