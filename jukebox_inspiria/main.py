import os
import re
import json
import time
import socket
import asyncio
import urllib.parse
from glob import glob
from passlib.hash import bcrypt
from google.cloud import storage
from datetime import datetime, date

import requests

from flask import Flask, redirect, jsonify, request, render_template, session

print("my log - 001 - Evento lançado")
print("my log - 002 - Hostname: ", socket.gethostname())

app = Flask(__name__)
app.secret_key = "24322c7e4594a9f3be55923eb291aa6a6ccdedf6bd988cd4a99fbdf737c68b46" 

# Condicional para inicialização local ou na nuvem
if socket.gethostname() == 'lepdozicz':
    print("my log - 003 - Rodando local")
    #COMENTAR PARA RODAR NA NUVEM
    #As variáveis de ambiente são estabelecidas diretamente no cloud run
    #A o CLient ID e secret são diferentes pois os apps são diferentes por conta do redirect URI
    os.environ['ACCESS_TOKEN'] = "none"
    os.environ['REFRESH_TOKEN'] = "none"
    os.environ['EXPIRES_AT'] = 'none'
    os.environ['JUKE_LIST'] = 'none'
    os.environ['JUKE_LIST2'] = 'none'
    os.environ['LIKES'] = '{}'
    os.environ['ICN'] = "jukebox-446711:southamerica-east1:jukebox" 
    os.environ['DB_USER'] = "postgres"
    os.environ['DB_PASS'] = "k]a-hXIRZ0taLT}K"
    os.environ['DB_NAME'] = "postgres"
    os.environ['INSTANCE'] = "jukebox"
    CLIENT_ID = "e14b251f60b54f2f9e2d8e7f00435eee"
    CLIENT_SECRET = "b397dc26d4a845699b1781b4d0b40c82"
    REDIRECT_URI = "http://localhost:5000/callback"
    show_dialog = True
    debug = True
else:
    #COMENTAR PARA RODAR LOCAL
    print("my log - 003 - Rodando nas núvens")
    CLIENT_ID = os.environ.get("CLIENT_ID") 
    CLIENT_SECRET= os.environ.get("CLIENT_SECRET") 
    REDIRECT_URI = os.environ.get("REDIRECT_URI")
    INSTANCE = os.environ.get('INSTANCE')
    show_dialog = False
    debug = False

from jukebox_inspiria.spoti_functions import * 
from jukebox_inspiria.helper_functions import *
from jukebox_inspiria.management_functions import *
from jukebox_inspiria.sql_stuf import *

juke_sql = jukeSQL(os.environ.get('INSTANCE'), os.environ.get('ICN'), os.environ.get('DB_USER'), os.environ.get('DB_PASS'), os.environ.get('DB_NAME'))

logged_requests = ['/get_queue', '/add_2_queue', '/search_page', '/search_song', '/heart_click', '/share_click', '/serve']

AUTH_URL = "https://accounts.spotify.com/authorize"
TOKEN_URL = "https://accounts.spotify.com/api/token"
API_BASE_URL = "https://api.spotify.com/v1/"

promos = []

BUCKET_NAME = "meu-jukebox-promos"
storage_client = storage.Client()
bucket = storage_client.bucket(BUCKET_NAME)


juke_list = os.environ.get('JUKE_LIST')
juke_list = juke_list.split("', '") # Baixa a lista de musicas pedidas de str para list
juke_list2 = os.environ.get('JUKE_LIST2')
juke_list2 = juke_list2.split("', '")
likes = json.loads(os.environ.get('LIKES')) # Carrega a contagem de likes de str pata json

# Variaveis de compartilhamento
MAIN = "static/customer/main-jukebox.jpg" #imagem de fundo para compartilhamento
BAR= "static/customer/bar_foto.png" #imagem do bar
OUTPUT_PATH = "static/customer/jukebox_share.jpg" #Nome da imagem final

# Verifica acessos do usuário 
print(f"my log - 004 - Verificando acesso do usuário {juke_sql.DB_USER}")
result, config = juke_sql.check_connection()
# se sim, acertar acessos ao usiário
while config == None:
    if result=="access":
        print("my log - 007 - Erro de acesso. Revisar acesso do usuário", juke_sql.DB_USER)
        #interromper execução
        exit()
    elif result=="data":
        print(f"my log - 009 - configuração para {juke_sql.instance} não encontrada")
        print("my log - 010 - criando configuração")
        if juke_sql.create_config():
            pass
        else:
            exit()
    result, config = juke_sql.check_connection()

# SETUP FILES
def set_setup_vars():
    print("my log - 012 - Carregando variáveis de configuração")
    global config, grant_list, ban_list, msg_ban, msg_grant, promos
    instance = os.environ.get('INSTANCE')
    config = juke_sql.load_config()
    grant_list = config['list_2_grant']
    ban_list = config['list_2_ban']
    msg_ban = config['refuse_msg_ban']
    msg_grant = config['refuse_msg_grant']
    promos = juke_sql.get_promos()


set_setup_vars()

if socket.gethostname() == 'lepdozicz':
    print("Para lançar serviço: http://127.0.0.1:5000/serve")
    print("Para lançar cliente: http://127.0.0.1:5000")

#-------------------------------------------------------------------------------------
#                           ENDPOINTS START
#-------------------------------------------------------------------------------------

@app.before_request
async def before_request():
    
    if 'session_id' in session:
        session_id = session['session_id']
    else:
        if 'username' in session:
            session_id = generate_unique_id()
            session['session_id'] = session_id

    if 'session_id' in session and request.path in logged_requests:

        query = f"SELECT user_id, last_seen FROM sessions WHERE session_id = '{session_id}'"
        result = juke_sql.sql_get_one(query)
        if result:
            user_name = session.get('username')
            user_id, last_seen = result
            query = f"UPDATE sessions SET last_seen = '{datetime.now()}', user_name = '{user_name}' WHERE session_id = '{session_id}'"
            await juke_sql.sql_exe(query)
        else:
            user_id = 0
            user_name = session.get('username', 'Anônimo')
            query = f"INSERT INTO sessions (session_id, user_id, last_seen, user_name, instance) VALUES ('{session_id}', {user_id}, '{datetime.now()}', '{user_name}', '{os.environ.get('INSTANCE')}')"
            await juke_sql.sql_exe(query)

@app.route('/')
def login():
    # LOGIN PRINCIPAL
    #Verificar se é para rodar servidor ou cliente

    if os.environ['ACCESS_TOKEN'] != "none":
        # Tem um token no aambiente
        if 'username' in session:
            return redirect('get_queue?user=' + session['username'])
        else:
            user = "Anônimo"
            session['username'] = user
            session['access_level'] = 0
            session['user_id'] = 0
            return redirect('get_queue')
    else:
        # Não tem token no ambiente, verificar base sql
        tokens = juke_sql.get_token()
        if tokens is not None:
            # Tem token no banco
            os.environ['ACCESS_TOKEN'] = tokens['token']
            os.environ['REFRESH_TOKEN'] = tokens['ref_token']
            os.environ['EXPIRES_AT'] = str(tokens['expires_at'])
            user = "Anônimo"
            session['username'] = user
            session['access_level'] = 0
            session['user_id'] = 0
            return redirect('/get_queue')
        else:
            # Não há token na mase
            print("my log - 0xx - Erro de login - sem token disponível")
            return render_template("not_serving.html")

@app.route('/serve')
def serve():
    #Login principal Serviço. Mantém sessaão aberta e verifica token continuamente
    # VERIFICAR SE TEMOS O ACCESS TOKEN
    if os.environ['ACCESS_TOKEN'] == "none":

        print("my log - 013 - Iniciando primeiro login - request for token")
        scope = "user-read-playback-state user-read-currently-playing user-modify-playback-state playlist-read-private"
        params = {
            'client_id': CLIENT_ID,
            'response_type': 'code',
            'scope': scope,
            'redirect_uri': REDIRECT_URI,
            'show_dialog': False
        }
        auth_url = f"{AUTH_URL}?{urllib.parse.urlencode(params)}"
        
        session['serve_flag'] = None
        
        return redirect(auth_url)

    # VERIFICAR SE TOKEN NÃO VAI EXPIRAR em 5 minutos (300 segundos)
    if datetime.now().timestamp() > float(os.environ['EXPIRES_AT'])-300:
        session['serve_flag'] = "serve"
        return redirect('/refresh-token?origins=serve')

    session['username'] = "Server"
    session['access_level'] = 1
    session['user_id'] = 0

    #Verificar status do player
    headers = {'Authorization': f"Bearer {os.environ['ACCESS_TOKEN']}"}
    response = requests.get(API_BASE_URL + "me/player/queue", headers = headers)

    if response.text == "":
        return "No device: por favor lançar o spotify antes de lançar o serviço"
    
    resp = response.json()

    if resp['currently_playing'] == None:
        return render_template('not_serving.html')

    if len(resp['queue'])==0:
        serving = "No music"
    else:
        serving = "music"

    now_playing, juke_queue, _ = process_queue(resp, juke_list, juke_list2)

    activity, active_users_list = juke_sql.get_serve_data()

    return render_template(
        'server.html', 
        instance = os.environ.get('INSTANCE'), 
        serving = serving, 
        now_playing = now_playing, 
        juke_songs = juke_queue, 
        users = active_users_list, 
        activity = activity,
        )

@app.route('/callback')
def callback():
    # Callback recebendo autorização e gerando TOKENS
    if 'error' in request.args:
        print("my log - 015 - Callbeck - Erro no login:", request.args['error'])
        return jsonify({'error no callback': request.args['error']})
    
    if 'code' in request.args:
        req_body = {
            'code': request.args['code'],
            'grant_type': 'authorization_code',
            'redirect_uri': REDIRECT_URI,
            'client_id': CLIENT_ID,
            'client_secret': CLIENT_SECRET
        }

    response = requests.post(TOKEN_URL, data=req_body)
    token_info = response.json()

    os.environ['ACCESS_TOKEN'] = token_info['access_token']
    os.environ['REFRESH_TOKEN'] = token_info['refresh_token']
    os.environ['EXPIRES_AT'] = str(datetime.now().timestamp() + token_info['expires_in'])

    juke_sql.save_token(token_info['access_token'], os.environ['EXPIRES_AT'], token_info['refresh_token'])

    print("my log - 015 - Callback - Token recebido e login realizado. Expires in", token_info['expires_in'], "s" )
    return redirect('/serve')

@app.route('/refresh-token')
def refresh_token():
    print("my log - 0xx - Refresh token")

    if os.environ['REFRESH_TOKEN'] == "none":
        return redirect('/serve')
    
    req_body = {
        'grant_type': 'refresh_token',
        'refresh_token': os.environ['REFRESH_TOKEN'],
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET    
    }

    response = requests.post(TOKEN_URL, data=req_body)
    new_token_info = response.json()

    os.environ['ACCESS_TOKEN'] = new_token_info['access_token']
    os.environ['EXPIRES_AT'] = str(datetime.now().timestamp() + new_token_info['expires_in'])

    juke_sql.save_token(new_token_info['access_token'], datetime.now().timestamp() + new_token_info['expires_in'], os.environ['REFRESH_TOKEN'])

    return redirect('/serve')

@app.route('/get_queue')
def get_queue():
    # VERIFICAR SE TEMOS O ACCESS TOKEN
    if os.environ['ACCESS_TOKEN'] == "none":
        return redirect('/')
    # VERIFICAR SE TOKEN NÃO EXPIROU
    if datetime.now().timestamp() > float(os.environ['EXPIRES_AT']):
        return redirect('/refresh-token')
    
    user = request.args.get('user')
    if user is None:
       if 'username' in session:
          user = session['username']
       else:
        user = "Anônimo"
        session['username'] = user
        session['access_level'] = 0
        session['user_id'] = 0

    #Verificar status do player
    headers = {
        'Authorization': f"Bearer {os.environ['ACCESS_TOKEN']}"
    }

    response = requests.get(API_BASE_URL + "me/player/queue", headers = headers)

    if response.text == "":
        return "No device"
    
    resp = response.json()

    if len(resp['queue'])==0:
        return render_template('no_queue.html', config=config)

    now_playing, juke_queue, house_queue = process_queue(resp, juke_list, juke_list2)

    # montar query para busca da letra

    query_letra = urllib.parse.quote_plus(now_playing['name'] + " " + now_playing['artista_um'] + " letra")

    # Escolher ícone heart

    if key_exists(likes, now_playing['id']):
        pass
    else:
        likes[now_playing['id']] = 0
    if now_playing['id'] in session:
        heart_icon = "static/customer/horn-full-icon.png"
    else:
        heart_icon = "static/customer/horn-icon.png"
   
    # gerenciar os SPLASHES

    if 'splash_index' in session:
        if len(promos) > 0:
            splash_index = int(session['splash_index'])
            if splash_index <= len(promos):
                splash_image = promos[int(splash_index)-1]['src']
                session['splash_index'] = str(splash_index + 1)
            else:
                session['splash_index'] = '1'
                splash_index = 1
                splash_image = promos[splash_index-1]['src']
                session['splash_index'] = str(splash_index + 1)
        else:
            splash_index = -1
            splash_image = 'customer/splash_1.png'
    else:
        splash_index = 0
        splash_image = 'customer/splash_0.png'
        session['splash_index'] = '1'

    return render_template('index.html',
                            juke_songs = juke_queue, 
                            house_songs = house_queue, 
                            now_playing = now_playing, 
                            likes = likes[now_playing['id']],
                            config = config,
                            user = user,
                            heart_icon = heart_icon,
                            query_letra = query_letra,
                            splash_index = splash_index,
                            splash_image = splash_image
                           )

@app.route('/add_2_queue', methods = ['POST'])
def add_2_queue():
    # VERIFICAR SE TEMOS O ACCESS TOKEN
    if os.environ['ACCESS_TOKEN'] == "none":
        return redirect('/')
    # VERIFICAR SE TOKEN NÃO EXPIROU
    if datetime.now().timestamp() > float(os.environ['EXPIRES_AT']):
        return redirect('/refresh-token')
    
    data = request.get_json() 
    track_id = data.get('song_id')
    artist_ids = data.get('artist_ids')
    song_name = data.get('song_name')
    song_artist = data.get('song_artist')
    album_url = data.get('album_url')

    # validar musica 
    validation_string, artists_ids, generos = validate_track(artist_ids, track_id, song_name, song_artist, juke_list, API_BASE_URL, grant_list, ban_list, config, msg_ban, album_url, session['username'], os.environ.get('INSTANCE'))

    if validation_string == "valid_track":

        juke_list.append(track_id)
        juke_list2.append(session['username'])
        os.environ['JUKE_LIST'] = str(juke_list)
        os.environ['JUKE_LIST2'] = str(juke_list2)

        action_url = f"{API_BASE_URL}me/player/queue?uri=spotify%3Atrack%3A{track_id}"
        headers = {'Authorization': f"Bearer {os.environ['ACCESS_TOKEN']}"}
        response = requests.post(action_url, headers=headers)

        log_add(juke_sql, True, track_id, song_name, song_artist, validation_string, album_url, session['username'], artists_ids, generos, os.environ.get('INSTANCE'))
        time.sleep(0.5) # Wait for 1/2 second

        print(f"my log - add_2_queue - track adicionado - id: {track_id} - nome: {song_name} ")

        return jsonify({'message': 'ok'}) 
    else:
        log_add(juke_sql, False, track_id, song_name, song_artist, validation_string, album_url, session['username'], artists_ids, generos, os.environ.get('INSTANCE'))
        print(f"my log - add_2_queue - track bloqueado - id: {track_id} - nome: {song_name} - id_artista: {str(artist_ids)} - nome_artista: {song_artist} - validação: {validation_string}")
        return jsonify({'message': validation_string}) 

@app.route('/search_page')
def search_page():
    return render_template('search_song.html', user=session['username'])

@app.route('/search_song', methods = ['POST'])
def search_song():
    #if 'access_token' not in session:
    if os.environ['ACCESS_TOKEN'] == "none":
        return redirect('/')
    
    track = request.form['track']
    artist = request.form['artist']
    album = request.form['album']

    search_str = " "
    if track != "":
        search_str = search_str + "track:" + track + " "
    if artist != "":
        search_str = search_str + "artist:" + artist + " "
    if album != "":
        search_str = search_str + "album:" + album + " "
    if search_str == "":
        search_str = search_str + "genre:" + config['default_search']

    search_str = urllib.parse.quote_plus(search_str)
    search_url = f"{API_BASE_URL}search?q={search_str}&type=track&market=BR"

    headers = {
        'Authorization': f"Bearer {os.environ['ACCESS_TOKEN']}"
    }

    response = requests.get(search_url, headers=headers)
    result = response.json()

    data = process_search(result)

    

    return render_template("search_song.html", search_result=data, user=session['username'])
    
@app.route('/heart_click', methods = ['POST'])
def heart_click():
    song_id = request.form['id']

    # verificar se usuário já deu like
    if song_id not in session:
        session[song_id] = True
        # verificar se alguém mais já deu like
        if key_exists(likes, song_id):
            # adicionar um like
            likes[song_id] = likes[song_id] + 1
        else:
            #inicializar like
            likes[song_id] = 1
        
        #salvar likes para todos
        os.environ['LIKES'] = json.dumps(likes)

    new_data = {"heart_icon": "static/customer/horn-full-icon.png",
                "likes": likes[song_id]}

    print(f"my log - heart_click - like registrado em {song_id}")

    return jsonify(new_data)

@app.route('/heart_click_log', methods = ['POST'])
def heart_click_log():
    song_id = request.form['id']
    track_name = request.form['name']
    artist_name = request.form['artist']
    url = request.form['url']
    user_name = session['username']
    user_id = session['user_id']
    timestamp = datetime.now().timestamp()
    
    query1 = f"""
        INSERT INTO tracks (track_id, song_name, song_artist, album_url)
        SELECT '{song_id}', '{track_name}', '{artist_name}', '{url}'
        WHERE NOT EXISTS (
            SELECT 1 
            FROM tracks
            WHERE track_id = '{song_id}' );
        """
    
    query2 = f"""
        INSERT INTO likes (time_stamp, instance, track_id, user_name, user_id) VALUES
        ({timestamp}, '{os.environ.get('INSTANCE')}', '{song_id}', '{user_name}', {user_id}); 
        """

    asyncio.run(log_qs(juke_sql, [query1, query2]))

    return jsonify({"response":"ok"})

@app.route('/report_likes')
def report_likes():
    period = request.args.get('period')
    report = request.args.get('report')
   
    if period != None:
        period = int(period)
        start_date = datetime.now() - timedelta(days=period)
        if report == "likes":
            stats = juke_sql.analyze_likes(period, top=10)
        else:
            stats = juke_sql.analyze_pass(period, top=10)
    else:
        start_date = datetime.now() - timedelta(days=365)
        period = 365
        report = 'likes'
        if report == "likes":
            stats = juke_sql.analyze_likes(period, top=10)
        else:
            stats = juke_sql.analyze_pass(period, top=10)

    start_date = start_date.strftime("%d-%m-%Y")

    return render_template('like_list.html',
                           default_timeframe = str(period),
                           default_report = report,
                           start_date = start_date,
                           stats = stats)

@app.route('/share_click', methods = ['POST'])
def share_click():
    artist = request.form['artist']
    track = request.form['track']
    url = request.form['url']
    text = config['share_msg']
    text = re.sub(re.escape("TRACK"), track, text)
    text = re.sub(re.escape("ARTIST"), artist, text)

    if paste_images_resized(MAIN, BAR, url, OUTPUT_PATH, text):
        print(f"my log - share_click_ Compartilhamento de midia: {track}")
        return render_template('share_now_playing.html')
    else:
        print("my log - share_click - Erro em compartilhamento")
        return redirect('/get_queue' + session['username'])
    
#----------------------------------------------------------------------------
#                PÁGINAS DE CONFIGURAÇÃO                                     
#----------------------------------------------------------------------------

@app.route('/relatorios', methods = ['GET','POST'])
def reports():
    if 'username' in session:
        if session['access_level'] > 0:
            j_report = []
            report = []
            timeframe = request.form.get('timeframe')
            start_date_str = request.form.get('start_date')
            end_date_str = request.form.get('end_date')
            report_type = request.form.get('report-type')

            if report_type and timeframe: 

                if timeframe == 'today':
                    start = date.today()
                    end = date.today() + timedelta(days=1)
                    start_date = datetime(start.year, start.month, start.day)
                    end_date = datetime(end.year, end.month, end.day)
                elif timeframe == 'yesterday':
                    start = date.today() - timedelta(days=1)
                    end = date.today()
                    start_date = datetime(start.year, start.month, start.day)
                    end_date = datetime(end.year, end.month, end.day)
                elif timeframe == 'last_7_days':
                    start = datetime.today() - timedelta(days=7)
                    end = datetime.today()
                    start_date = datetime(start.year, start.month, start.day)
                    end_date = datetime(end.year, end.month, end.day)
                elif timeframe == 'last_month':
                    start = datetime.today() - timedelta(days=30)
                    end = datetime.today()
                    start_date = datetime(start.year, start.month, start.day)
                    end_date = datetime(end.year, end.month, end.day)
                elif timeframe == 'current_year':
                    start = datetime.today() - timedelta(days=365)
                    end = datetime.today()
                    start_date = datetime(start.year, start.month, start.day)
                    end_date = datetime(end.year, end.month, end.day)
                elif timeframe == 'custom':
                    try:
                        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
                        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
                    except ValueError:
                        return "Invalid date format", 400  # Handle bad date input
                    else:
                        return "Invalid timeframe selection", 400
                    
                report = juke_sql.load_report(report_type, start_date, end_date)

                for line in report:
                    line = dict(line._mapping)
                    line['time_stamp'] = datetime.fromtimestamp(line['time_stamp']).strftime("%d/%m/%Y, %H:%M:%S")
                    j_report.append(line)
            
            return render_template('reports.html', reptype = report_type, report=j_report)
        
    return "You must be an admin to log into setup pages"

@app.route('/generate_report', methods=['POST'])
def generate_report():
    timeframe = request.form.get('timeframe')
    start_date_str = request.form.get('start_date')
    end_date_str = request.form.get('end_date')
    report_type = request.form.get('report-type')

    if timeframe == 'today':
        start_date = end_date = date.today()
    elif timeframe == 'yesterday':
        start_date = end_date = date.today() - timedelta(days=1)
    elif timeframe == 'last_7_days':
        end_date = date.today()
        start_date = end_date - timedelta(days=7)
    elif timeframe == 'last_month':
        end_date = date.today().replace(day=1) - timedelta(days=1) # Last day of last month
        start_date = date(end_date.year, end_date.month, 1) # First day of last month
    elif timeframe == 'current_year':
        start_date = date(date.today().year, 1, 1)
        end_date = date.today()
    elif timeframe == 'custom':
      try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
      except ValueError:
        return "Invalid date format", 400  # Handle bad date input
    else:
        return "Invalid timeframe selection", 400

    # Now use start_date and end_date to generate your report
    # ... your report generation logic ...

    return jsonify(request.form)#render_template('report.html', start_date=start_date, end_date=end_date)

@app.route('/generos')
def genre_setup():

    msg = request.args.get('msg')
    msg_type = request.args.get('msg_type')

    headers = {
        'Authorization': f"Bearer {os.environ['ACCESS_TOKEN']}"
    }
    playlists = get_playlists(API_BASE_URL,headers)

    if msg is None:
       msg = "Bom dia!"
       msg_type = "neutral"
    
    genres, grants, bans = juke_sql.get_genre_lists()

    return render_template('generos.html', genres = genres, grants = grants, bans = bans, msgb = msg, msg_type = msg_type, playlists = playlists)

@app.route('/get_genre_from_queue')
async def get_genre_from_queue():

    msg = request.args.get('msg')
    msg_type = request.args.get('msg_type')

    # VERIFICAR SE TEMOS O ACCESS TOKEN
    if os.environ['ACCESS_TOKEN'] == "none":
        return redirect('/')
    # VERIFICAR SE TOKEN NÃO EXPIROU
    if datetime.now().timestamp() > float(os.environ['EXPIRES_AT']):
        return redirect('/refresh-token')

    #Verificar status do player e buscar fila
    headers = {
        'Authorization': f"Bearer {os.environ['ACCESS_TOKEN']}"
    }

    response = requests.get(API_BASE_URL + "me/player/queue", headers = headers)

    if response.text == "":
        return "No device"
    resp = response.json()

    #identificar artistas ebuscar generos
    new_grants = get_genres_from_queue_response(resp, API_BASE_URL, headers)
    #alimentar generos

    genres, grants, bans = juke_sql.get_genre_lists()

    for g in grants:
        genres.append(g)
    for g in new_grants:
        if g in genres:
            genres.remove(g)
        if g in bans:
            bans.remove(g)
    
    query = f"""
    UPDATE configurations 
    SET list_2_ban = '{str(bans).replace("'", '"')}',
    list_2_grant = '{str(new_grants).replace("'", '"')}'
    WHERE config_name = '{juke_sql.instance}';
    """
    await juke_sql.sql_exe(query)

    headers = {
        'Authorization': f"Bearer {os.environ['ACCESS_TOKEN']}"
    }
    playlists = get_playlists(API_BASE_URL,headers)

    return render_template('generos.html', genres = genres, grants = new_grants, bans = bans, msgb = msg, msg_type = msg_type, playlists=playlists)  

@app.route('/get_genre_from_playlist')
async def get_genre_from_playlist():
    msg = request.args.get('msg')
    msg_type = request.args.get('msg_type')
    playlist_id = request.args.get('playlist_id')

    # VERIFICAR SE TEMOS O ACCESS TOKEN
    if os.environ['ACCESS_TOKEN'] == "none":
        return redirect('/')
    # VERIFICAR SE TOKEN NÃO EXPIROU
    if datetime.now().timestamp() > float(os.environ['EXPIRES_AT']):
        return redirect('/refresh-token')

    #Verificar status do player e buscar fila
    headers = {
        'Authorization': f"Bearer {os.environ['ACCESS_TOKEN']}"
    }
    url = API_BASE_URL + f"playlists/{playlist_id}?fields=tracks%28items%28track%28artists%28id%29%29%29%29"

    response = requests.get(url, headers = headers)

    if response.text == "":
        return "No device"
    resp = response.json()


    #identificar artistas ebuscar generos
    new_grants = get_genres_from_playlist_response(resp, API_BASE_URL, headers)
    #alimentar generos

    genres, grants, bans = juke_sql.get_genre_lists()

    for g in grants:
        genres.append(g)
    for g in new_grants:
        if g in genres:
            genres.remove(g)
        if g in bans:
            bans.remove(g)
    
    query = f"""
    UPDATE configurations 
    SET list_2_ban = '{str(bans).replace("['", '["').replace("']", '"]').replace("',", '",').replace(" '", ' "').replace("'", '`')}',
    list_2_grant = '{str(new_grants).replace("['", '["').replace("']", '"]').replace("',", '",').replace(" '", ' "').replace("'", '`')}'
    WHERE config_name = '{juke_sql.instance}';
    """
    await juke_sql.sql_exe(query)

    headers = {
        'Authorization': f"Bearer {os.environ['ACCESS_TOKEN']}"
    }
    playlists = get_playlists(API_BASE_URL,headers)

    return render_template('generos.html', genres = genres, grants = new_grants, bans = bans, msgb = msg, msg_type = msg_type, playlists=playlists) 

@app.route('/clear_genres')
async def clear_genres():

    msg = request.args.get('msg')
    msg_type = request.args.get('msg_type')

    query = f"""
    UPDATE configurations
    SET
        list_2_ban = '[]',
        list_2_grant = '[]'
    WHERE
        config_name = '{juke_sql.instance}';
    """
    await juke_sql.sql_exe(query)
    genres, grants, bans = juke_sql.get_genre_lists()

    headers = {
        'Authorization': f"Bearer {os.environ['ACCESS_TOKEN']}"
    }
    playlists = get_playlists(API_BASE_URL,headers)

    return render_template('generos.html', genres = genres, grants = grants, bans = bans, msgb = msg, msg_type = msg_type, playlists=playlists)

@app.route('/move_genre_item', methods=['POST'])
async def move_genre_item():
    data = request.get_json()
    source_file = data.get('source_file')
    destination_file = data.get('destination_file')
    selectedValue = data.get('selectedValue')
    
    await move_item_between_files(juke_sql, source_file, destination_file, selectedValue)

    return jsonify({'message': 'ok'})

@app.route('/add_genre_item', methods=['POST'])
def add_genre():
    data = request.get_json()
    new_genero = data.get('new_genero')
    
    return jsonify({'message': juke_sql.add_genre_item(new_genero)})

@app.route('/setup')
def setup():
   return render_template('config.html')

@app.route('/get_config')
def get_config():
    return jsonify(juke_sql.load_config())

@app.route('/update_config', methods=['POST'])
def update_config():
    data = request.get_json()
    try:
        juke_sql.save_config(data)
        return jsonify({'message': 'Config updated successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
@app.route('/aplicar_setup')
def aplicar():
   rota = request.args.get("rota")
   set_setup_vars()
   return redirect("/" + rota)

@app.route('/promos')
def render_promos():
    return render_template('promos.html')

@app.route('/upload_to_gcs', methods=['POST'])
async def upload_to_gcs():
    try:
        file_name = request.headers.get('X-File-Name')
        if not file_name:
            return jsonify({'error': 'File name not provided'}), 400

        file_data = request.data # binary file data
        blob = bucket.blob(file_name)
        blob.upload_from_string(file_data, content_type=request.content_type) # important to include content_type
        src = blob.public_url

        query = f"INSERT INTO promos (instance, name, src) VALUES ('{juke_sql.instance}', '{file_name}', '{src}');"
        await juke_sql.sql_exe(query)

        return jsonify({'message': f'File {file_name} uploaded successfully! GCS src={src}'}), 200

    except Exception as e:
        print(f"Error uploading to GCS: {e}")
        return jsonify({'error': 'Upload failed'}), 500

@app.route('/get_promos')
def get_promo():
    query = f"SELECT id, name, src FROM promos WHERE instance = '{juke_sql.instance}'"
    promos = juke_sql.sql_get_all(query)
    data = []
    for line in promos:
        data.append(dict(line._mapping))
    return data

@app.route('/delete_promo', methods=['POST'])
async def delete_promo():
    data = request.get_json()
    promo_id = data.get('id')

    if promo_id is not None:
        
        file_name = juke_sql.sql_get_one(f"SELECT name FROM promos WHERE id = {promo_id};")
        blob = bucket.blob(file_name[0])
        blob.delete()

        #delete line from promos table
        query = f"DELETE FROM promos WHERE id = {promo_id};"
        await juke_sql.sql_exe(query)

        return jsonify({'message': 'Promo deleted successfully'}), 200
    else:
        return jsonify({'error': 'ID not provided'}), 400

#-----------------------------------------------------------------------------
#                        PÁGINAS DE LOGIN E REGIUSTRO
#-----------------------------------------------------------------------------

@app.route('/identifiquese')
def identifiquese():
   return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
async def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password_hash = bcrypt.hash(request.form['password'])
        result, user_id = await register_user(juke_sql, username, email, password_hash)
        if result:
            session['username'] = username
            session['access_level'] = 0
            session['user_id'] = user_id
            await update_session(juke_sql, username, user_id, session['session_id'])
            return redirect('/get_queue?user=' + username)
        else:
            return "Algo de errado não deu certo"
    return render_template('register.html')

@app.route('/user_login', methods=['POST'])
async def user_login():
    
    email = request.form['email']
    password = request.form['password']
    
    result, username, access_level, user_id = verify_password(juke_sql, email, password)
    if result:
        session['username'] = username
        session['access_level'] = access_level
        session['user_id'] = user_id
        await update_session(juke_sql, username, user_id, session['session_id'])
        return redirect('/get_queue?user=' + username)
    else:
        return render_template('login.html')

@app.route('/visitor_login', methods=['POST'])
async def visitor():
    visitor_name = request.form.get('visitor_name')
    if visitor_name:
        session['username'] = visitor_name
        session['access_level'] = 0
        await update_session(juke_sql, visitor_name, 0, session['session_id'])
        return redirect('/get_queue?user=' + visitor_name)
    return render_template('login.html')

@app.route('/logout')
def logout():
  session.clear()
  return 'Você foi deslogado'

#----------------------------------------------------------------------------
#                                    RODAR
#----------------------------------------------------------------------------

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=debug)