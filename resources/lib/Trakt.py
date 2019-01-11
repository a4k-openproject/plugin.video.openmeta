import time, requests
import xbmc, xbmcgui
from resources.lib import text
from resources.lib import dialogs
from resources.lib import settings
from resources.lib.xswift2 import plugin

API_ENDPOINT  = 'https://api-v2launch.trakt.tv'
REDIRECT_URI  = 'urn:ietf:wg:oauth:2.0:oob'
LIST_PRIVACY_IDS = ('private', 'friends', 'public')
TCI = plugin.get_setting(settings.SETTING_TRAKT_API_CLIENT_ID, str)
TCS = plugin.get_setting(settings.SETTING_TRAKT_API_CLIENT_SECRET, str)
if len(TCI) == 64 and len(TCS) == 64:
	CLIENT_ID = TCI
	CLIENT_SECRET = TCS
else:
	CLIENT_ID     = 'd1feff7915af479f8d14cf9afcc2e5a2fb5534512021d58447985e2fd555b26d'
	CLIENT_SECRET = '68dd208db29a54c56753549a6dbc635e7e3a1e03104b15fc0dd00555f1a549cb'

def call_trakt(path, params = {}, data=None, is_delete=False, with_auth=True, pagination=False, page=1):
	params = dict([(k, text.to_utf8(v)) for k, v in params.items() if v])
	headers = {
		'Content-Type': 'application/json',
		'trakt-api-version': '2',
		'trakt-api-key': CLIENT_ID
		}

	def send_query():
		if with_auth:
			try:
				expires_at = plugin.get_setting(settings.SETTING_TRAKT_EXPIRES_AT, int)
				if time.time() > expires_at:
					trakt_refresh_token()
			except:
				pass
			token = plugin.get_setting(settings.SETTING_TRAKT_ACCESS_TOKEN, unicode)
			if token:
				headers['Authorization'] = 'Bearer %s' % token
		if data is not None:
			assert not params
			return requests.post('%s/%s' % (API_ENDPOINT, path), json=data, headers=headers)
		elif is_delete:
			return requests.delete('%s/%s' % (API_ENDPOINT, path), headers=headers)
		else:
			return requests.get('%s/%s' % (API_ENDPOINT, path), params, headers=headers)

	def paginated_query(page):
		lists = []
		params['page'] = page
		results = send_query()
		title = 'Authenticate Trakt'
		msg = 'Do you want to authenticate with Trakt now?'
		if with_auth and results.status_code == 401 and dialogs.yesno(title, msg) and trakt_authenticate():
			response = paginated_query(1)
			return response
		results.raise_for_status()
		results.encoding = 'utf-8'
		lists.extend(results.json())
		return lists, results.headers['X-Pagination-Page-Count']
	if pagination == False:
		response = send_query()
		if with_auth and response.status_code == 401 and dialogs.yesno(title, msg) and trakt_authenticate(): response = send_query()
		response.raise_for_status()
		response.encoding = 'utf-8'
		return response.json()
	else:
		response, numpages = paginated_query(page)
		return response, numpages

def search_trakt(**search_params):
	return call_trakt('search', search_params)

def find_trakt_ids(id_type, id, query=None, type=None, year=None):
	response = search_trakt(id_type=id_type, id=id)
	if not response and query:
		response = search_trakt(query=query, type=type, year=year)
		if response and len(response) > 1:
			response = [r for r in response if r[r['type']]['title'] == query]
	if response:
		content = response[0]
		return content[content['type']]['ids']
	return {}

def trakt_get_device_code():
	data = {'client_id': CLIENT_ID}
	return call_trakt('oauth/device/code', data=data, with_auth=False)

def trakt_get_device_token(device_codes):
	data = {
		'code': device_codes['device_code'],
		'client_id': CLIENT_ID,
		'client_secret': CLIENT_SECRET
		}
	start = time.time()
	expires_in = device_codes['expires_in']
	progress_dialog = xbmcgui.DialogProgress()
	title = 'Authenticate Trakt'
	msg = 'Please go to  https://trakt.tv/activate  and enter the code'
	progress_dialog.create(title, msg, str(device_codes['user_code']))
	try:
		time_passed = 0
		while not xbmc.abortRequested and not progress_dialog.iscanceled() and time_passed < expires_in:            
			try:
				response = call_trakt('oauth/device/token', data=data, with_auth=False)
			except requests.HTTPError as e:
				if e.response.status_code != 400:
					raise e
				progress = int(100 * time_passed / expires_in)
				progress_dialog.update(progress)
				xbmc.sleep(max(device_codes['interval'], 1)*1000)
			else:
				return response
			time_passed = time.time() - start
	finally:
		progress_dialog.close()
		del progress_dialog
	return None

def trakt_refresh_token():
	data = {
		'client_id': CLIENT_ID,
		'client_secret': CLIENT_SECRET,
		'redirect_uri': REDIRECT_URI,
		'grant_type': 'refresh_token',
		'refresh_token': plugin.get_setting(settings.SETTING_TRAKT_REFRESH_TOKEN, unicode)
		}
	response = call_trakt('oauth/token', data=data, with_auth=False)
	if response:
		plugin.set_setting(settings.SETTING_TRAKT_ACCESS_TOKEN, response['access_token'])
		plugin.set_setting(settings.SETTING_TRAKT_REFRESH_TOKEN, response['refresh_token'])

def trakt_authenticate():
	code = trakt_get_device_code()
	token = trakt_get_device_token(code)
	if token:
		expires_at = time.time() + 60*60*24*30
		plugin.set_setting(settings.SETTING_TRAKT_EXPIRES_AT, str(expires_at))
		plugin.set_setting(settings.SETTING_TRAKT_ACCESS_TOKEN, token['access_token'])
		plugin.set_setting(settings.SETTING_TRAKT_REFRESH_TOKEN, token['refresh_token'])
		return True
	return False

def add_list(name, privacy_id=None, description=None):
	data = {
		'name': name,
		'description': description or '',
		'privacy': privacy_id or LIST_PRIVACY_IDS[0]
		}
	return call_trakt('users/me/lists', data=data)

def del_list(list_slug):
	return call_trakt('users/me/lists/%s' % list_slug, is_delete=True)

@plugin.cached(TTL=60, cache='Trakt')
def trakt_get_hidden_items(type):
	return call_trakt('users/hidden/%s' % type)

def trakt_get_collection(type):
	params = {'extended': 'full'}
	return call_trakt('sync/collection/%s' % type, params)

def trakt_get_lists():
	return call_trakt('users/me/lists')

def trakt_get_liked_lists(page):
	params = {'limit': '20'}
	result, pages = call_trakt('users/likes/lists', params, pagination=True, page=page)
	return result, pages

def trakt_get_watchlist(type):
	params = {'extended': 'full'}
	return call_trakt('sync/watchlist/%s' % type, params)

@plugin.cached(TTL=60, cache='Trakt')
def trakt_get_calendar():
	params = {'extended': 'full'}
	return call_trakt('calendars/my/shows', params)

@plugin.cached(TTL=60, cache='Trakt')
def trakt_get_netflix_collected_shows(page):
	params = {'networks': 'Netflix', 'extended': 'full', 'limit': '20'}
	result, pages = call_trakt('shows/collected/weekly?', params, pagination=True, page=page, with_auth=False)
	return result, pages

@plugin.cached(TTL=60, cache='Trakt')
def trakt_get_next_episodes():
	params = {'extended': 'noseasons,full'}
	shows = call_trakt('sync/watched/shows', params)
	hidden_shows = [item['show']['ids']['trakt'] for item in trakt_get_hidden_items('progress_watched') if item['type'] == 'show']
	items = []
	for item in shows:
		show = item['show']
		id = show['ids']['trakt']
		if id in hidden_shows:
			continue
		response = call_trakt('shows/%s/progress/watched' % id)    
		if response['next_episode']:
			next_episode = response['next_episode']
			next_episode['show'] = show
			items.append(next_episode)
	return items

@plugin.cached(TTL=60, cache='Trakt')
def trakt_get_latest_releases_movies():
	params = {'extended': 'full'}
	return call_trakt('users/giladg/lists/latest-releases/items', params, pagination=False, with_auth=False)

@plugin.cached(TTL=60, cache='Trakt')
def trakt_get_imdb_top_rated_movies(page):
	params = {'extended': 'full', 'limit': '20'}
	result, pages = call_trakt('users/justin/lists/imdb-top-rated-movies/items', params, pagination=True, page=page, with_auth=False)
	return result, pages

@plugin.cached(TTL=60, cache='Trakt')
def trakt_get_trending_shows_paginated(page):
	params = {'extended': 'full', 'limit': '20'}
	result, pages = call_trakt('shows/trending', params, pagination=True, page=page, with_auth=False)
	return result, pages

@plugin.cached(TTL=60, cache='Trakt')
def trakt_get_popular_shows_paginated(page):
	params = {'extended': 'full', 'limit': '20'}
	result, pages = call_trakt('shows/popular', params, pagination=True, page=page, with_auth=False)
	return result, pages

@plugin.cached(TTL=60, cache='Trakt')
def trakt_get_watched_shows_paginated(page):
	params = {'extended': 'full', 'limit': '20'}
	result, pages = call_trakt('shows/watched/weekly', params, pagination=True, page=page, with_auth=False)
	return result, pages

@plugin.cached(TTL=60, cache='Trakt')
def trakt_get_collected_shows_paginated(page):
	params = {'extended': 'full', 'limit': '20'}
	result, pages = call_trakt('shows/collected/weekly', params, pagination=True, page=page, with_auth=False)
	return result, pages

@plugin.cached(TTL=60, cache='Trakt')
def trakt_get_trending_movies_paginated(page):
	params = {'extended': 'full', 'limit': '20'}
	result, pages = call_trakt('movies/trending', params, pagination=True, page=page, with_auth=False)
	return result, pages

@plugin.cached(TTL=60, cache='Trakt')
def trakt_get_popular_movies_paginated(page):
	params = {'extended': 'full', 'limit': '20'}
	result, pages = call_trakt('movies/popular', params, pagination=True, page=page, with_auth=False)
	return result, pages

@plugin.cached(TTL=60, cache='Trakt')
def trakt_get_watched_movies_paginated(page):
	params = {'extended': 'full', 'limit': '20'}
	result, pages = call_trakt('movies/watched/weekly', params, pagination=True, page=page, with_auth=False)
	return result, pages

@plugin.cached(TTL=60, cache='Trakt')
def trakt_get_collected_movies_paginated(page):
	params = {'extended': 'full', 'limit': '20'}
	result, pages = call_trakt('movies/collected/weekly', params, pagination=True, page=page, with_auth=False)
	return  result, pages

@plugin.cached(TTL=60, cache='Trakt')
def trakt_get_related_movies_paginated(imdb_id, page):
	params = {'extended': 'full', 'limit': '20'}
	return call_trakt('movies/%s/related' % imdb_id, params, pagination=True, page=page, with_auth=False)

@plugin.cached(TTL=60, cache='Trakt')
def get_list(user, slug):
	params = {'extended': 'full'}
	return call_trakt('users/%s/lists/%s/items' % (user, slug), params, pagination=False)
    
@plugin.cached(TTL=60*24, cache='Trakt')
def trakt_get_genres(type):
	return call_trakt('genres/%s' % type)

@plugin.cached(TTL=60, cache='Trakt')
def get_show(id):
	params = {'extended': 'full'}
	return call_trakt('shows/%s' % id, params)

def get_latest_episode(id):
	params = {'extended': 'full'}
	return call_trakt('shows/%s/last_episode' % id, params)

@plugin.cached(TTL=60, cache='Trakt')
def get_season(id,season_number):
	params = {'extended': 'full'}
	seasons = call_trakt('shows/%s/seasons' % id, params)
	for season in seasons:
		if season['number'] == season_number:
			return season

@plugin.cached(TTL=60, cache='Trakt')
def get_seasons(id):
	params = {'extended': 'full'}
	seasons = call_trakt('shows/%s/seasons' % id, params)
	return seasons

@plugin.cached(TTL=60, cache='Trakt')
def get_episode(id, season, episode):
	params = {'extended': 'full'}
	return call_trakt('shows/%s/seasons/%s/episodes/%s' % (id, season, episode), params)

@plugin.cached(TTL=60, cache='Trakt')
def get_movie(id):
	params = {'extended': 'full'}
	return call_trakt('movies/%s' % id, params)

@plugin.cached(TTL=60, cache='Trakt')
def search_for_list(list_name, page):
	params = {'type': 'list', 'query': list_name, 'limit': '20'}
	results, pages = call_trakt('search', params, pagination=True, page=page)
	return results, pages

@plugin.cached(TTL=60, cache='Trakt')
def search_for_movie(movie_title, page):
	params = {'type': 'movie', 'query': movie_title}
	results = call_trakt('search', params)
	return results

@plugin.cached(TTL=60, cache='Trakt')
def search_for_movie_paginated(movie_title, page):
	params = {'type': 'movie', 'query': movie_title, 'limit': '20'}
	results, pages = call_trakt('search', params, pagination=True, page=page)
	return results, pages

@plugin.cached(TTL=60, cache='Trakt')
def search_for_tvshow_paginated(show_name, page):
	params = {'type': 'show', 'query': show_name, 'limit': '20'}
	results, pages = call_trakt('search', params, pagination=True, page=page)
	return results, pages