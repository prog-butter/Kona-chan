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
	def __init__(self, ip, port, torMan, pieMan):
		self.ip = ip
		self.port = int(port)
		self.sock = None
		self.isGoodPeer = 0
		self.pieces = ""
		self.read_buffer = b''
		self.state = {
			"am_choking": 1,
			"am_interested": 0,
			"peer_choking": 1,
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

	# Gets messages from read_buffer
	def get_messages(self):
		# If the peer is a good peer
		if self.isGoodPeer:
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

	# Main loop
	def mainLoop(self):
		# Connect to peer and handshake, close connection and thread otherwise
		if self.connect() == -1 or self.handshake() == -1:
			print("\033[91mThread Closed.\033[0m")
			return

		while len(self.read_buffer) > 4:
			self.read_buffer += self.read_from_socket()
			msg = self.get_messages()

			if msg.message_id == 5:
				# Append bitstring to self.pieces
				self.pieces += msg.bitfield.bin
				print("\033[92mBitstring message of length: {}\033[0m".format(len(msg.bitfield.bin)))

			elif msg.message_id == 4:
				print("\033[92mHave piece index: {}\033[0m".format(msg.piece_index))
				# Convert existing bitstring to list
				pieceList = list(self.pieces)
				# Update corresponding piece_index to 1
				pieceList[msg.piece_index] = 1
				# Convert back to string and update self.pieces
				self.pieces = "".join(pieceList)

			print("Length of read_buffer: \033[93m{}\033[0m".format(len(self.read_buffer)))

		print("\033[95mFinal Bitstring Length: {}\033[0m".format(len(self.pieces)))
		print("\033[95mDone.\033[0m")

if __name__ == "__main__":
	print("Not supposed to run this way!")
