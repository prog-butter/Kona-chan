import time
import socket
import struct
import colorama
import logging
import messages
import bitstring

# Globals
colorama.init()
DEFAULT_TIMEOUT_VALUE = 3
PSTRLEN = 19
PSTR = "BitTorrent protocol"

# Peer class representing every peer and it's attributes
class Peer:
	def __init__(self, ip, port, torMan):
		self.ip = ip
		self.port = int(port)
		self.sock = None
		self.isGoodPeer = 1
		self.pieces = bitstring.BitArray(len(torMan.pieceHashes))
		self.read_buffer = b''
		self.running = True
		self.state = {
			# This client is choking the peer
			"am_choking": 1,
			# This client is interested in the peer
			"am_interested": 0,
			# Peer is choking this client
			"peer_choking": 1,
			# Peer is interested in this client
			"peer_interested": 0
		}

		# Whether this peer has a piece to download or not
		self.hasPiece = 0
		self.currentPiece = None
		# self.currentBlockOffset = -1
		# self.blocks_downloaded = 0
		self.tManager = torMan
		self.pieManager = self.tManager.pieManager
		self.sentRequest = 0
		self.pipeline = []

		#Status
		"""
		Oldest Status (lower index) → Newest Status (higher index)
		"""
		self.statusList = []
		for _ in range(self.tManager.NUM_STATUS):
			self.statusList.append("None")

		self.changeStatus("I am born!")

	#Change Status
	def changeStatus(self, newStatus):
		for i in range(len(self.statusList) - 1):
			self.statusList[i] = self.statusList[i + 1]

		self.statusList[len(self.statusList) - 1] = newStatus

	# Print Status
	def printStatus(self):
		print("{}:{}".format(self.ip, self.port), end='')
		for s in self.statusList:
			print("[{}]".format(s), end='')
		for s in self.statusList:
			s = ""
		print("")

	# Establish TCP connection with peer
	def connect(self):
		self.changeStatus("Attempting to establish TCP connection with peer")
		try:
			self.sock = socket.create_connection((self.ip, self.port), DEFAULT_TIMEOUT_VALUE)
			return 0

		except socket.timeout:
			#print("\033[31mSocket timed out!\033[39m")
			self.isGoodPeer = 0
			self.changeStatus("\033[31mSocket timed out!\033[0m")
			self.sock.close()
			return -1

		except socket.error:
			#print("\033[31mConnection error!\033[39m")
			self.isGoodPeer = 0
			self.changeStatus("\033[31mConnection error!\033[0m")
			self.sock.close()
			return -1

	# Send a message to peer
	def send_msg(self, msg):
		try:
			self.sock.send(msg)

		except Exception as e:
			self.running = False
			self.changeStatus("\033[91mFailed to send message!\033[0m")
			print("{} [IP: {}, Port: {}]".format(e, self.ip, self.port))

	# Reads from socket and returns the received data in bytes form
	def read_from_socket(self):
		data = b''
		while True:
			try:
				buff = self.sock.recv(4096)
				if len(buff) <= 0:
					break

				data += buff

			except socket.timeout as e:
				err = e.args[0]
				#print("No data received - Timed out.")
				self.changeStatus("No data received - Timed out.")
				break

			except Exception:
				logging.exception("\033[91mRecieve failed.\033[0m")
				break

		return data

	# Do hanshake with peer
	def handshake(self):
		try:
			# Send handshakeString for BitTorrent Protocol
			handshake_msg = messages.Handshake(self.tManager.infoHash, self.tManager.local_peer_id).encode()
			self.send_msg(handshake_msg)

			# Receive handshake message
			self.read_buffer += self.read_from_socket()
			# print("Raw Handshake response:")
			# print(self.read_buffer)
			handshake_recv = messages.Handshake.decode(self.read_buffer)
			#print("Decoded response:")
			#print("\033[92mInfo Hash: {}, Length: {}\033[0m".format(handshake_recv.infoHash, len(handshake_recv.infoHash)))
			#print("\033[92mPeer ID: {}, Length: {}\033[0m".format(handshake_recv.peer_id, len(handshake_recv.peer_id)))
			self.changeStatus("Got handshake response")

			# Drop connection if hashes don't match
			if handshake_recv.infoHash != self.tManager.infoHash:
				#print("\033[91m]Info Hashes don't match. Dropping Connection\033[0m")
				self.changeStatus("\033[91m]Info Hashes don't match. Dropping Connection\033[0m")
				return -1
			# Update read_buffer with the next message to be read
			self.read_buffer = self.read_buffer[handshake_recv.total_length:]
			# print("Updated read_buffer: {}".format(self.read_buffer))
			# Set isGoodPeer = 1 indicating completion of handshake
			self.isGoodPeer = 1

			self.send_interested()
			self.send_unchoke()

		except Exception:
			self.isGoodPeer = 0
			print("\033[91mError sending or receiving Handshake message.\033[0m")
			self.sock.close()
			return -1

	# Returns true if message is keepAlive, False otherwise
	def check_for_keepAlive(self):
		#print("\033[93mChecking for KeepAlive\033[0m")
		self.changeStatus("\033[93mChecking for KeepAlive\033[0m")
		try:
			# print("Read Buffer: {}".format(self.read_buffer))
			keep_alive = messages.KeepAlive.decode(self.read_buffer)
		except messages.WrongMessageException:
			self.changeStatus("\033[91mNot a keepAlive message\033[0m")
			return False
		except Exception as e:
			#print("\033[91m{}\033[0m".format(e))
			self.changeStatus("\033[91m{}\033[0m".format(e))

		self.read_buffer = self.read_buffer[keep_alive.total_length:]
		self.changeStatus("\033[92mIs a keepAlive message\033[0m")
		return True

	# # Is this client choking the peer?
	# def am_choking(self):
	# 	return self.state['am_choking']

	# # Is this client unchoking the peer?
	# def am_unchoking(self):
	# 	return not self.am_choking()

	# Is peer choking this client?
	def is_choking(self):
		return self.state['peer_choking']

	# Is this client unchoked?
	def is_unchoked(self):
		return not self.is_choking()

	# # Is the peer interested in this client?
	# def is_interested(self):
	# 	return self.state['peer_interested']

	# Is this client interested?
	def am_interested(self):
		return self.state['am_interested']

	# Peer is choking this client
	def set_choke(self):
		self.state['peer_choking'] = True

	# Peer has unchoked this client
	def set_unchoke(self):
		self.state['peer_choking'] = False
		# self.send_interested()

	# # Peer is interested in this client
	# def set_interested(self):
	# 	self.state['peer_interested'] = True
	# 	# If this client is choking the peer, first unchoke the peer and send him an unchoke message
	# 	if self.am_choking():
	# 		unchoke = messages.UnChoke().encode()
	# 		self.send_msg(unchoke)

	# # Peer is not interested in this client
	# def set_not_interested(self):
	# 	self.state['peer_interested'] = False

	# Send interested message to peer
	def send_interested(self):
		interested = messages.Interested().encode()
		#print("\033[93mSending Interested Message to Peer IP: {}, Port: {}\033[0m".format(self.ip, self.port))
		self.changeStatus("\033[93mSending Interested Message to Peer\033[0m")
		self.send_msg(interested)
		self.state['am_interested'] = True

	def send_unchoke(self):
		try:
			self.changeStatus("\033[95mSending Unchoke Message to Peer\033[0m")
			unchoke = messages.UnChoke().encode()
			self.send_msg(unchoke)
			self.state['am_choking'] = False
		except Exception as e:
			print("\033[91m{}\033[0m".format(e))
			print("{} [IP: {}, Port: {}]".format(e, self.ip, self.port))

	# If peer sends a have message, set the corresponding piece to be true in the self.pieces BitArray
	def handle_have(self, msg):
		self.pieces[msg.piece_index] = True
		#print("\033[92mCurrent bitfield: {}\033[0m".format(self.pieces))
		# If peer is not choking this client and this client is not interested, send peer an interested message
		# if self.is_choking():
		# 	self.send_interested()

		# Send parsed have message to pieceManager
		with self.tManager.piemLock:
			self.pieManager.submitHaveMessage(msg.piece_index)

	# Set pieces if client receives a bitfield message
	def handle_bitfield(self, msg):
		# bitfield is of type messages.BitField
		try:
			self.pieces = msg.bitfield
			#print("\033[92mBitfield Message: {}\033[0m".format(self.pieces))
		except Exception as e:
			#print("\033[91m{}\033[0m".format(e))
			self.changeStatus("\033[91m{}\033[0m".format(e))
		# If peer is not choking this client and this client is not interested, send peer an interested message
		# if self.is_choking() and not self.state['am_interested']:
		# 	interested = messages.Interested().encode()
		# 	self.send_msg(interested)
		# 	self.state['am_interested'] = True

		# Submit bitfield to pieceManager
		with self.tManager.piemLock:
			#print("\033[93mSending bitfield to Piece Manager\033[0m")
			self.changeStatus("\033[93mSending bitfield to Piece Manager\033[0m")
			self.pieManager.submitBitfield(self.pieces)

	# If client is unchoked and interested, request message is sent
	def send_request(self, block_offset):
		try:
			# self.currentBlockOffset = block_offset
			# print("\033[92mChoking: {}, Interested: {}\033[0m".format(self.state['peer_choking'], self.state['am_interested']))
			#print("\033[93mSending Request Message [{}, {}] to Peer IP: {}, Port: {}\033[0m".format(self.currentPiece.index, block_offset, self.ip, self.port))
			if self.am_interested() and self.is_unchoked():
				self.changeStatus("\033[93mSending Request Message [{}, {}] to Peer IP: {}, Port: {}\033[0m".format(self.currentPiece.index, block_offset, self.ip, self.port))
				if block_offset == self.currentPiece.number_of_blocks - 1 and self.currentPiece.index == len(self.tManager.pieceHashes):
					# request = messages.Request(self.currentPiece.index, block_offset*self.currentPiece.block_size, self.currentPiece.last_block_size).encode()
					request = messages.Request(self.currentPiece.index, block_offset*self.currentPiece.block_size, 5).encode()

				request = messages.Request(self.currentPiece.index, block_offset*self.currentPiece.block_size, self.currentPiece.block_size).encode()
				self.send_msg(request)

		except Exception as e:
			print("\033[91m{}\033[0m".format(e))
			print("{} [IP: {}, Port: {}]".format(e, self.ip, self.port))

	# Receive a piece
	def handle_piece(self, msg):
		try:
			# If received piece has matching piece_index and block_offset values, download it
			if msg.piece_index == self.currentPiece.index:
				self.currentPiece.blocks[int(msg.block_offset/self.currentPiece.block_size)] = 1
				self.currentPiece.blocks_downloaded += 1
				self.currentPiece.makePiece(msg.block_offset, msg.block)
				self.changeStatus("Making piece [{}, {}]".format(msg.piece_index, int(msg.block_offset/self.currentPiece.block_size)))
				print("Making piece [{}, {}] [IP: {}, Port: {}]".format(msg.piece_index, int(msg.block_offset/self.currentPiece.block_size), self.ip, self.port))
				#print("\033[95mData so far: {}\033[0m".format(self.currentPiece.final_data))
				# Set that block as downloaded, increment downloaded blocks counter by 1, set hasPiece to 0 to receive new piece
				# print("\033[92mBlocks Downloaded: {}, Number of Blocks: {}\033[0m".format(self.currentPiece.blocks_downloaded, self.currentPiece.number_of_blocks))
		except Exception as e:
			print("\033[91m{}\033[0m".format(e))
			print("{} [IP: {}, Port: {}]".format(e, self.ip, self.port))

	# Gets messages from read_buffer
	def get_messages(self):
		# If the peer is a good peer and message is not a keepAlive message
		if self.isGoodPeer and not self.check_for_keepAlive():
			# Get payload length from the first 4 bytes of the read buffer
			payload_length, = struct.unpack("!I", self.read_buffer[:4])
			# print("\033[92mPayload Length: {}\033[0m".format(payload_length))
			total_length = payload_length + 4
			# Read message till total length and update read buffer to resume from end of last message
			payload = self.read_buffer[:total_length]
			# print("Raw Payload: {}".format(payload))
			self.read_buffer = self.read_buffer[total_length:]
			#print("Updated read_buffer: {}".format(self.read_buffer))

			# Sends payload to the message dispatcher which returns an appropriate parsed message object
			m = messages.MessageDispatcher(payload).dispatch()
			return m

	# Function to check if the received messages obj is an instance of one of the 9 possible message types
	def parse_message(self, msg: messages.Message):
		if isinstance(msg, messages.Choke):
			#print("\033[96mFound Choke Message [IP: {}, Port: {}]\033[0m".format(self.ip, self.port))
			self.changeStatus("\033[31mFound Choke Message\033[0m")
			self.set_choke()

		elif isinstance(msg, messages.UnChoke):
			#print("\033[95mFound UnChoke Message [IP: {}, Port: {}]\033[0m".format(self.ip, self.port))
			self.changeStatus("\033[95mFound UnChoke Message\033[0m")
			self.set_unchoke()

		elif isinstance(msg, messages.Interested):
			#print("\033[96mFound Interested Message [IP: {}, Port: {}]\033[0m".format(self.ip, self.port))
			self.changeStatus("\033[96mFound Interested Message\033[0m")
			self.set_interested()

		elif isinstance(msg, messages.NotInterested):
			#print("\033[96mFound NotInterested Message [IP: {}, Port: {}]\033[0m".format(self.ip, self.port))
			self.changeStatus("\033[96mFound NotInterested Message\033[0m")
			self.set_not_interested()

		elif isinstance(msg, messages.Have):
			#print("\033[96mFound Have Message [IP: {}, Port: {}]\033[0m".format(self.ip, self.port))
			self.changeStatus("\033[96mFound Have Message\033[0m")
			self.handle_have(msg)

		elif isinstance(msg, messages.BitField):
			#print("\033[96mFound Bitfield Message [IP: {}, Port: {}]\033[0m".format(self.ip, self.port))
			self.changeStatus("\033[96mFound Bitfield Message\033[0m")
			self.handle_bitfield(msg)

		elif isinstance(msg, messages.Piece):
			#print("\033[94mFound Piece Message [IP: {}, Port: {}]\033[0m".format(self.ip, self.port))
			self.changeStatus("\033[94mFound Piece Message [{}, {}]\033[0m".format(msg.piece_index, msg.block_offset))
			self.handle_piece(msg)

		else:
			logging.error("\033[91mMessage not recognized.\033[0m")
		# elif isinstance(msg, messages.Request):
		# 	print("\033[96mFound Request Message [IP: {}, Port: {}]\033[0m".format(self.ip, self.port))
		# 	self.handle_request(msg)
		#
		# elif isinstance(msg, messages.Cancel):
		# 	print("\033[96mFound Cancel Message [IP: {}, Port: {}]\033[0m".format(self.ip, self.port))
		# 	self.handle_cancel(msg)


	# Main loop
	def mainLoop(self):
		# Connect to peer and handshake, close connection and thread otherwise
		if self.connect() == -1 or self.handshake() == -1:
			#print("\033[91mThread Closed.\033[0m")
			self.changeStatus("\033[91mThread Closed.\033[0m")
			return

		while self.running:
			self.changeStatus("\033[92mAlive! ({})\033[0m".format(self.hasPiece))
			# WOW
			self.read_buffer += self.read_from_socket()
			while len(self.read_buffer) > 4:
				self.changeStatus("Reading messages from buffer")
				self.read_buffer += self.read_from_socket()
				msg = self.get_messages()
				self.parse_message(msg)
				# self.sentRequest = 0

			if not self.state['peer_choking']:
				# Ask for piece to download from pieceManager
				if(self.hasPiece == 0):
					with self.tManager.piemLock:
						self.changeStatus("Attempting to get a piece from pieceManager")
						self.currentPiece = self.pieManager.getPiece(self.pieces)
					if(self.currentPiece.isEmpty == 0): #Check if a valid piece was received
						self.hasPiece = 1
						self.changeStatus("Received piece index [{}] from pieceManager".format(self.currentPiece.index))
					elif (self.pieManager.createdQueue):
						# pieceQueue is empty, close connection with peer
						#print("\033[95mDone! Closing thread\033[0m")
						self.changeStatus("\033[95mDone! Closing thread\033[0m")
						self.running = False
						self.sock.close()
						return

				# Download if peer has a piece
				if(self.hasPiece):
					# If all blocks have been downloaded
					# print("\033[92mInside hasPiece if\033[0m")
					if self.currentPiece.blocks_downloaded == self.currentPiece.number_of_blocks:
						print("About to submit - {}".format(self.currentPiece.index))
						with self.tManager.piemLock:
							print("[{}: {}] ({}) <{}>".format(self.ip, self.port, self.currentPiece.index, self.currentPiece.complete_piece()))
							self.changeStatus("\033[92mSubmitting piece index: [{}]\033[0m".format(self.currentPiece.index))
							self.pieManager.submitPiece(self.currentPiece)
							self.currentPiece.blocks_downloaded = 0
						self.hasPiece = 0
						continue

					#Send request messages to download piece
					# if self.sentRequest == 0:
					for i in range(len(self.currentPiece.blocks)):
						if self.currentPiece.blocks[i] != 1:
							self.send_request(i)
						# self.sentRequest = 1
					# for i in range(len(self.currentPiece.blocks)):
					# 	if self.currentPiece.blocks[i] != 1:
					# 		self.send_request(i)
					# 		time.sleep(0.2)

			else:
				self.changeStatus("\033[91mBeing Choked.\033[0m")

if __name__ == "__main__":
	print("Not supposed to run this way!")
