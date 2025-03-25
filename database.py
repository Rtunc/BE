
import psycopg2

# 100.92.66.89 server pc
# 127.0.0.1 docker
def get_postgres_connection():
    conn = psycopg2.connect(
        dbname="mydatabase",
        user="admin",
        password="admin",
        host="100.92.66.89",  # hoặc IP của container Docker
        port="5432"
    )
    return conn


