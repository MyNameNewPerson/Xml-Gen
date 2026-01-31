# core/db.py
import mysql.connector
import yaml
from core.logger import get_logger

logger = get_logger(__name__)

class Database:
    def __init__(self):
        with open('config/db.yaml', 'r') as f:
            config = yaml.safe_load(f)['database']
        self.conn = mysql.connector.connect(
            host=config['host'],
            user=config['user'],
            password=config['password'],
            database=config['database'],
            port=config.get('port', 3306)
        )
        self.cursor = self.conn.cursor(dictionary=True)
        logger.info("Database connection established.")

    def execute(self, query, params=None):
        try:
            self.cursor.execute(query, params)
            return self.cursor.fetchall()
        except mysql.connector.Error as err:
            logger.error(f"Database error: {err}")
            raise

    def close(self):
        self.cursor.close()
        self.conn.close()
        logger.info("Database connection closed.")

# Context manager usage: with Database() as db: ...
def with_db(func):
    def wrapper(*args, **kwargs):
        db = Database()
        try:
            return func(db, *args, **kwargs)
        finally:
            db.close()
    return wrapper