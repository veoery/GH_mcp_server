#!/usr/bin/env python
import sys
import os

# Set up the Python path to find the package
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import and run the server module
from grasshopper_mcp.server import main

if __name__ == "__main__":
    main()
