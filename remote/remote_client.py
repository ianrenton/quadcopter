#!/usr/bin/env python

# Quadcopter client-side control script, v0.1
# Python 2.x
# by Ian Renton
# BSD 2-clause licenced
# http://ianrenton.com/quadcopter

import operator
import socket
import time
import thread

#################
#   Constants   #
#################

IP = "10.0.0.1"    # IP address of the quadcopter
PORT = 5123         # Port on which the server runs
SEND_PERIOD = 1     # How long to wait between sending each packet (sec)
BUFFER_SIZE = 1024

#################
#    Globals    #
#################

# Control state
throttle = 0
pitch = 0
roll = 0
yaw = 0
autolevel = 1

keepSending = True


#################
#   Functions   #
#################

# NMEA checksum
def checksum(nmeaString):
    return "%02X" % reduce(operator.xor, map(ord, nmeaString), 0)

# Get keyboard char
def getch():
  import sys, tty, termios
  fd = sys.stdin.fileno()
  old_settings = termios.tcgetattr(fd)
  try:
    tty.setraw(sys.stdin.fileno())
    ch = sys.stdin.read(1)
  finally:
    termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
  return ch
  
# Keyboard input thread
def keypress():
  global throttle, pitch, roll, yaw, keepSending
  while True:
    char = getch()
    if (char == "a"):
      roll = -10
    elif (char == "d"):
      roll = 10
    else:
      roll = 0
    if (char == "w"):
      pitch = 10
    elif (char == "s"):
      pitch = -10
    else:
      pitch = 0
    if (char == "q"):
      yaw = -10
    elif (char == "e"):
      yaw = 10
    else:
      yaw = 0
    if (char == "p"):
      if (throttle < 100):
        throttle = throttle+1
    elif (char == "l"):
      if (throttle > 0):
        throttle = throttle-1
    if (char == " "):
      keepSending = False
      break


#################
#      Main     #
#################

# Startup
print "Quadcopter remote control script, v0.1"
print "Pitch Fwd:   W    Back: S       Roll Left:  A    Right: D"
print "Yaw CCW:     Q    CW:   E       Centre Pitch/Roll/Yaw:  X"
print "Throttle Up: P    Down: L       Quit: SPACE"
print

# Spawn key listener thread
thread.start_new_thread(keypress, ())

# Run TCP connection loop until stopped
while keepSending:
    # Connect to the server
    conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    conn.connect((IP, PORT))
    # Send control packet every second
    while keepSending:
        # Build and send an NMEA string
        controls = map(lambda x: str(x), [throttle, pitch, roll, yaw, autolevel])
        baseMsg = "QCCON," + ",".join(controls)
        fullMsg = "$" + baseMsg + "*" + checksum(baseMsg)
        conn.send(fullMsg)

        # Check server response
        echoMsg = conn.recv(BUFFER_SIZE)
        if echoMsg == fullMsg:
            print "Echo OK:", echoMsg
            print "\r\n"
        else:
            print "Echo mismatch!"
            print "Demand  ", fullMsg
            print "Response", echoMsg
            print "\r\n"

        # Wait for next time
        time.sleep(SEND_PERIOD)
    conn.close()

