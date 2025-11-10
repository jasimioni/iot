#!/usr/bin/env python3

import asyncio
import httpx # The modern, async-capable HTTP client
import logging

logging.basicConfig(level=logging.INFO)

async def main():
    """
    Main function to run the HTTP client.
    """
    # Create an async client context
    async with httpx.AsyncClient() as client:
        
        uri = 'http://localhost:8000/time'
        print(f"Sending request to {uri}...")

        try:
            # Send the request and wait for a response
            response = await client.get(uri)

            # Raise an error if the request was unsuccessful (e.g., 404, 500)
            response.raise_for_status() 
            
        except (httpx.ConnectError, httpx.HTTPStatusError) as e:
            print(f"Failed to fetch resource: {e}")
            return

        # Process the response
        # Use .json() to parse the JSON response from the server
        payload = response.json() 
        
        print("Response received successfully!")
        print(f"  Status Code: {response.status_code}")
        print(f"  Payload (Server Time): {payload['current_time']}")

if __name__ == "__main__":
    asyncio.run(main())