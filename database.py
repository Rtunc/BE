
import psycopg2


def get_postgres_connection():
    conn = psycopg2.connect(
        dbname="mydatabase",
        user="admin",
        password="admin",
        host="127.0.0.1",  # hoặc IP của container Docker
        port="5432"
    )
    return conn


