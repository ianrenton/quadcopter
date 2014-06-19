#!/usr/bin/env python

# Quadcopter server-side control script, v0.1
# Python 2.x for Raspberry Pi
# by Ian Renton
# BSD 2-clause licenced
# http://ianrenton.com/quadcopter

import operator
import socket
import select
import serial
import time
import thread

#################
#   Constants   #
#################

IP = ""          # Listen to all IPs
PORT = 5123      # Port on which to run the server
TIMEOUT = 5      # Packet Rx timeout, will land automatically if a timeout occurs
BUFFER_SIZE = 1024

s = serial.Serial("/dev/ttyAMA0",9600)

#################
#   Functions   #
#################

# NMEA checksum
def checksum(nmeaString):
  return "%02X" % reduce(operator.xor, map(ord, nmeaString), 0)
  
# Set controls
# Throttle, pitch, roll, yaw in %. Autolevel as boolean
def setControls(throttle, pitch, roll, yaw, autolevel):
  s.write("sa "+str(roll*10)+" "+str(-pitch*10)+" "+str(throttle*20-1000)+" "+str(-yaw*10)+" "+("1000" if autolevel else "-1000")+"\n")
    
# Set idle positions
def idle():
  setControls(0,0,0,0,True)

# Arm
def arm():
  setControls(0,0,0,100,True)
  time.sleep(3)
  idle()

# Disarm
def disarm():
  setControls(0,0,0,-100,True) 
  time.sleep(3)
  idle()


#################
#      Main     #
#################

# Startup
print "Quadcopter remote control script, v0.1"

# Open serial port and set controls to idle
s.open()
idle()
currentThrottle = 0

# Bind to port and listen for incoming TCP connections
tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
tcp.bind((IP, PORT))
tcp.setblocking(1)
tcp.listen(1)

# Run forever
while True:
    # Accept connection
    print "Listening on port", PORT
    conn, addr = tcp.accept()
    print "Client connected from address", addr
    
    # Client connected, arm control board
    arm()
    
    # Receive packets until connection drops
    while True:
        ready = select.select([conn], [], [], TIMEOUT)
        if ready[0]:
            # Read the message
            msg = conn.recv(BUFFER_SIZE)
            
            if (msg == ""):
              print "Connection lost."
              break
              
            try:
              # Check checksum matches
              baseMsg = msg.split("*")[0][1:]
              msgChecksum = msg.split("*")[1]
              if (msgChecksum == checksum(baseMsg)):
                  # Checksum OK. Check message is a QCCON
                  bits = baseMsg.split(",")
                  if (bits[0] == "QCCON"):
                      # QCCON OK. Unpack contents
                      controls = map(lambda x: int(x), bits[1:])
                      print "THR {:03d}  PIT {:03d}  ROL {:03d}  YAW {:03d}  LEV {:03d}".format(*controls)
                      # Set controls
                      setControls(controls[0], controls[1], controls[2], controls[3], (controls[4]>0))
                      # Store current throttle for spin-down when necessary
                      currentThrottle = controls[0]
                  else:
                      print "Message was not $QCCON"
              else:
                  print "Checksum mismatch, expected", checksum(baseMsg)
              
              # Echo back to the client for confirmation
              conn.send(msg)
            except:
              print "Exception caught, dropping connection."
              break
        else:
            print "Connection lost."
            break;

    conn.close()

    # Nothing's in control! Spin down
    print 'Client disconnected, landing...'
    while (currentThrottle > 0):
      currentThrottle = currentThrottle - 1
      setControls(currentThrottle, 0, 0, 0, True)
      time.sleep(0.5)
    # Disarm control board
    disarm()
    
# Close serial port
s.close()
