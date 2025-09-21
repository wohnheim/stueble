"""
Main runner using threading for Flask API and WebSocket server
Note: Variables WILL be shared between threads - same memory space
"""

import asyncio
import threading
import time
import signal
import sys
from packages.backend import api
from packages.backend import websocket
from waitress import serve
from packages.backend.sql_connection import database as db

pool = db.create_pool()

def get_conn_cursor():
    """
    gets a connection and a cursor from the connection pool
    """
    conn = pool.getconn()
    cursor = conn.cursor()
    return conn, cursor

def close_conn_cursor(connection, cursor):
    """
    closes the cursor and returns the connection to the pool
    """
    cursor.close()
    pool.putconn(connection)

def run_flask():
    """Run the Flask API server in separate thread"""
    print(f"Starting Flask API server in thread {threading.current_thread().name}...")
    serve(api.app, host="127.0.0.1", port=3000)

def run_websocket():
    """Run the WebSocket server in separate thread"""
    print(f"Starting WebSocket server in thread {threading.current_thread().name}...")
    asyncio.run(websocket.main())

def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully"""
    print('\nShutting down servers...')
    sys.exit(0)

def main():
    """Main function to start both servers in separate threads"""
    # Set up signal handler for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    
    print("Starting Stueble application with threading...")
    print("SUCCESS: Variables WILL be shared between Flask and WebSocket threads!")
    
    # Create threads (daemon=True means they'll exit when main program exits)
    flask_thread = threading.Thread(target=run_flask, name="Flask-Server", daemon=True)
    websocket_thread = threading.Thread(target=run_websocket, name="WebSocket-Server", daemon=True)

    # Start both threads
    flask_thread.start()
    websocket_thread.start()
    
    print(f"Flask server started in thread: {flask_thread.name}")
    print(f"WebSocket server started in thread: {websocket_thread.name}")
    print("Both servers started. Press Ctrl+C to stop.")
    
    # Keep main thread alive
    while flask_thread.is_alive() or websocket_thread.is_alive():
        time.sleep(1)

if __name__ == "__main__":
    main()
