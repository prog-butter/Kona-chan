#!/usr/bin/env python3
import struct
import bitstring
import logging
import colorama

# Globals
PSTR = b"BitTorrent protocol"
PSTR_LEN = len(PSTR)
colorama.init()

# Used to raise wrong message exceptions
class WrongMessageException(Exception):
    pass

# Class to parse message id and payload of received message and send it to appropriate message parser
class MessageDispatcher:
    def __init__(self, payload):
        # print("\033[93mStarting message dispatcher.\033[0m")
        self.payload = payload

    def dispatch(self):
        try:
            payload_length, message_id = struct.unpack("!IB", self.payload[:5])
            # print("\033[92mPayload length: {}\033[0m".format(payload_length))
            #print("\033[92mMessage ID: {}\033[0m".format(message_id))

        except:
            logging.exception("\033[91mError in unpacking message.\033[0m")
            # print("Payload: {}".format(self.payload))
            return None

        map_id_to_message = {
            0: Choke,
            1: UnChoke,
            2: Interested,
            3: NotInterested,
            4: Have,
            5: BitField,
            6: Request,
            7: Piece,
            8: Cancel,
            9: Port
        }

        if message_id not in list(map_id_to_message.keys()):
            raise WrongMessageException("\033[91mMessage ID not recognized.\033[0m")

        return map_id_to_message[message_id].decode(self.payload)

# Abstract base class - acts as a blueprint for all child classes
class Message:
    def encode(self):
        raise NotImplementedError()

    @classmethod
    def decode(cls, response):
        raise NotImplementedError()

class Handshake(Message):
    """
        Handshake = <pstrlen><pstr><reserved><info_hash><peer_id>
            - pstrlen = length of pstr (1 byte)
            - pstr = string identifier of the protocol: "BitTorrent protocol" (19 bytes)
            - reserved = 8 reserved bytes indicating extensions to the protocol (8 bytes)
            - info_hash = hash of the value of the 'info' key of the torrent file (20 bytes)
            - peer_id = unique identifier of the Peer (20 bytes)
        Total length = payload length = 49 + len(pstr) = 68 bytes (for BitTorrent v1)
    """
    payload_length = 68
    total_length = payload_length

    def __init__(self, infoHash, local_peer_id):
        super(Handshake, self).__init__()

        assert len(infoHash) == 20
        assert len(local_peer_id) == 20
        self.peer_id = local_peer_id
        self.infoHash = infoHash

    # Encode to form handshake request
    def encode(self):
        reserved = b'\x00' * 8
        handshake_msg = struct.pack("!B{}s8s20s20s".format(PSTR_LEN), PSTR_LEN, PSTR, reserved, self.infoHash, self.peer_id)
        return handshake_msg

    # Decode handshake response
    @classmethod
    def decode(cls, response):
        pstrlen, = struct.unpack("!B", response[:1])
        pstr, reserved, info_hash, peer_id = struct.unpack("!{}s8s20s20s".format(pstrlen), response[1:cls.total_length])
        return Handshake(info_hash, peer_id)

class KeepAlive(Message):
    """
        KEEP_ALIVE = <length>
            - payload length = 0 (4 bytes)
    """
    payload_length = 0
    total_length = 4

    def __init__(self):
        super(KeepAlive, self).__init__()

    def encode(self):
        return struct.pack("!I", payload_length)

    @classmethod
    def decode(cls, response):
        # print("Response: {}".format(response))
        payload_length = struct.unpack("!I", response[:cls.total_length])
        if payload_length != 0:
            raise WrongMessageException("\033[91mNot a KeepAlive Message\033[0m")

        return KeepAlive()

class Choke(Message):
    """
        CHOKE = <length><message_id>
            - payload length = 1 (4 bytes)
            - message id = 0 (1 byte)
    """
    message_id = 0
    chokes_me = True
    payload_length = 1
    total_length = 5

    def __init__(self):
        super(Choke, self).__init__()

    def encode(self):
        return struct.pack("!IB", self.payload_length, self.message_id)

    @classmethod
    def decode(cls, response):
        payload_length, message_id = struct.unpack("!IB", response[:cls.total_length])
        return Choke()

class UnChoke(Message):
    """
        UnChoke = <length><message_id>
            - payload length = 1 (4 bytes)
            - message id = 1 (1 byte)
    """
    message_id = 1
    chokes_me = False
    payload_length = 1
    total_length = 5

    def __init__(self):
        super(UnChoke, self).__init__()

    def encode(self):
        return struct.pack("!IB", self.payload_length, self.message_id)

    @classmethod
    def decode(cls, response):
        payload_length, message_id = struct.unpack("!IB", response[:cls.total_length])
        return UnChoke()

class Interested(Message):
    """
        INTERESTED = <length><message_id>
            - payload length = 1 (4 bytes)
            - message id = 2 (1 byte)
    """
    message_id = 2
    interested = True
    payload_length = 1
    total_length = 5

    def __init__(self):
        super(Interested, self).__init__()

    def encode(self):
        # print("\033[92mIn Message Dispatcher - Interested Message\033[0m")
        return struct.pack("!IB", self.payload_length, self.message_id)

    @classmethod
    def decode(cls, response):
        payload_length, message_id = struct.unpack("!IB", response[:cls.total_length])
        return Interested()

class NotInterested(Message):
    """
        NOT INTERESTED = <length><message_id>
            - payload length = 1 (4 bytes)
            - message id = 3 (1 byte)
    """
    message_id = 3
    interested = False
    payload_length = 1
    total_length = 5

    def __init__(self):
        super(NotInterested, self).__init__()

    def encode(self):
        return struct.pack("!IB", self.payload_length, self.message_id)

    @classmethod
    def decode(cls, response):
        payload_length, message_id = struct.unpack("!IB", response[:cls.total_length])
        return NotInterested()

class Have(Message):
    """
        HAVE = <length><message_id><piece_index>
            - payload length = 5 (4 bytes)
            - message_id = 4 (1 byte)
            - piece_index = zero based index of the piece (4 bytes)
    """
    message_id = 4
    payload_length = 5
    total_length = 9

    def __init__(self, piece_index):
        super(Have, self).__init__()
        self.piece_index = piece_index

    def encode(self):
        return struct.pack("!IBI", self.payload_length, self.message_id, self.piece_index)

    @classmethod
    def decode(cls, response):
        payload_length, message_id, piece_index = struct.unpack("!IBI", response[:cls.total_length])
        return Have(piece_index)

class BitField(Message):
    """
        BITFIELD = <length><message id><bitfield>
            - payload length = 1 + bitfield_size (4 bytes)
            - message id = 5 (1 byte)
            - bitfield = bitfield representing downloaded pieces (bitfield_size bytes)
    """
    message_id = 5

    # bitfield is bitstring.BitArray
    def __init__(self, bitfield):
        super(BitField, self).__init__()
        self.bitfield = bitfield
        self.bitfield_as_bytes = bitfield.tobytes()
        self.bitfield_length = len(self.bitfield_as_bytes)
        self.payload_length = 1 + self.bitfield_length
        self.total_length = 4 + self.payload_length

    def encode(self):
        return struct.pack("!IB{}s".format(self.bitfield_length), self.payload_length, self.message_id, self.bitfield_as_bytes)

    @classmethod
    def decode(cls, response):
        # print("\033[93mIn BitField Message Parser.\033[0m")
        payload_length, message_id = struct.unpack("!IB", response[:5])
        bitfield_length = payload_length - 1
        raw_bitfield, = struct.unpack("!{}s".format(bitfield_length), response[5: 5 + bitfield_length])
        bitfield = bitstring.BitArray(bytes = bytes(raw_bitfield))
        return BitField(bitfield)

class Request(Message):
    """
        REQUEST = <length><message id><piece index><block offset><block length>
            - payload length = 13 (4 bytes)
            - message id = 6 (1 byte)
            - piece index = zero based piece index (4 bytes)
            - block offset = zero based of the requested block (4 bytes)
            - block length = length of the requested block (4 bytes)
    """
    message_id = 6
    payload_length = 13
    total_length = 4 + payload_length

    def __init__(self, piece_index, block_offset, block_length):
        super(Request, self).__init__()
        self.piece_index = piece_index
        self.block_offset = block_offset
        self.block_length = block_length

    def encode(self):
        # print("\033[92mIn Message Dispatcher - Request Message\033[0m")
        return struct.pack("!IBIII", self.payload_length, self.message_id, self.piece_index, self.block_offset, self.block_length)

    @classmethod
    def decode(cls, response):
        payload_length, message_id, piece_index, block_offset, block_length = struct.unpack("!IBIII", response[:cls.total_length])
        return Request(piece_index, block_offset, block_length)

class Piece(Message):
    """
        PIECE = <length><message id><piece index><block offset><block>
        - length = 9 + block length (4 bytes)
        - message id = 7 (1 byte)
        - piece index =  zero based piece index (4 bytes)
        - block offset = zero based of the requested block (4 bytes)
        - block = block as a bytestring or bytearray (block_length bytes)
    """
    message_id = 7
    payload_length = -1
    total_length = -1

    def __init__(self, block_length, piece_index, block_offset, block):
        super(Piece, self).__init__()
        self.block_length = block_length
        self.piece_index = piece_index
        self.block_offset = block_offset
        self.block = block
        self.payload_length = 9 + block_length
        self.total_length = 4 + self.payload_length

    def encode(self):
        return struct.pack("!IBII{}s".format(self.block_length), self.payload_length, self.message_id, self.piece_index, self.block_offset, self.block)

    @classmethod
    def decode(cls, response):
        block_length = len(response) - 13
        payload_length, message_id, piece_index, block_offset, block = struct.unpack("!IBII{}s".format(block_length), response[:13 + block_length])
        return Piece(block_length, piece_index, block_offset, block)

class Cancel(Message):
    """CANCEL = <length><message id><piece index><block offset><block length>
        - length = 13 (4 bytes)
        - message id = 8 (1 byte)
        - piece index = zero based piece index (4 bytes)
        - block offset = zero based of the requested block (4 bytes)
        - block length = length of the requested block (4 bytes)"""
    message_id = 8
    payload_length = 13
    total_length = 4 + payload_length

    def __init__(self, piece_index, block_offset, block_length):
        super(Cancel, self).__init__()
        self.piece_index = piece_index
        self.block_offset = block_offset
        self.block_length = block_length

    def encode(self):
        return struct.pack("!IBIII", self.payload_length, self.message_id, self.piece_index, self.block_offset, self.block_length)

    @classmethod
    def decode(cls, response):
        payload_length, message_id, piece_index, block_offset, block_length = struct.unpack("!IBIII", response[:cls.total_length])
        return Cancel(piece_index, block_offset, block_length)

class Port(Message):
    """
        PORT = <length><message id><port number>
            - length = 5 (4 bytes)
            - message id = 9 (1 byte)
            - port number = listen_port (4 bytes)
    """
    message_id = 9
    payload_length = 5
    total_length = 4 + payload_length

    def __init__(self, listen_port):
        super(Port, self).__init__()
        self.listen_port = listen_port

    def encode(self):
        return struct.pack("!IBI", self.payload_length, self.message_id, self.listen_port)

    @classmethod
    def decode(cls, response):
        payload_length, message_id, listen_port = struct.unpack("!IBI", response[:cls.total_length])
        return Port(listen_port)
