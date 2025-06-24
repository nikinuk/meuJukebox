#---------------------------------------------------------------------------------
#                          HELP FUNCTIONS para jukebox
#--------------------------------------------------------------------------------

#--------------------------------------------------------------------------------
#                           Imagem para compartilhamento
#  -------------------------------------------------------------------------------

import json
import asyncio
from datetime import datetime, timedelta

from PIL import Image, ImageDraw, ImageFont
FONT_PATH = "static/customer/AGENCYR.TTF" #arquivo de fonte utilizado

def wrap_text(text, max_width):
  """
  Wraps a string to a specified maximum width.

  Args:
    text: The input string.
    max_width: The maximum number of characters per line, including spaces.

  Returns:
    A string with line breaks inserted at appropriate positions.
  """

  words = text.split()
  lines = []
  current_line = ""

  for word in words:
    if len(current_line) + len(word) + 1 <= max_width:  # +1 for the space
      current_line += word + " "
    else:
      lines.append(current_line.strip())
      current_line = word + " "

  if current_line:
    lines.append(current_line.strip())

  return "\n".join(lines)

def paste_images_resized(main_image_path, image1_path, image2_path, output_path, text):
  """
  Recebe o path para imagens de fundo e do bar e faz a colagem com a imagem do album
  Adiciona o texto e salva em output path

  Retorna True se tudo ok e False caso erros
  """
  try:

    main_image = Image.open(main_image_path)
    image1 = Image.open(image1_path)
    image2 = Image.open(requests.get(image2_path, stream=True).raw)

    image1 = image1.resize((500, 500))
    image2 = image2.resize((500, 500))

    main_image.paste(image1, (50, 180))
    main_image.paste(image2, (200, 600))

    wtext = wrap_text(text, 33)
    draw = ImageDraw.Draw(main_image)
    font = ImageFont.truetype(FONT_PATH, 64)
    position = (720, 1200)
    padding = 10

    tx_img = Image.new('RGB', (1, 1))  # Create a dummy image
    tx_draw = ImageDraw.Draw(tx_img)
    bbox = tx_draw.textbbox((0, 0), wtext, font=font)  # Use textbbox()
    text_width, text_height = bbox[2] - bbox[0], bbox[3] - bbox[1]  # Calculate width and height
    
    bg_left = position[0] - padding - text_width
    bg_top = position[1] - padding
    bg_right = position[0] + text_width + padding
    bg_bottom = position[1] + text_height + padding

    draw.rectangle([bg_left, bg_top, bg_right, bg_bottom], fill="black")
    draw.multiline_text(position, wtext, font=font, fill="white", align = "right", anchor="ra")
    main_image.save(output_path)

    return True

  except Exception as inst:
    print("my log - ERROR EM paste_images_resized - construindo imagens - ", inst) 
    return False

import json

def key_exists(json_data, key):
  """
  vERIFICA SE CHAVE EXISTE NO JSON
  """
  try:
    if isinstance(json_data, str):
      json_data = json.loads(json_data)  # Convert string to dictionary if necessary
    return key in json_data
  except json.JSONDecodeError:
    return False

import ast
import requests
import os

def find_matching_texts(list1, list2):
    """
    Finds and returns a list of texts that are present in both input lists.

    Args:
        list1: The first list of texts.
        list2: The second list of texts.

    Returns:
        A list of matching texts. If no matches are found, returns an empty list.
    """

    matching_texts = []
    for text1 in list1:
        if text1 in list2:
            matching_texts.append(text1)
    return matching_texts

from datetime import datetime
from glob import glob

def log_like(id, name, artist, url, user):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    filename = f"static/reports/like_log.txt"

    # Check if the file exists, if not create it  
    with open(filename, 'a', encoding='utf-8') as file:
      pass

    log_data = {
        'timestamp': now,
        'track_id': id,
        'song_name': name,
        'song_artist': artist,
        'album_url' : url,
        'user': user,
      }
    log_line = json.dumps(log_data) 
    with open(filename, 'a', encoding='utf-8') as file:
        file.write(log_line + '\n')

    now = datetime.now()
    cutoff_date = now - timedelta(days=365)
    new_lines = []
    
    with open(filename, 'r+', encoding='utf-8') as f:
        for line in f:
          try:
            data = json.loads(line)
            timestamp_str = data['timestamp']
            timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S.%f")

            # Keep lines within the age limit and add them to new_lines
            if timestamp >= cutoff_date:
              new_lines.append(line)
          except (json.JSONDecodeError, ValueError):
            print(f"my log - ERROR EM log_like - Error parsing line: {line}")

        # Truncate the file and write new lines (up to max_lines)
        f.seek(0)
        f.truncate()
        f.writelines(new_lines)
    

def validate_track(artists_ids, track_id, song_name, song_artist, juke_list, API_BASE_URL, grant_list, ban_list, config, msg_ban, album_url, user, instance):
    artists_ids = ast.literal_eval(artists_ids)
    # Validar repetições
    if track_id in juke_list:
       return "Música já se encontra na lista de pedidos.", None, None

    # Validar Gênero
    generos = []
    for id in artists_ids:
        headers = {'Authorization': f"Bearer {os.environ['ACCESS_TOKEN']}"}
        response1 = requests.get( API_BASE_URL + "artists/" + id, headers = headers).json()
        for genero in response1['genres']:
            generos.append(genero.replace("'","`"))

    if generos == []:
       return "Artista sem gênero especificado", None, None
    if config['ban_list'] == True: 
        banned_list = find_matching_texts(generos, ban_list)
        if banned_list != []:
            return_msg =  ""
            for genero in banned_list:
                return_msg = return_msg + genero + ", "
            #log_add(False, track_id, song_name, song_artist, msg_ban + return_msg[:-2], album_url, user, artists_ids, generos, instance)
            return msg_ban + " " + return_msg[:-2], artists_ids, generos

    if config['grant_list'] == True:
        granted_list = find_matching_texts(generos, grant_list)
        if granted_list == []:
            return_msg = " "
            for genero in generos:
                return_msg = return_msg + genero + ", "
            #log_add(False, track_id, song_name, song_artist, msg_ban + return_msg[:-2], album_url, user, artists_ids, generos, instance)
            return msg_ban + " " + return_msg[:-2], artists_ids, generos
    
    #log_add(True, track_id, song_name, song_artist, "valid_track", album_url, user, artists_ids, generos, instance)

    return "valid_track", artists_ids, generos

import uuid

def generate_unique_id():
  """Generates a unique identification ID using UUID v4.

  Returns:
      str: A unique ID string.
  """
  return str(uuid.uuid4())

def log_add(juke_sql, valid, track_id, song_name, song_artist, return_msg, album_url, user, artists_ids, generos, instance):
   
    now = datetime.now().timestamp()

    query1 = f"""
        INSERT INTO pedidos (time_stamp, track_id, user_name, reason, val_result, instance ) 
        VALUES ('{now}', '{track_id}', '{user}', '{return_msg}', '{valid}', '{instance}');
        """    
    
    query2 = f"""
        INSERT INTO tracks (track_id, song_name, song_artist, album_url)
        SELECT '{track_id}', '{song_name.replace("'", "''")}', '{song_artist.replace("'", "''")}', '{album_url}'
        WHERE NOT EXISTS (
            SELECT 1 
            FROM tracks
            WHERE track_id = '{track_id}' );
        """
    
    query3 = "INSERT INTO artistas (track_id, generos, artistas, ids_artistas) SELECT '" + track_id + "', '" + str(generos).replace("'", '"') + "', '" + str(song_artist).replace("'", '"') + "', '" + str(artists_ids).replace("'", '"') + "' WHERE NOT EXISTS (SELECT 1 FROM artistas WHERE track_id = '" + track_id + "' );"

    asyncio.run(log_qs(juke_sql, [query1, query2, query3]))

async def log_qs(juke_sql, queries):
    tasks = []
    for i, query in enumerate(queries):
        tasks.append(asyncio.create_task(juke_sql.sql_exe(query)))

    for task in tasks:
        await task

async def update_session(juke_sql, user_name, user_id, session_id):
    user_name = user_name.replace("'", "''")
    query = f"UPDATE sessions SET user_id = {user_id}, user_name = '{user_name}' WHERE session_id = '{session_id}';"
    await juke_sql.sql_exe(query)