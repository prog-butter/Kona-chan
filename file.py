import bitstring

class File:
	def __init__(self, filepath, name, length):
		self.filepath = filepath
		self.name = name
		self.length = length
		self.data = bitstring.BitString()