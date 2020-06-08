import bitstring

class Piece:
	def __init__(self, index, piecelength, isEmpty):
		self.index = index
		self.data = bitstring.BitArray(bytes = piecelength)
		self.isEmpty = isEmpty