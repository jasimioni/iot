#!/usr/bin/env python3

import asyncio
import logging
import datetime

import aiocoap
import aiocoap.resource as resource

# Configure logging
logging.basicConfig(level=logging.INFO)
logging.getLogger("coap-server").setLevel(logging.DEBUG)

class TimeResource(resource.Resource):
    """
    This resource provides the current server time.
    """
    async def render_get(self, request):
        """
        Handles GET requests.
        """
        # Get the current time
        current_time = datetime.datetime.now().isoformat()
        
        # Create the response payload
        payload = current_time.encode('utf-8')
        
        # Create a CoAP message with a 'Content' code and the payload
        return aiocoap.Message(code=aiocoap.CONTENT, payload=payload)

async def main():
    """
    Main function to set up and run the CoAP server.
    """
    # Create the root resource which will hold all other resources
    root = resource.Site()
    
    # Add our TimeResource to the site at the path "time"
    root.add_resource(('time',), TimeResource())

    # Set up the CoAP server context
    # This binds the server to all available network interfaces on port 5683
    await aiocoap.Context.create_server_context(root)

    # Wait indefinitely for requests
    print("CoAP server started on coap://[::]:5683")
    print("Serving resource at /time")
    
    # Keep the server running
    await asyncio.get_running_loop().create_future()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Server shutting down.")
