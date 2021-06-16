#!/bin/bash

# watchdog/keep-alive for script

while :
do
	/usr/bin/python3 /home/pi/kexp.py
	sleep 1
done
