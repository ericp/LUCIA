from sqlalchemy import create_engine

# This will create (or will use if it already exists) the file data/db.sqlite3
engine = create_engine('sqlite:/Users/eric/Documents/Masters Degree/M10.-TFM/LUCIA/data/db.sqlite3')