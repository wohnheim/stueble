import os

from dotenv import load_dotenv
from psycopg2.pool import ThreadedConnectionPool

_ = load_dotenv()

USER = os.getenv("USERDB") # stueble (like the linux user name!)
PASSWORD = os.getenv("PASSWORD")
HOST = os.getenv("HOST") # localhost
PORT = os.getenv("PORT") # 5432
DBNAME = os.getenv("DBNAME") # stueble_data

def create_pool(max_connections: int = 100, min_connections: int=20):
    """
    create_pool \n
    creates a thread pool safely

    Parameters:
    max_connections (int): maximum number of connections
    min_connections (int): minimum number of connections
    Returns:
        connection_pool:connection_pool
    """
    connection_pool = ThreadedConnectionPool(
        minconn=min_connections,
        maxconn=max_connections,
        user=USER,
        password=PASSWORD,
        host=HOST,
        port=PORT,
        database=DBNAME
    )

    if not connection_pool:
        raise Exception("Creation of connection pool failed")
    return connection_pool

pool = create_pool()