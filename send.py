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

def scp_call(src, dest):

    command = [ 'scp', src, dest ]
    print(' '.join(command))
    return sp.call(command)

def send_files(src, rfolder, ips=IP_FILE):

    vps = read_ips(ips)

    files = glob.glob(src)
    files = sorted(files)

    for fl, ip in zip(files, vps):
        dest = '%s:%s' % (ip, rfolder)
        code = scp_call(fl, dest)
        print('Return code:', code, ip) 

def main():

    if len(sys.argv) != 2:
        print('Usage: ./send.py [REMOTE DIR]')
        return

    rfolder = sys.argv[1]
    send_files('./dumps/parts/*', rfolder)

if __name__ == '__main__':
    main()

