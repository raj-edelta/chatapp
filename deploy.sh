#!/bin/bash
docker build -t speech-to-text .
docker run -p 7500:7500 -d speech-to-text:latest
