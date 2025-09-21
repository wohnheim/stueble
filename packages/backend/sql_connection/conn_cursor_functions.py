from packages.backend.sql_connection.pool import pool

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