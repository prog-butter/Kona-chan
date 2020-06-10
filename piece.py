import bitstring
import math

class Piece:
	def __init__(self, index, piecelength, isEmpty):
		self.index = index
		self.piece_size = piecelength
		self.block_size = 2**14
		self.last_block_size = self.piece_size % self.block_size
		self.number_of_blocks = int(math.ceil(float(self.piece_size) / self.block_size))
		self.blocks_downloaded = 0
		self.datalist = [0 for i in range(self.number_of_blocks)]
		self.blocks = [0 for i in range(self.number_of_blocks)]
		self.isEmpty = isEmpty

	def makePiece(self, block_offset, block_data):
		self.datalist[int(block_offset/self.block_size)] = block_data

	def complete_piece(self):
		final_data = b''
		final_data = final_data.join(self.datalist)
		# hex_data = bitstring.BitArray(final_data)

		return final_data
