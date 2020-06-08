import time
import socket
import struct
import colorama
import logging
import messages
import bitstring

# Globals
colorama.init()
DEFAULT_TIMEOUT_VALUE = 5
PSTRLEN = 19
PSTR = "BitTorrent protocol"

# Peer class representing every peer and it's attributes
class Peer:
	def __init__(self, ip, port, torMan, pieMan):
		self.ip = ip
		self.port = int(port)
		self.sock = None
		self.isGoodPeer = 0
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

		self.tManager = torMan
		self.pieManager = pieMan

	# Establish TCP connection with peer
	def connect(self):
		try:
			self.sock = socket.create_connection((self.ip, self.port), DEFAULT_TIMEOUT_VALUE)
			return 0

		except socket.timeout:
			print("\033[31mSocket timed out!\033[39m")
			self.sock.close()
			return -1

		except socket.error:
			print("\033[31mConnection error!\033[39m")
			self.sock.close()
			return -1

	# Send a message to peer
	def send_msg(self, msg):
		try:
			self.sock.send(msg)

		except Exception as e:
			logging.error("\033[91mFailed to send message!\033[0m")

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
				print("No data received - Timed out.")
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
			print("Decoded response:")
			print("\033[92mInfo Hash: {}, Length: {}\033[0m".format(handshake_recv.infoHash, len(handshake_recv.infoHash)))
			print("\033[92mPeer ID: {}, Length: {}\033[0m".format(handshake_recv.peer_id, len(handshake_recv.peer_id)))

			# Drop connection if hashes don't match
			if handshake_recv.infoHash != self.tManager.infoHash:
				print("\033[91m]Info Hashes don't match. Dropping Connection\033[0m")
				return -1
			# Update read_buffer with the next message to be read
			self.read_buffer = self.read_buffer[handshake_recv.total_length:]
			# print("Updated read_buffer: {}".format(self.read_buffer))
			# Set isGoodPeer = 1 indicating completion of handshake
			self.isGoodPeer = 1

		except Exception:
			logging.exception("\033[91mError sending or receiving Handshake message.\033[0m")
			self.sock.close()
			return -1

	# Returns true if message is keepAlive, False otherwise
	def check_for_keepAlive(self):
		print("\033[93mChecking for KeepAlive\033[0m")
		try:
			keep_alive = messages.KeepAlive.decode(self.read_buffer)
		except messages.WrongMessageException:
			return False
		except Exception as e:
			print("\033[91m{}\033[0m".format(e))

		self.read_buffer = self.read_buffer[keep_alive.total_length:]
		return True

	# Is this client choking the peer?
	def am_choking(self):
		return self.state['am_choking']

	# Is this client unchoking the peer?
	def am_unchoking(self):
		return not self.am_choking()

	# Is peer choking this client?
	def is_choking(self):
		return self.state['peer_choking']

	# Is this client unchoked?
	def is_unchoked(self):
		return not self.is_choking()

	# Is the peer interested in this client?
	def is_interested(self):
		return self.state['peer_interested']

	# Is this client interested?
	def am_interested(self):
		return self.state['am_interested']

	# Peer is choking this client
	def set_choke(self):
		self.state['peer_choking'] = True

	# Peer has unchoked this client
	def set_unchoke(self):
		self.state['peer_choking'] = False

	# Peer is interested in this client
	def set_interested(self):
		self.state['peer_interested'] = True
		# If this client is choking the peer, first unchoke the peer and send him an unchoke message
		if self.am_choking():
			unchoke = messages.UnChoke().encode()
			self.send_msg(unchoke)

	# Peer is not interested in this client
	def set_not_interested(self):
		self.state['peer_interested'] = False

	# If peer sends a have message, set the corresponding piece to be true in the self.pieces BitArray
	def handle_have(self, msg):
		self.pieces[msg.piece_index] = True
		print("\033[92mCurrent bitfield: {}\033[0m".format(self.pieces))
		# If peer is not choking this client and this client is not interested, send peer an interested message
		if self.is_choking() and not self.state['am_interested']:
			interested = messages.Interested().encode()
			self.send_msg(interested)
			self.state['am_interested'] = True

	# Set pieces if client receives a bitfield message
	def handle_bitfield(self, msg):
		# bitfield is of type messages.BitField
		try:
			self.pieces = msg.bitfield
			print("\033[92mBitfield Message: {}\033[0m".format(self.pieces))
		except Exception as e:
			print("\033[91m{}\033[0m".format(e))
		# If peer is not choking this client and this client is not interested, send peer an interested message
		if self.is_choking() and not self.state['am_interested']:
			interested = messages.Interested().encode()
			self.send_msg(interested)
			self.state['am_interested'] = True

	# Gets messages from read_buffer
	def get_messages(self):
		# If the peer is a good peer and message is not a keepAlive message
		if self.isGoodPeer and not self.check_for_keepAlive():
			# Get payload length from the first 4 bytes of the read buffer
			payload_length, = struct.unpack("!I", self.read_buffer[:4])
			# print("\033[92mPayload Length: {}\033[0m".format(payload_length))
			total_length = payload_length + 4

			# # If message in buffer is less than total length of expected message, break
			# if len(self.read_buffer) < total_length:
			# 	return
			# else:
			# Read message till total length and update read buffer to resume from end of last message
			payload = self.read_buffer[:total_length]
			# print("Raw Payload: {}".format(payload))
			self.read_buffer = self.read_buffer[total_length:]
			print("Updated read_buffer: {}".format(self.read_buffer))

			# Sends payload to the message dispatcher which returns an appropriate parsed message object
			m = messages.MessageDispatcher(payload).dispatch()
			return m

	# Function to check if the received messages obj is an instance of one of the 9 possible message types
	def parse_message(self, msg: messages.Message):
		if isinstance(msg, messages.Choke):
			print("\033[96mFound Choke Message\033[0m")
			self.set_choke()

		elif isinstance(msg, messages.UnChoke):
			print("\033[96mFound UnChoke Message\033[0m")
			self.set_unchoke()

		elif isinstance(msg, messages.Interested):
			print("\033[96mFound Interested Message\033[0m")
			self.set_interested()

		elif isinstance(msg, messages.NotInterested):
			print("\033[96mFound NotInterested Message\033[0m")
			self.set_not_interested()

		elif isinstance(msg, messages.Have):
			print("\033[96mFound Have Message\033[0m")
			self.handle_have(msg)

		elif isinstance(msg, messages.BitField):
			print("\033[96mFound Bitfield Message\033[0m")
			self.handle_bitfield(msg)

		else:
			logging.error("\033[91mMessage not recognized.\033[0m")

	# Main loop
	def mainLoop(self):
		# Connect to peer and handshake, close connection and thread otherwise
		if self.connect() == -1 or self.handshake() == -1:
			print("\033[91mThread Closed.\033[0m")
			return

		while len(self.read_buffer) > 4:
			self.read_buffer += self.read_from_socket()
			msg = self.get_messages()
			self.parse_message(msg)

		print("\033[95mFinal Bitstring: {}\033[0m".format(self.pieces.bin))
		print("\033[95mDone.\033[0m")

if __name__ == "__main__":
	print("Not supposed to run this way!")
