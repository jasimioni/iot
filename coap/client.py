#!/usr/bin/env python3

import asyncio
import logging

from aiocoap import Context, Message
import aiocoap

# Configure logging
logging.basicConfig(level=logging.INFO)

async def main():
    """
    Main function to run the CoAP client.
    """
    # Create a client context
    context = await Context.create_client_context()

    # Define the request message
    # We are sending a GET request to the URI coap://localhost/time
    request = Message(code=aiocoap.GET, uri='coap://localhost/time')

    print("Sending request to coap://localhost/time...")

    try:
        # Send the request and wait for a response
        response = await context.request(request).response
    except Exception as e:
        print(f"Failed to fetch resource: {e}")
        return
    finally:
        # Clean up the context
        await context.shutdown()

    # Process the response
    if response.code.is_successful():
        payload = response.payload.decode('utf-8')
        print(f"Response received successfully!")
        print(f"  Code: {response.code}")
        print(f"  Payload (Server Time): {payload}")
    else:
        print(f"Error: Received code {response.code}")

if __name__ == "__main__":
    asyncio.run(main())
