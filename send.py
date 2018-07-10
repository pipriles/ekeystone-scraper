#!/usr/bin/env python3

import subprocess as sp
import glob
import sys

IP_FILE = './ip.in'

def read_ips(filename):
    data = []
    with open(filename, 'r', encoding='utf8') as fl:
        data = [ x.rstrip('\n') for x in fl ]
    return data

def main():

    if len(sys.argv) != 2:
        print('Usage: ./send.py [REMOTE DIR]')
        return

    rfolder = sys.argv[1]
    vps = read_ips(IP_FILE)

    files = glob.glob('./inputs/white_*')
    files = sorted(files)

    for fl, ip in zip(files, vps):
        dest = '%s:%s' % (ip, rfolder)
        command = [ 'scp', fl, dest ]
        print(' '.join(command))
        code = sp.call(command)
        print('Return code:', code, ip) 

if __name__ == '__main__':
    main()
