import bitstring
import hashlib
import os
import time

import piece as p

class pieceManager:
	def __init__(self, torMan):
		self.tManager = torMan
		self.pieceFreq = {}
		self.numPieces = len(self.tManager.pieceHashes)
		for i in range(self.numPieces):
			self.pieceFreq[i] = 0

		self.pieceQueue = []
		self.createdInitialQueue = 0
	"""
	All methods get called by peers
	"""

	# Get bitfield from peers
	def submitBitfield(self, bitfield):
		bfBin = bitfield.bin
		for i in range(self.numPieces):
			if(bfBin[i] == '1'):
				self.pieceFreq[i] += 1

	# Return piece index to download
	def getPiece(self, bitfield):
		bfBin = bitfield.bin
		if(len(self.pieceQueue) != 0):
			indexToReturn = 0
			for indexToReturn in range(len(self.pieceQueue)):
				if(bfBin[self.pieceQueue[indexToReturn].index] == '1'):
					return self.pieceQueue.pop(indexToReturn)

		# Return an empty piece
		return p.Piece(0, 0, 1)

	# Get piece from peer
	# Write to disk if hashcheck matches otherwise add piece back to queue
	def submitPiece(self, piece):
		# Check download piece with hash
		m = hashlib.sha1(piece.data)
		if(self.tManager.pieceHashes[piece.index] is m.digest()):
			print("Do shit")
			# TO-DO
			# Write piece to disk (Only works for single file for now)
			if(os.path.isfile(self.tManager.files[0].filepath)): #file already exists
				f = open(self.tManager.files[0].filepath, "r+b")
			else: #file doesn't exist already
				f = open(self.tManager.files[0].filepath, "wb")

			f.seek(piece.index * self.tManager.pieceLength)
			f.write(piece.data)
			f.close()

		else:
			# Return piece back to queue
			self.pieceQueue.append(piece)

	def loop(self):
		print("pieceManager loop")
		# TO-DO
		# Form initial work queue: Add all pieces to queue (Run once)
		if(self.createdInitialQueue == 0):
			# Wait for sometime to receive bitfield messages
			time.sleep(20)
			print("pieceFreq:")
			with self.tManager.piemLock:
				print(self.pieceFreq)
				# Get piece indexes that is not available with any peer (needs to be placed at end of work queue)
				unavailablePieceIndexes = []
				for key in self.pieceFreq:
					if(self.pieceFreq[key] == 0):
						unavailablePieceIndexes.append(key)
				#tempPieceFreq = {k: v for k, v in sorted(self.pieceFreq.items(), key=lambda item: item[1])}
				sortedKeys = list({k: v for k, v in sorted(self.pieceFreq.items(), key=lambda item: item[1])}.keys())

				self.pieceQueue = []
				# Loop through sortedKeys (sorted in increasing order of piece freq)
				for ind in sortedKeys:
					if(ind not in unavailablePieceIndexes):
						self.pieceQueue.append(p.Piece(ind, self.tManager.pieceLength, 0))

				# Add remaining piece indexes
				for ind in unavailablePieceIndexes:
					self.pieceQueue.append(p.Piece(ind, self.tManager.pieceLength, 0))

				#self.createdInitialQueue = 1
				print("pieceQueue")
				for pie in self.pieceQueue:
					print(pie.index, end=", ")

				print("")
