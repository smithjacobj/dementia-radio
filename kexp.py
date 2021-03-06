#!/usr/bin/python3

from gpiozero import Button, RotaryEncoder
from gpiozero.tools import scaled
from time import sleep 
import subprocess
import syslog

PLAYER_BIN = "mpg123"
STREAM_URIS = ["http://live-mp3-128.kexp.org/kexp128.mp3", "http://216.246.37.218/kexp128-backup.mp3"]

START_VOLUME = 30
MIN_VOLUME = 1 
MAX_VOLUME = 60

is_playing = False
is_restarting = False
play_handle = None
current_stream_uri = 0 

def Log(s):
    syslog.syslog(s)
    
def Warn(s):
    syslog.syslog(syslog.LOG_WARNING, s)

def PlayStream(uri):
    return subprocess.Popen([PLAYER_BIN, uri], stderr=subprocess.PIPE, text=True)

def Stop():
    global is_playing

    is_playing = False
     
def Play():
    global is_playing

    if is_playing:
        return

    is_playing = True
    
def RunPlayWatchdog():
    global is_playing
    global is_restarting
    global play_handle
    global current_stream_uri

    # start or re-start the stream
    if is_playing and play_handle is None:
        if not is_restarting:
            ResetVolume(START_VOLUME)
            Log("starting stream")
        else:
            Log("restarting stream")
        is_restarting = False

        play_handle = PlayStream(STREAM_URIS[current_stream_uri])
        return

    # stream failure
    if is_playing and play_handle is not None:
        play_handle.poll()

        if play_handle.returncode is not None:
            if play_handle.returncode is not 0:
                Warn("stream failure, error code {}, stderr: {}".format(play_handle.returncode, play_handle.stderr.read()))

            play_handle = None
            is_restarting = True
            current_stream_uri = (current_stream_uri + 1) % (len(STREAM_URIS) - 1)

    # stream stopped
    if not is_playing and play_handle is not None:
        Log("stopping stream")
        try:
            play_handle.terminate()
            play_handle.wait(3)
        except TimeoutExpired:
            play_handle.kill()
            Warn("stream wouldn't stop, had to kill")
        finally:
            play_handle = None



def SetVolume(value):
    subprocess.run(["amixer", "sset", "'Master'", "{}%".format(value)])
    Log("volume set to {}%".format(value))

def ResetVolume(value):
    global volume_encoder

    SetVolume(value)
    volume_encoder.value = next(scaled([value], -1.0, 1.0, MIN_VOLUME, MAX_VOLUME))

def WhenVolumeRotated():
    volume_value = next(scaled(volume_encoder.values, MIN_VOLUME, MAX_VOLUME, -1.0, 1.0))
    SetVolume(volume_value)
    Play() # setting the volume should also trigger if it's not playing

def OnGreenButton():
    Log("play button pressed")
    Play()

def OnRedButton():
    Log("stop button pressed")
    Stop()

# procedural script & loop
volume_encoder = RotaryEncoder(24, 22, max_steps=20)
volume_encoder.when_rotated = WhenVolumeRotated

green_button = Button(17)
green_button.when_released = OnGreenButton

red_button = Button(27)
red_button.when_released = OnRedButton

syslog.openlog("KEXP-Dementia-Radio")

# activity loop
while True:
    RunPlayWatchdog()
    sleep(0.1)
