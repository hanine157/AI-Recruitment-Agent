#!/usr/bin/env python
import sys
import os

# Add current directory to path so 'app' module can be found
sys.path.insert(0, os.path.dirname(__file__))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
