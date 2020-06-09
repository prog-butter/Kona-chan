#!/usr/bin/env python3
from bcoding import bencode, bdecode
import hashlib
import requests
import random
import struct
import socket

import torrentManager as tm

def main():
	tor1 = tm.torrentManager("P10.mkv.torrent")
	tor1.initialAnnounce()
	tor1.loop()

if __name__ == "__main__":
	main()
