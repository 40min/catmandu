#!/usr/bin/env python3
"""
Entry point script for the echo cattackle server.
This script imports and runs the main server from the echo package.
"""

import sys

from echo.server import main

if __name__ == "__main__":
    sys.exit(main())
