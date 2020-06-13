import bitstring
import math
import colorama

colorama.init()

class Piece:
	"""
	index - pieceIndex which this piece object represents
	torrentLength - length of the entire torrent (sum of length of all files if multiple files)
	pieceLength - length of a single piece as specified in the torrent file
	isEmpty - Whether this piece is an empty piece
	isLastPiece - Whether this piece is the last piece of the torrent file (Needs to be handled specifically)
	"""
	def __init__(self, index, torrentLength, pieceLength, isEmpty, isLastPiece):
		self.index = index
		self.block_size = 2**14
		self.last_block_size = self.block_size
		self.isEmpty = isEmpty
		self.isLastPiece = isLastPiece

		self.blocks_downloaded = 0
		self.latest_block_index = 0

		if (isLastPiece == 0):
			self.piece_size = pieceLength
			if ((self.piece_size % self.block_size) == 0):
				self.number_of_blocks = int(self.piece_size / self.block_size)
			else:
				print("\033[31m<{}>Weird pieceLength(of none-last index piece)! Not able to divide in even no. of blocks\033[0m".format(index))
		else:
			# Handle the last piece separately
			if (torrentLength % pieceLength): # Last piece is smaller than pieceLength
				self.piece_size = torrentLength % pieceLength
			else: # Last piece is also exactly equal to pieceLength (Rare Case)
				self.piece_size = pieceLength

			if(self.piece_size % self.block_size): # Last block of this piece will be smaller than other blocks
				self.number_of_blocks = math.ceil(float(self.piece_size) / self.block_size)
				self.last_block_size = self.piece_size % self.block_size # last_block_size is updated as needed
			else: # All blocks are of equal size in this piece
				self.number_of_blocks = int(self.piece_size / self.block_size)

		self.datalist = [0 for i in range(self.number_of_blocks)]
		self.blocks = [0 for i in range(self.number_of_blocks)]

	def makePiece(self, block_offset, block_data):
		self.datalist[int(block_offset / self.block_size)] = block_data

	def complete_piece(self):
		final_data = b''
		final_data = final_data.join(self.datalist)
		# hex_data = bitstring.BitArray(final_data)

		return final_data
