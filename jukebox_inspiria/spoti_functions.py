import requests

def get_username(id, juke_list, juke_list2):
    try:
        index = juke_list.index(id)
        return juke_list2[index]
    except ValueError:
        return 'playlist da casa'

def process_queue(resp, juke_list, juke_list2):
    """
    Processa retorno da fila para identificar dados necessários e montar um JSON mais leve
    """
    np = resp['currently_playing']
    jk_list = juke_list.copy()

    now_playing = {}
    now_playing['album_name'] = np['album']['name']
    now_playing['url'] = np['album']['images'][0]['url']
    now_playing['name'] = np['name']
    now_playing['id'] = np['id']
    now_playing['artista_um'] = np['artists'][0]['name']
    artistas = np['artists'][0]['name']
    if len(np['artists']) > 1:
        for artist in np['artists'][1:]:
            artistas = artistas + "&" + artist['name']
    now_playing['artist'] = artistas
    now_playing['username'] = get_username(np['id'], juke_list, juke_list2)

    queue = resp['queue']
    juke_queue = []
    house_queue = []
    for song in queue:
        try:
            song_dict = {}
            song_dict['album_name'] = song['album']['name']
            song_dict['url'] = song['album']['images'][0]['url']
            song_dict['name'] = song['name']
            artistas = song['artists'][0]['name']
            if len(song['artists']) > 1:
                for artist in song['artists'][1:]:
                    artistas = artistas + "&" + artist['name']
            song_dict['artist'] = artistas
            if song['id'] in jk_list:
                song_dict['username'] = get_username(song['id'], juke_list, juke_list2)
                juke_queue.append(song_dict)
                jk_list.remove(song['id'])
            else:
                song_dict['username'] = 'play list da casa'
                house_queue.append(song_dict)
        except:
            print("my log - xxx - error on queue processing-", str(song))
    return now_playing, juke_queue, house_queue

def process_search(resp):
    """
    Processa retorno de busca de músicas para retornar um json mais leve
    """
    if 'tracks' in resp:
        tracks = resp['tracks']['items']

        search_result = []
        for track in tracks:
            try:
                track_dict = {}
                track_dict['album_name'] = track['album']['name']
                track_dict['url'] = track['album']['images'][0]['url']
                track_dict['name'] = track['name']
                artistas = track['artists'][0]['name']
                artistas_id = [track['artists'][0]['id']]
                if len(track['artists']) > 1:
                    for artist in track['artists'][1:]:
                        artistas = artistas + "&" + artist['name']
                        artistas_id.append(artist['id'])
                track_dict['artist'] = artistas
                track_dict['artist_id'] = artistas_id
                track_dict['id'] = track['id']
                search_result.append(track_dict)
            except:
                print("my log - xxx - error on search  processing-", str(track))
    else:
        search_result = []

    return search_result

def get_genres_from_queue_response(resp, API_BASE_URL, headers):

    generos = []

    #retirar generos de "currently_playing"
    queue = resp['currently_playing']
    for artist in queue['artists']:
        artist_id = artist['id']
        artist_gs = get_artist_genres(artist_id, API_BASE_URL, headers)
        for artist_g in artist_gs:
            if artist_g not in generos:
                generos.append(artist_g)
    
    #retirar generos de "queue"
    queue = resp['queue']
    for song in queue:
        for artist in song['artists']:
            artist_id = artist['id']
            artist_gs = get_artist_genres(artist_id, API_BASE_URL, headers)
            for artist_g in artist_gs:
                if artist_g not in generos:
                    generos.append(artist_g)

    return generos

def get_genres_from_playlist_response(resp, API_BASE_URL, headers):

    generos = []
    #retirar generos de lista
    items = resp['tracks']['items']
    for item in items:
        artists = item['track']['artists']
        for artist in artists:
            artist_id = artist['id']
            artist_gs = get_artist_genres(artist_id, API_BASE_URL, headers)
            for artist_g in artist_gs:
                if artist_g not in generos:
                    generos.append(artist_g)
    
    return generos

def get_artist_genres(artist_id, API_BASE_URL, headers):

    search_url = f"{API_BASE_URL}artists/{artist_id}"

    response = requests.get(search_url, headers=headers)
    result = response.json()

    return result['genres']

def get_playlists(API_BASE_URL, headers):

    search_url = f"{API_BASE_URL}me/playlists?limit=50&offset=0"
    response = requests.get(search_url, headers=headers)
    result = response.json()
   

    playlists = []
    for playlist in result['items']:
        playlists.append(
            {"value": playlist['id'],
            "text": playlist['name']}
        )
    
    return playlists