#!/bin/bash

# This is the ABSOLUTE path INSIDE the container where the DLLs are located.
VSCAPTURE_DIR="/opt/vscapture/VSCaptureCLIv1.006Binary"

# 1. Change the current working directory (CWD) to the DLL's folder.
# This ensures dotnet VSCaptureCLI.dll can find VSCaptureWave.dll.
cd "$VSCAPTURE_DIR" || { echo "Error: Cannot change directory to $VSCAPTURE_DIR" >&2; exit 1; }

# 2. Execute the dotnet command using the DLL name (not the full path now)
# and pass all arguments ($@) that were given to this script.
dotnet VSCaptureCLI.dll "$@"