from google.cloud.sql.connector import Connector, IPTypes
import pg8000
from sqlalchemy import text, create_engine
from sqlalchemy.exc import SQLAlchemyError
from passlib.hash import bcrypt
from datetime import datetime, timedelta
import os

class jukeSQL:
    def __init__(self, instance, ICN, DB_USER, DB_PASS, DB_NAME):
        self.instance = instance
        self.ICN = ICN
        self.DB_USER = DB_USER
        self.DB_PASS = DB_PASS
        self.DB_NAME = DB_NAME
        self.pool = create_engine( "postgresql+pg8000://", creator=self.__getconn__)

    def __getconn__(self) -> pg8000.dbapi.Connection:
        """Initializes a connection to the Cloud SQL PostgreSQL instance."""
        connector = Connector()
        conne = connector.connect(
            self.ICN,
            "pg8000",
            user=self.DB_USER,
            password=self.DB_PASS,
            db=self.DB_NAME,
            ip_type=IPTypes.PUBLIC  # or IPTypes.PRIVATE if applicable
        )
        return conne

    def save_token(self, token, expires_at, refresh_token):
        last_modified = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        query = f"""
UPDATE instances 
SET token = '{token}', expires_at = '{expires_at}', ref_token = '{refresh_token}', lastupdate = '{last_modified}'
WHERE instance = '{self.instance}'
"""
        try:
            with self.pool.connect() as conn:
                conn.execute(text(query))
                conn.commit()
            return True
        except Exception as e:
            print("my log - 014 - Erro ao salvar token:", e)
            return False

    def get_token(self):
        query = f"SELECT token, expires_at, ref_token FROM instances WHERE instance='{self.instance}'"
        try:
            with self.pool.connect() as conn:
                result = conn.execute(text(query))
                row = result.fetchone()
            tokens = dict(row._mapping)

            # Verificar validade
            if datetime.now().timestamp() < float(tokens['expires_at']):
                # se válido retornar
                return tokens
            else:
                return None    

        except Exception as e:
            print("my log - sql - Erro ao buscar token:", e)

    def check_connection(self):
        try:
            query = f"SELECT * FROM configurations WHERE config_name='{self.instance}'"

            with self.pool.connect() as conn:
                result = conn.execute(text(query))
                row = result.fetchone()
            config_dict = dict(row._mapping)
            print("my log - 005 - Acesso de usuário validado:", self.DB_USER)
            return "ok", config_dict
        except SQLAlchemyError as e:
            if e.code == "4xp6":
                print("my log - 005 - Usuário sem acesso")
                return "access", None
        except Exception as e:
            print("my log - 005 - Erro nos dadoss:", e)
            return "data", None
    
    def create_config(self):
        query = f"""
INSERT INTO configurations (config_name, ban_list, grant_list, list_2_grant, list_2_ban, refuse_msg_grant, refuse_msg_ban, share_msg, default_search, jukebox_title)
VALUES ('{self.instance}', False, False, '[]', '[]', 'Não foi possível encontrar genero musical válido', 'Gênero musical do artista incompatível', 'Curtindo TRACK do ARTIST aqui na {self.instance}', 'mpb', '{self.instance}');
"""
        try:
            with self.pool.connect() as conn:
                conn.execute(text(query))
                conn.commit()
            print("my log - 011 - Configuração criada:", self.instance)
            return True
        except Exception as e:
            print("my log - 011 - Erro na criação da config:", e)
            return False

    async def sql_exe(self, query):
        try:
            with self.pool.connect() as conn:
                conn.execute(text(query))
                conn.commit()
        except SQLAlchemyError as e:
            print(f"my log - ERRO EM sql_exe - SQLAlchemy error ocorreu: {e}")
        except Exception as e: 
            # Catch generic exceptions as a last resort
            print(f"my log - ERRO EM sql_exe - An unexpected error occurred: {e}")

    def sql_get_all(self, query):
        try:
            with self.pool.connect() as conn:
                result = conn.execute(text(query))
            return result.fetchall()
        except Exception as e: 
            # Catch generic exceptions as a last resort
            return f"An unexpected error occurred: {e}"

    def sql_get_one(self, query):
        try:
            with self.pool.connect() as conn:
                result = conn.execute(text(query))
            return result.fetchone()
        except Exception as e: 
            # Catch generic exceptions as a last resort
            return f"An unexpected error occurred: {e}"
 
    def get_track_validation(self):

        query = f"SELECT list_2_ban, list_2_grant FROM configurations WHERE config_name = '{self.instance}'"

        with self.pool.connect() as conn:
            result = conn.execute(text(query))
            list = result.fetchone()

        bans, grants = list

        return grants, bans

    def get_genre_lists(self):
        grants, bans = self.get_track_validation()

        # GET generos
        query = text("""
                SELECT * FROM generos;
        """)

        with self.pool.connect() as conn:
            result = conn.execute(query)
            generos = result.fetchall()

        all_gen = [gen[1] for gen in generos]

        genres = [item for item in all_gen if item not in bans + grants]

        return sorted(genres), sorted(grants), sorted(bans)

    def add_genre_item(self, item):
        """
        Adds an item to the genre_list, checking for duplicates in other lists.

        Args:
            item (str): The item to be added to the genre_list.txt.

        Returns:
            str: "ok" if the item was successfully added, 
                otherwise the name of the list where the duplicate was found.
        """
        query = f"SELECT EXISTS (SELECT 1 FROM generos WHERE genero = '{item}');"

        with self.pool.connect() as conn:
            result = conn.execute(text(query))
            list = result.fetchone()[0]

        if list:
            return "na base de dados."

        # Add item

        query = f"INSERT INTO generos (genero) VALUES ('{item}');"
        with self.pool.connect() as conn:
            conn.execute(text(query))
            conn.commit()
        
        return "ok"

    def load_config(self):
        query = f"SELECT * FROM configurations WHERE config_name='{self.instance}'"
        try:
            with self.pool.connect() as conn:
                result = conn.execute(text(query))
                row = result.fetchone()
            config_dict = dict(row._mapping)
            return config_dict
        except SQLAlchemyError as e:
            return None
        except Exception as e:
            return None

    def save_config(self, data):
        query = f"""
UPDATE configurations
SET ban_list = '{data['ban_list']}',
    default_search = '{data['default_search']}',
    grant_list = '{data['grant_list']}',
    refuse_msg_ban = '{data['refuse_msg_ban']}',
    refuse_msg_grant = '{data['refuse_msg_grant']}',
    share_msg = '{data['share_msg']}',
    jukebox_title = '{data['jukebox_title']}'
WHERE id = {int(data['id'])}; 
"""
        with self.pool.connect() as conn:
            conn.execute(text(query))
            conn.commit()

    def load_report(self, rep_type, start_date, end_date):

        start_stamp = start_date.timestamp()
        end_stamp =end_date.timestamp()

        if rep_type == 'like':
            query = f"""
SELECT
    l.time_stamp,
    l.track_id,
    l.user_name,
    t.song_name,
    t.song_artist
FROM
    likes AS l
INNER JOIN
    tracks AS t ON l.track_id = t.track_id
WHERE
    l.instance = '{self.instance}' AND l.time_stamp BETWEEN {start_stamp} AND {end_stamp};
""" 
        else:
            query = f""" 
SELECT
    p.time_stamp,
    p.track_id,
    p.user_name,
    p.val_result,
    p.reason,
    t.song_name,
    t.song_artist,
    a.generos,
    a.ids_artistas
FROM
    pedidos AS p
INNER JOIN
    tracks AS t ON p.track_id = t.track_id
INNER JOIN
    artistas AS a ON p.track_id = a.track_id 
WHERE
    p.instance = '{self.instance}' AND p.val_result = '{rep_type}' AND p.time_stamp BETWEEN {start_stamp} AND {end_stamp};
"""
        with self.pool.connect() as conn:
            reusult = conn.execute(text(query))
            report = reusult.fetchall()

        return report

 
# Load config from file

    def analyze_likes(self, period=365, top=5):
        """
        Analyzes a JSON file containing track information and returns a dictionary
        with track counts, names, artists, and associated users.

        Args:
            file_path: Path to the JSON file.

        Returns:
            A dictionary with the following keys:
            - track_counts: A dictionary mapping track IDs to their counts.
            - tracks: A dictionary mapping track IDs to their names and artists.
            - users_per_track: A dictionary mapping track IDs to lists of users
                                who listened to the track.
        """
    
        start_date = datetime.today() - timedelta(days=period)
        start_stamp = start_date.timestamp() 
        end_stamp = datetime.now().timestamp()


        query = f""" 
SELECT
    t.song_name,
    t.album_url,
    t.song_artist,
    COUNT(l.track_id) AS like_count
FROM
    likes l
JOIN
    tracks t ON l.track_id = t.track_id
WHERE l.time_stamp BETWEEN {start_stamp} AND {end_stamp}  AND l.instance = '{self.instance}'
GROUP BY
    t.song_name, t.album_url, t.song_artist
ORDER BY
    like_count DESC
LIMIT {top};
    """
        with self.pool.connect() as conn:
            result = conn.execute(text(query))
            info = result.fetchall()

        j_info = []
        for line in info:
            j_info.append(line._mapping)

        return j_info

    def analyze_pass(self, period=365, top=5):
        """
Analyzes a JSON file containing track information and returns a dictionary
with track counts, names, artists, and associated users.

Args:
    file_path: Path to the JSON file.

Returns:
    A dictionary with the following keys:
    - track_counts: A dictionary mapping track IDs to their counts.
    - tracks: A dictionary mapping track IDs to their names and artists.
    - u sers_per_track: A dictionary mapping track IDs to lists of users
                        who listened to the track.
"""
  
        start_date = datetime.today() - timedelta(days=period)
        start_stamp = start_date.timestamp() 
        end_stamp = datetime.now().timestamp()

        query = f""" 
SELECT
t.song_name,
t.album_url,
t.song_artist,
COUNT(p.track_id) AS like_count
FROM
pedidos p
JOIN
tracks t ON p.track_id = t.track_id
WHERE p.time_stamp BETWEEN {start_stamp} AND {end_stamp}  AND p.instance = '{self.instance}' AND val_result = 'True'
GROUP BY
t.song_name, t.album_url, t.song_artist
ORDER BY
like_count DESC
LIMIT {top};
"""
        with self.pool.connect() as conn:
            result = conn.execute(text(query))
            info = result.fetchall()

        j_info = []
        for line in info:
            j_info.append(line._mapping)

        return j_info

    def get_serve_data(self):

        start_of_day_timestamp = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
        now_timestamp = datetime.now().timestamp()
        # timestamp for an hour ago
        hour_ago_timestamp = datetime.now() - timedelta(hours=1)

        q1 = f"""
    SELECT
    l.time_stamp,
    l.user_name,
    t.song_name,
    t.song_artist
    FROM
    likes l
    JOIN
    tracks t ON l.track_id = t.track_id
    WHERE l.time_stamp BETWEEN {start_of_day_timestamp} AND {now_timestamp}  AND l.instance = '{self.instance}';
    """
        q2 = f"""
    SELECT
    p.time_stamp,
    p.user_name,
    p.val_result,
    t.song_name,
    t.song_artist
    FROM
    pedidos p
    JOIN
    tracks t ON p.track_id = t.track_id
    WHERE p.time_stamp  BETWEEN {start_of_day_timestamp} AND {now_timestamp}  AND P.instance = '{self.instance}';
    """
        q3 = f"SELECT session_id, user_id, last_seen, user_name FROM sessions WHERE instance = '{self.instance}' AND last_seen > '{hour_ago_timestamp}';"
        
        with self.pool.connect() as conn:
            result = conn.execute(text(q1))
            like_activity = result.fetchall()
            result = conn.execute(text(q2))
            pedidos_activity = result.fetchall()
            result = conn.execute(text(q3))
            active_sessions_data = result.fetchall()

        act = []
        if len(like_activity)>0:
            for line in like_activity:
                line_dict = dict(line._mapping)
                line_dict['activity_type'] = "likes"
                act.append(line_dict)
        if len(pedidos_activity)>0:
            for line in pedidos_activity:
                line_dict = dict(line._mapping)
                line_dict['activity_type'] = "pedidos"
                act.append(line_dict)

        sorted_act = sorted(act, key=lambda item: item['time_stamp'],reverse=True)
        # format the teme_stamp of each item in sorted_act
        for item in sorted_act:
            item['time_stamp'] = datetime.fromtimestamp(item['time_stamp']).strftime('%H:%M:%S')

        active_sessions = []
        for sid, user, last_seen, user_name in active_sessions_data:
            active_sessions.append({'user_id': user, 'last_seen': last_seen, 'user_name': user_name, 'session_id': sid})

        sorted_sessions = sorted(active_sessions, key=lambda item: item['last_seen'],reverse=True)

        return sorted_act, sorted_sessions

    def get_promos(self):
        query = f"SELECT id, src FROM promos WHERE instance = '{self.instance}'"
        promos = self.sql_get_all(query)
        data = []
        for line in promos:
            data.append(dict(line._mapping))
        return data
        