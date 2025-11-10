#!/usr/bin/env python3

import uvicorn
from fastapi import FastAPI
import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)

# 1. Create the FastAPI app instance
app = FastAPI()

# 2. Define the resource (route)
@app.get("/time")
async def get_time():
    """
    Handles GET requests to /time.
    """
    logging.info("Received request for /time")
    current_time = datetime.datetime.now().isoformat()
    
    # In FastAPI, you just return a dictionary,
    # and it automatically converts it to a JSON response.
    return {"current_time": current_time}

# 3. Main function to run the server
if __name__ == "__main__":
    print("Starting HTTP server on http://127.0.0.1:8000")
    print("Serving resource at /time")
    
    # Uvicorn runs the FastAPI application
    uvicorn.run(app, host="127.0.0.1", port=8000)