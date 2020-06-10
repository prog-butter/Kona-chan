import bitstring
import hashlib
import os
import time
import colorama

colorama.init()

import piece as p

class pieceManager:
	def __init__(self, torMan):
		self.tManager = torMan
		self.pieceFreq = {}
		self.numPieces = len(self.tManager.pieceHashes)
		for i in range(self.numPieces):
			self.pieceFreq[i] = 0

		self.pieceQueue = []
		self.createdQueue = 0

		#Status
		self.ppStatus = "None"
		self.currentStatus = "None"
		self.previousStatus = "None"
		self.p3status = "None"
		self.p4status = "None"

	#Change Status
	def changeStatus(self, newStatus):
		self.p4status = self.p3status
		self.p3status = self.ppStatus
		self.ppStatus = self.previousStatus
		self.previousStatus = self.currentStatus
		self.currentStatus = newStatus

	"""
	All methods get called by peers
	"""
	# Get Have messages from peer
	def submitHaveMessage(self, index):
		self.changeStatus("Received a have message [{}]".format(index))
		self.pieceFreq[index] += 1

	# Get bitfield from peers
	def submitBitfield(self, bitfield):
		self.changeStatus("Received a bitfield")
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
					self.changeStatus("Return piece index [{}]".format(indexToReturn))
					self.changeStatus("Queue size: {}".format(len(self.pieceQueue)))
					return self.pieceQueue.pop(indexToReturn)


		# Return an empty piece
		return p.Piece(0, 0, 1)

	# Get piece from peer
	# Write to disk if hashcheck matches otherwise add piece back to queue
	def submitPiece(self, piece):
		self.changeStatus("Received a completely downloaded piece")
		# Check download piece with hash
		m = hashlib.sha1(piece.complete_piece())
		print("Calculated Hash: {}".format(m.digest()))
		print("Actual Hash: {}".format(self.tManager.pieceHashes[piece.index]))
		if(self.tManager.pieceHashes[piece.index] == m.digest()):
			self.changeStatus("\033[92mHash Matched! [{}]\033[0m".format(piece.index))
			# Write piece to disk (Only works for single file for now)
			try:
				if(os.path.isfile(self.tManager.files[0].filepath)): #file already exists
					f = open(self.tManager.files[0].filepath, "r+b")
				else: #file doesn't exist already
					f = open(self.tManager.files[0].filepath, "wb")

				f.seek(piece.index * self.tManager.pieceLength)
				f.write(piece.complete_piece())
				f.close()

			except Exception as e:
				print("\033[91m{}\033[0m".format(e))

		else:
			# Return piece back to queue
			self.changeStatus("\033[91mHash didn't match! ({}) Putting back in queue\033[0m".format(piece.index))
			self.pieceQueue.append(piece)

	def loop(self):
		#print("pieceManager loop")
		# TO-DO
		# Form initial work queue: Add all pieces to queue (Run once)
		# if(self.createdInitialQueue == 0):
			# Wait for sometime to receive bitfield messages
		#time.sleep(20)
		#print("pieceFreq:")
		if self.createdQueue == 0:
			with self.tManager.piemLock:
				#print(self.pieceFreq)
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
						if ind == len(self.tManager.pieceHashes) - 1:
							self.pieceQueue.append(p.Piece(ind, self.tManager.lastPieceLength, 0))
						self.pieceQueue.append(p.Piece(ind, self.tManager.pieceLength, 0))

				# Add remaining piece indexes
				for ind in unavailablePieceIndexes:
					if ind == len(self.tManager.pieceHashes) - 1:
						self.pieceQueue.append(p.Piece(ind, self.tManager.lastPieceLength, 0))
					self.pieceQueue.append(p.Piece(ind, self.tManager.pieceLength, 0))

				self.changeStatus("Created/Updated pieceQueue")
				self.createdQueue = 1
				# print("pieceQueue")
				# for pie in self.pieceQueue:
				# 	print(pie.index, end=", ")

				#print("")

		print("({}) pieceManager:[{}][{}][{}][{}][{}]".format(len(self.pieceQueue), self.p4status, self.p3status, self.ppStatus, self.previousStatus, self.currentStatus))
		self.p3status = self.p4status = self.ppStatus = self.previousStatus = self.currentStatus = ""
