import bitstring
import queue
import hashlib
import os

class pieceManager:
	def __init__(self, torMan):
		self.tManager = torMan
		self.pieceFreq = []
		self.numPieces = len(self.tManager.pieceHashes)
		for _ in range(self.numPieces):
			self.pieceFreq.append(0)

		self.pieceQueue = queue.Queue()
	"""
	All methods get called by peers
	"""

	# Get bitfield from peers
	def initialBitfield(self, bitfield):
		bfBin = bitfield.bin
		for i in range(self.numPieces):
			if(bfBin[i] == '1'):
				self.pieceFreq[i] += 1

	# Return piece index to download
	def getPiece(self):
		pass

	# Get piece from peer
	# Write to disk if hashcheck matches otherwise add piece back to queue
	def submitPiece(self, piece):
		# Check download piece with hash
		m = hashlib.sha1(piece.data)
		if(self.tManager.pieceHashes[piece.index] is m.digest()):
			print("Do shit")
			# TO-DO
			# Write piece to disk

		else:
			# Return piece back to queue
			self.pieceQueue.put(piece)

	def loop(self):
		print("pieceManager loop")
		# TO-DO
		# Add all pieces to queue (Run once)
