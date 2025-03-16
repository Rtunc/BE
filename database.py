from cassandra.cluster import Cluster
from cassandra.query import SimpleStatement
import psycopg2
def get_cassandra_connection():
    cluster = Cluster(['127.0.0.1'], port=9042)  # Địa chỉ và cổng của Cassandra
    session = cluster.connect()
    session.set_keyspace('data_aqi')
    return session

def get_postgres_connection():
    conn = psycopg2.connect(
        dbname="mydatabase",
        user="admin",
        password="admin",
        host="127.0.0.1",  # hoặc IP của container Docker
        port="5432"
    )
    return conn


