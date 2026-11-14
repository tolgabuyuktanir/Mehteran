#!/bin/sh
# Starts the Mehteran web interface on macOS. Double-click this file.
# The interface runs while this window stays open; to stop it, press Ctrl+C in the window or close it.
exec sh "$(dirname "$0")/scripts/mehter.sh" ui
