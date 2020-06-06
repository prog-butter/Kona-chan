import time
import socket
import struct
import colorama
import logging
import messages

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
		self.pieces = []
		self.read_buffer = b''
		self.state = {
			"am_choking" = 1
			"am_interested" = 0
			"peer_choking" = 1
			"peer_interested" = 0
		}

		self.tManager = torMan
		self.pieManager = pieMan

	# Establish TCP connection with peer
	def connect(self):
		try:
			self.sock = socket.create_connection((self.ip, self.port), DEFAULT_TIMEOUT_VALUE)
			self.sock.setblocking(False)
			self.isGoodPeer = 1

		except socket.timeout:
			print("\033[31mSocket timed out!\033[39m")
			self.isGoodPeer = 0

		except socket.error:
			print("\033[31mConnection error!\033[39m")
			self.isGoodPeer = 0

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

			except Exception:
				logging.exception("Recieve failed.")
				break

		return data

	# Do hanshake with peer
	def handshake(self):
		try:
			# Send handshakeString for BitTorrent Protocol
			handshake_msg = messages.Handshake(self.tManager.infoHash, self.tManager.local_peer_id).encode()
			print("Sending handshakeString: <{}>".format(handshakeString))
			self.send_msg(handshake_msg)

		except Exception:
			logging.exception("Error sending Handshake message.")

	# Gets messages from read_buffer
	def get_messages(self):
		# Till read buffer is not empty (only contains length header) and the peer is a good peer
		while len(self.read_buffer) > 4 and self.isGoodPeer:
			# Get payload length from the first 4 bytes of the read buffer
			payload_length = struct.unpack("!I", self.read_buffer[:4])
			total_length = payload_length + 4

			# If message in buffer is less than total length of expected message, break
			if len(self.read_buffer) < total_length:
				break
			else:
				# Read message till total length and update read buffer to resume from end of last message
				payload = self.read_buffer[:total_length]
				self.read_buffer = self.read_buffer[total_length:]

			# Sends payload to the message dispatcher which returns an appropriate parsed message object
			m = messages.MessageDispatcher(payload).dispatch()
			return m

	# Main loop
	def mainLoop(self):
		# Connect to peer
		Peer peer;
		peer.connect()
		# Perform handshake
		peer.handshake()
		# Read from socket and fill buffer
		peer.read_buffer += peer.read_from_socket()
		# Get messages from the buffer
		peer.get_messages()


if __name__ == "__main__":
	print("Not supposed to run this way!")
