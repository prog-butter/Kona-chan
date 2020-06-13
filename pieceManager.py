import bitstring
import hashlib
import os
import time
import colorama

import piece as p

class pieceManager:
	def __init__(self, torMan, pieceList):
		colorama.init()
		self.tManager = torMan
		self.pieceFreq = {}
		self.numPieces = len(self.tManager.pieceHashes)
		for i in range(self.numPieces):
			self.pieceFreq[i] = 0

		self.pieceList = pieceList
		self.pieceQueue = [] # Store the pieces as a queue
		self.downloadedPieces = [] # To keep track of which pieces have been downloaded
		self.pieceQueueSize = len(self.tManager.pieceHashes)
		self.bytesDownloaded = 0

		#Add all pieces in order initially
		for p in self.pieceList:
			self.pieceQueue.append(p)
			self.downloadedPieces.append(0)

		self.updateTimer = time.monotonic()
		self.updateInterval = 30
		self.elapsed = 0

		#Status
		"""
		Oldest Status (lower index) → Newest Status (higher index)
		"""
		self.statusList = []
		for _ in range(5):
			self.statusList.append("None")

	#Change Status
	def changeStatus(self, newStatus):
		for i in range(len(self.statusList) - 1):
			self.statusList[i] = self.statusList[i + 1]

		self.statusList[len(self.statusList) - 1] = newStatus

	"""
	All methods get called by peers
	"""
	# Get Have messages from peer
	def submitHaveMessage(self, index):
		self.changeStatus("Received a have message [{}]".format(index))
		try:
			self.pieceFreq[index] += 1
		except Exception as e:
			self.changeStatus("\033[91m{}\033[0m".format(e))

	# Get bitfield from peers
	def submitBitfield(self, bitfield):
		self.changeStatus("Received a bitfield")
		try:
			bfBin = bitfield.bin
			for i in range(self.numPieces):
				if(bfBin[i] == '1'):
					self.pieceFreq[i] += 1
		except Exception as e:
			self.changeStatus("\033[91m{}\033[0m".format(e))

	# Return (to peer) the piece index to download
	def getPiece(self, bitfield):
		bfBin = bitfield.bin
		# An empty pieceQueue means either it hasn't been made yet or it's empty, in either case we return an empty piece
		if(len(self.pieceQueue) != 0):
			indexToReturn = 0
			for indexToReturn in range(len(self.pieceQueue)):
				if(bfBin[self.pieceQueue[indexToReturn].index] == '1'):
					self.changeStatus("Returning piece index [{}]".format(indexToReturn))
					return self.pieceQueue.pop(indexToReturn)

		# Return an empty piece
		return p.Piece(0, 0, 1)

	# Get piece from peer
	# Write to disk if hashcheck matches otherwise add piece back to queue
	def submitPiece(self, piece):
		self.changeStatus("Received a completely downloaded piece <{}>".format(piece.index))
		# Check download piece with hash
		m = hashlib.sha1(piece.complete_piece())
		print("Calculated Hash: {}".format(m.digest()))
		print("Actual Hash: {}".format(self.tManager.pieceHashes[piece.index]))
		if(self.tManager.pieceHashes[piece.index] == m.digest()):
			self.changeStatus("\033[92mHash Matched! [{}]\033[0m".format(piece.index))
			self.bytesDownloaded += piece.piece_size
			# Update downloadedPieces list
			self.downloadedPieces[piece.index] = 1

			# Figure out which file to write to
			# TO-DO

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

	# Return no. of bytes downloaded by this piece manager
	def getBytesDownloaded(self):
		return self.bytesDownloaded

	# Print Status
	def printStatus(self):
		print("[{}]PIECE MANAGER [{}] [D:{}]".format(self.pieceQueueSize, self.updateInterval - self.elapsed, (self.bytesDownloaded/1024**2)))
		for i in range(len(self.statusList)):
			print("[{}]".format(self.statusList[i]), end='')
			self.statusList[i] = ""
		print("")

	# Make sure this method is called from within a lock
	def isPieceIndexInQueue(self, index):
		for p in self.pieceQueue:
			if (p.index == index):
				return 1
		# Piece not in queue
		return 0

	# Make sure this method is called from within a lock
	# (IMP) Method assumes index is in queue
	def getPieceFromIndex(self, index):
		for p in self.pieceQueue:
			if (p.index == index):
				return p

	def loop(self):
		if (self.updateTimer):
			self.elapsed = time.monotonic() - self.updateTimer
			if (self.elapsed >= self.updateInterval):
				self.updateTimer = 0
		if (self.updateTimer == 0):
			with self.tManager.piemLock:
				self.pieceQueueSize = len(self.pieceQueue)
				#print(self.pieceFreq)
				# Get piece indexes that is not available with any peer (needs to be placed at end of work queue)
				unavailablePieceIndexes = []
				for key in self.pieceFreq:
					if(self.pieceFreq[key] == 0):
						unavailablePieceIndexes.append(key)

				# Sort piece indexes according to frequency (lower frequency pieces appear first)
				sortedKeys = list({k: v for k, v in sorted(self.pieceFreq.items(), key=lambda item: item[1])}.keys())

				self.updatedPieceQueue = []
				# Loop through sortedKeys (sorted in increasing order of piece freq)
				for ind in sortedKeys:
					if(ind not in unavailablePieceIndexes and self.downloadedPieces[ind] == 0): # Not already downloaded
						# Check if this piece is in queue (i.e. not already assigned to a peer)
						if (self.isPieceIndexInQueue(ind)):
							self.updatedPieceQueue.append(self.getPieceFromIndex(ind))

				# Add remaining piece indexes
				for ind in unavailablePieceIndexes:
					if (self.downloadedPieces[ind] == 0): # Not already downloaded
						# Check if this piece is in queue (i.e. not already assigned to a peer)
						if (self.isPieceIndexInQueue(ind)):
							self.updatedPieceQueue.append(self.getPieceFromIndex(ind))

				self.pieceQueue = self.updatedPieceQueue

				self.changeStatus("Updated pieceQueue")
				# End of lock


			# Lastly start the timer
			self.updateTimer = time.monotonic()
		# Timer block ends here
		with self.tManager.piemLock:
			self.pieceQueueSize = len(self.pieceQueue)

		if (self.tManager.DISPLAY_STATUS):
			self.printStatus()