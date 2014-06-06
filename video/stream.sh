#!/bin/bash

nc 10.0.0.1 5001 | mplayer -fps 30 -demuxer h264es -
