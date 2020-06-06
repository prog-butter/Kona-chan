#!/usr/bin/env python3
from bcoding import bencode, bdecode
import hashlib
import requests
import random
import struct
import socket

import torrentManager as tm

def main():
	tor1 = tm.torrentManager("ubuntu.iso.torrent")
	tor1.initialAnnounce()

if __name__ == "__main__":
	main()
