# NOTE: ONLY IMPORT THIS FILE FROM database/database.py !!!
# NOTE: otherwise pool will be created multiple times
import os

from dotenv import load_dotenv
from psycopg_pool import ConnectionPool
from psycopg import Cursor


# load environment variables
env_file_path = os.path.expanduser("~/.env")
load_dotenv(env_file_path)

USER = os.getenv("PGUSER")
PASSWORD = os.getenv("PGPASSWORD")
HOST = os.getenv("PGHOST")  # localhost
PORT = os.getenv("PGPORT")  # 5432
DBNAME = os.getenv("PGDATABASE")  # stueble_data


def create_pool(max_connections: int = 100, min_connections: int = 40) -> ConnectionPool | Exception:
    """
    create_pool \n
    creates a thread pool safely

    Args:
    max_connections (int): maximum number of connections
    min_connections (int): minimum number of connections
    Returns:
        connection_pool: connection_pool
    """
    connection_pool = ConnectionPool(
        min_size=min_connections,
        max_size=max_connections,
        kwargs={
        "user":USER,
        "password":PASSWORD,
        "host":HOST,
        "port":PORT,
        "dbname":DBNAME
        }
    )

    if not connection_pool:
        raise Exception("Creation of connection pool failed")
    return connection_pool

def close_pool(pool: ConnectionPool) -> None:
    """
    close the connection pool

    Args:
        pool (ConnectionPool): connection pool to close
    """
    pool.close()


def get_cursor(pool: ConnectionPool) -> Cursor:
    """
    get a cursor from the pool

    Returns:
        Cursor: cursor object for database
        pool (ConnectionPool): connection pool to get the connection from
    """
    return pool.getconn().cursor()


def close_cursor(cursor: Cursor, pool: ConnectionPool) -> None:
    """
    close a cursor and return the connection to the pool

    Args:
        Cursor: cursor object to close
        pool (ConnectionPool): connection pool to return the connection to
    """
    cursor.close()
    pool.putconn(cursor.connection)
