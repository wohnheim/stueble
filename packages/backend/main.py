"""
Main runner using threading for Flask API and WebSocket server
Note: Variables WILL be shared between threads - same memory space
"""

import asyncio
import os
import signal
import sys
import threading
import time
from types import FrameType

from waitress import serve

from backend import api
from backend import websocket
import backend.websocket_runner as ws_runner  # to ensure DB listener is set up

HOST = os.getenv("HOST") or "127.0.0.1"
PORT = os.getenv("PORT") or 3000

def run_flask():
    """Run the Flask API server in separate thread"""
    print(f"HTTP-Server is listening on {HOST}:{PORT}")
    serve(api.app, host=HOST, port=PORT)

def run_websocket():
    """Run the WebSocket server in separate thread"""
    asyncio.run(websocket.main())

def signal_handler(_sig: int, _frame: FrameType | None):
    """Handle Ctrl+C gracefully"""
    print('\nShutting down servers...')
    sys.exit(130)

def main():
    """Main function to start both servers in separate threads"""
    # Set up signal handler for graceful shutdown
    _ = signal.signal(signal.SIGINT, signal_handler)

    print("Starting Stueble application...")

    # Create threads (daemon=True means they'll exit when main program exits)
    flask_thread = threading.Thread(target=run_flask, name="Flask-Server", daemon=True)
    websocket_thread = threading.Thread(target=run_websocket, name="WebSocket-Server", daemon=True)
    db_listener_thread = threading.Thread(target=ws_runner.run_listener, name="DB-Listener", daemon=True)

    # Start threads
    flask_thread.start()
    websocket_thread.start()
    db_listener_thread.start()

    # Keep main thread alive
    while flask_thread.is_alive() and websocket_thread.is_alive() and db_listener_thread.is_alive():
        time.sleep(1)

if __name__ == "__main__":
    main()
