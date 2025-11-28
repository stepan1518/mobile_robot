from .DBConnection import DBConnection

DB_CONFIG = 'db.yml'
db_connection = None

class DBAbstractFactory:
    def __init__(self):
        pass

    @staticmethod
    def createDBConnection():
        global db_connection

        if db_connection == None:
            db_connection = DBConnection()

        return db_connection