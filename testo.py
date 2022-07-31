from lorettOrbital.orbital import *
from pprint import pprint
import sqlite3 as sql



db_connection = sql.connect('databases/users.db')
cursor = db_connection.cursor()

user_data = db_connection.execute("SELECT (user_id) FROM users").fetchall()
print(user_data)

db_connection.commit()
db_connection.close()
