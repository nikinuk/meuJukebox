import json
import asyncio
from jukebox_inspiria.sql_stuf import *

  
def save_credentials(users, username, password, filename='static/setup_files/credentials.json'):
  """
  Saves username and password to a JSON file.

  Args:
    username: The username to save.
    password: The password to save.
    filename: The name of the file to save the credentials to. 
              Defaults to 'credentials.json'.
  """
  users[username] = password
  with open(filename, 'w') as f:
    json.dump(users, f, indent=4)

async def move_item_between_files(juke_sql, source, destination, item):

    grants, bans = juke_sql.get_track_validation()

    if source == "grant":
        grants.remove(item)
        query = "UPDATE configurations SET list_2_grant = '" + str(sorted(grants)).replace("'", '"') + "' WHERE config_name = '" + juke_sql.instance + "';"
        await juke_sql.sql_exe(query)

    elif source == 'ban':
        bans.remove(item)
        query = "UPDATE configurations SET list_2_ban = '" + str(sorted(bans)).replace("'", '"') + "' WHERE config_name = '" + juke_sql.instance + "';"
        await juke_sql.sql_exe(query)

    elif destination == "grant":
        grants.append(item)
        query = "UPDATE configurations SET list_2_grant = '" + str(sorted(grants)).replace("'", '"') + "' WHERE config_name = '" + juke_sql.instance + "';"
        await juke_sql.sql_exe(query)

    else:
        bans.append(item)
        query = "UPDATE configurations SET list_2_ban = '" + str(sorted(bans)).replace("'", '"') + "' WHERE config_name = '" + juke_sql.instance + "';"
        await juke_sql.sql_exe(query)

async def register_user(juke_sql, username, email, password_hash):
    try:
        #insert new user
        query = f"INSERT INTO users (user_name, password_hash, email, access_level) VALUES ('{username}', '{password_hash}', '{email}', 1)"
        await juke_sql.sql_exe(query)
        # Get new user id
        query = f"SELECT id FROM users WHERE email = '{email}'"
        user_id = juke_sql.sql_get_one(query)[0]
        return True, user_id
    except Exception as e: # catch any other type of error
        print(f"my log - ERROR EM register_user -An unexpected error occurred: {e}")
        return False, None

def verify_password(juke_sql, user_id, entered_password):
    try:
        query = f"SELECT password_hash, user_name, access_level, id FROM users WHERE email = '{user_id}';"
        test = juke_sql.sql_get_one(query)
        if test:
            stored_hash = test[0]
            return bcrypt.verify(entered_password, stored_hash), test[1], test[2], test[3]
        else:
            return False, None, None  # User not found

    except Exception as e:
        print(f"my log - ERROR EM verify_password - Error verifying password: {e}")
        return False, None, None
