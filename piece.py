import bitstring
import math

class Piece:
	def __init__(self, index, piecelength, isEmpty):
		self.index = index
		self.piece_size = piecelength
		self.block_size = 2**14
		self.number_of_blocks = int(math.ceil(float(self.piece_size) / self.block_size))
		self.datalist = [0 for i in range(self.number_of_blocks)]
		self.blocks = [0 for i in range(self.number_of_blocks)]
		self.isEmpty = isEmpty

	def makePiece(self, block_offset, block_data):
		self.datalist[block_offset] = block_data

	def complete_piece(self):
		final_data = b''
		final_data.join(self.datalist)

		return final_data
