#!/usr/bin/env python3

import flask
import redis
import random
import os
import signal
import subprocess as sp
import psutil
import util
import json

db  = redis.Redis('localhost')
app = flask.Flask(__name__)
PID_KEY = 'SCRAPER_PID'

def find_pid():

    pid = db.get(PID_KEY)
    pid = parse_key(pid, int)
    if pid and psutil.pid_exists(pid):
        return pid
    db.delete(PID_KEY)
    return None

def parse_key(pid, cast):
    return cast(pid) if pid else pid

@app.route('/start')
@app.route('/')
def run():
    pid = find_pid()
    if pid is None:
        p = sp.Popen(['scraper.py'], stdin=sp.DEVNULL)
        pid = p.pid
        db.set(PID_KEY, pid)
    return flask.jsonify({ 'pid': pid })

@app.route('/status')
def status():
    pid = find_pid()
    st  = { 'pid': pid }
    if pid is None:
        st['status'] = 'stopped'
    st = util.read_status(st)
    return flask.jsonify(st)

@app.route('/stop')
def stop():
    pid = find_pid()
    if pid: 
        os.kill(pid, signal.SIGINT)
        # Ugly fix :(
        sp.run(['pkill', 'chromium'])
        db.delete(PID_KEY)
    return flask.jsonify({ 'pid': pid })

def main():
    pass

if __name__ == '__main__':
    main()

