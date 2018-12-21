import os
import xbmc, xbmcvfs, xbmcplugin
from resources.lib import text
from resources.lib import Trakt
from resources.lib import tools
from resources.lib import dialogs
from resources.lib import settings
from resources.lib import nav_base
from resources.lib import meta_info
from resources.lib import lib_movies
from resources.lib import playrandom
from resources.lib import play_movies
from resources.lib.rpc import RPC
from resources.lib.xswift2 import plugin

ICON = nav_base.get_meta_icon_path()
FANART = nav_base.get_background_path()
SORT = [
	xbmcplugin.SORT_METHOD_UNSORTED,
	xbmcplugin.SORT_METHOD_LABEL,
	xbmcplugin.SORT_METHOD_VIDEO_YEAR,
	xbmcplugin.SORT_METHOD_GENRE,
	xbmcplugin.SORT_METHOD_VIDEO_RATING,
	xbmcplugin.SORT_METHOD_PLAYCOUNT]
SORTRAKT = [
	xbmcplugin.SORT_METHOD_UNSORTED,
	xbmcplugin.SORT_METHOD_LABEL,
	xbmcplugin.SORT_METHOD_VIDEO_YEAR,
	xbmcplugin.SORT_METHOD_GENRE,
	xbmcplugin.SORT_METHOD_VIDEO_RATING,
	xbmcplugin.SORT_METHOD_PLAYCOUNT,
	xbmcplugin.SORT_METHOD_DURATION]

@plugin.route('/movies')
def movies():
	items = [
		{
			'label': 'Genres (TMDb)',
			'path': plugin.url_for('tmdb_movies_genres'),
			'icon': nav_base.get_icon_path('genres'),
			'thumbnail': nav_base.get_icon_path('genres')
		},
		{
			'label': 'Blockbusters (TMDb)',
			'path': plugin.url_for('tmdb_movies_blockbusters', page=1),
			'icon': nav_base.get_icon_path('most_voted'),
			'thumbnail': nav_base.get_icon_path('most_voted'),
			'context_menu': [
				('Play (random)', 'RunPlugin(%s)' % plugin.url_for('tmdb_movies_play_random_blockbuster'))]
		},
		{
			'label': 'In theatres (TMDb)',
			'path': plugin.url_for('tmdb_movies_now_playing', page=1),
			'icon': nav_base.get_icon_path('intheatres'),
			'thumbnail': nav_base.get_icon_path('intheatres'),
			'context_menu': [
				('Play (random)', 'RunPlugin(%s)' % plugin.url_for('tmdb_movies_play_random_now_playing'))]
		},
		{
			'label': 'Popular (TMDb)',
			'path': plugin.url_for('tmdb_movies_popular', page=1),
			'icon': nav_base.get_icon_path('popular'),
			'thumbnail': nav_base.get_icon_path('popular'),
			'context_menu': [
				('Play (random)', 'RunPlugin(%s)' % plugin.url_for('tmdb_movies_play_random_popular'))]
		},
		{
			'label': 'Top rated (TMDb)',
			'path': plugin.url_for('tmdb_movies_top_rated', page=1),
			'icon': nav_base.get_icon_path('top_rated'),
			'thumbnail': nav_base.get_icon_path('top_rated'),
			'context_menu': [
				('Play (random)', 'RunPlugin(%s)' % plugin.url_for('tmdb_movies_play_random_top_rated'))]
		},
		{
			'label': 'Most watched (Trakt)',
			'path': plugin.url_for('trakt_movies_watched', page=1),
			'icon': nav_base.get_icon_path('traktwatchlist'),
			'thumbnail': nav_base.get_icon_path('traktwatchlist'),
			'context_menu': [
				('Play (random)', 'RunPlugin(%s)' % plugin.url_for('trakt_movies_play_random_watched'))]
		},
		{
			'label': 'Most collected (Trakt)',
			'path': plugin.url_for('trakt_movies_collected', page=1),
			'icon': nav_base.get_icon_path('traktcollection'),
			'thumbnail': nav_base.get_icon_path('traktcollection'),
			'context_menu': [
				('Play (random)', 'RunPlugin(%s)' % plugin.url_for('trakt_movies_play_random_collected'))]
		},
		{
			'label': 'Popular (Trakt)',
			'path': plugin.url_for('trakt_movies_popular', page=1),
			'icon': nav_base.get_icon_path('traktrecommendations'),
			'thumbnail': nav_base.get_icon_path('traktrecommendations'),
			'context_menu': [
				('Play (random)', 'RunPlugin(%s)' % plugin.url_for('trakt_movies_play_random_popular'))]
		},
		{
			'label': 'Trending (Trakt)',
			'path': plugin.url_for('trakt_movies_trending', page=1),
			'icon': nav_base.get_icon_path('trending'),
			'thumbnail': nav_base.get_icon_path('trending'),
			'context_menu': [
				('Play (random)', 'RunPlugin(%s)' % plugin.url_for('trakt_movies_play_random_trending'))]
		},
		{
			'label': 'Latest releases (Trakt)',
			'path': plugin.url_for('trakt_movies_latest_releases'),
			'icon': nav_base.get_icon_path('traktcalendar'),
			'thumbnail': nav_base.get_icon_path('traktcalendar'),
			'context_menu': [
				('Play (random)', 'RunPlugin(%s)' % plugin.url_for('trakt_movies_play_random_latest_releases'))]
		},
		{
			'label': 'Top 250 (IMDB)',
			'path': plugin.url_for('trakt_movies_imdb_top_rated', page=1),
			'icon': nav_base.get_icon_path('imdb'),
			'thumbnail': nav_base.get_icon_path('imdb'),
			'context_menu': [
				('Play (random)', 'RunPlugin(%s)' % plugin.url_for('trakt_movies_play_random_imdb_top_rated'))]
		},
		{
			'label': 'Search movies',
			'path': plugin.url_for('movies_search'),
			'icon': nav_base.get_icon_path('search'),
			'thumbnail': nav_base.get_icon_path('search')
		}]
	for item in items:
		item['properties'] = {'fanart_image': FANART}
	return items

@plugin.route('/movies/tmdb/blockbusters/<page>')
def tmdb_movies_blockbusters(page, raw=False):
	plugin.set_content('movies')
	from resources.lib.TheMovieDB import Discover
	result = Discover().movie(language='en', append_to_response='external_ids,videos', **{'page': page, 'sort_by': 'revenue.desc'})
	if raw:
		return result
	else:
		return list_tmdb_movies(result)

@plugin.route('/movies/tmdb/random_blockbuster')
def tmdb_movies_play_random_blockbuster():
	result = {}
	pages = plugin.get_setting(settings.SETTING_RANDOM_PAGES, int) + 1
	for i in range(1, pages):
		result.update(tmdb_movies_blockbusters(i, raw=True))
	tmdb_movies_play_random(result)

@plugin.route('/movies/tmdb/now_playing/<page>')
def tmdb_movies_now_playing(page, raw=False):
	plugin.set_content('movies')
	from resources.lib.TheMovieDB import Movies
	result = Movies().now_playing(language='en', page=page, append_to_response='external_ids,videos')
	if raw:
		return result
	else:
		return list_tmdb_movies(result)

@plugin.route('/movies/tmdb/random_now_playing')
def tmdb_movies_play_random_now_playing():
	result = {}
	pages = plugin.get_setting(settings.SETTING_RANDOM_PAGES, int) + 1
	for i in range(1, pages):
		result.update(tmdb_movies_now_playing(i, raw=True))
	tmdb_movies_play_random(result)


@plugin.route('/movies/tmdb/popular/<page>')
def tmdb_movies_popular(page, raw=False):
	plugin.set_content('movies')
	from resources.lib.TheMovieDB import Movies
	result = Movies().popular(language='en', page=page)
	if raw:
		return result
	else:
		return list_tmdb_movies(result)

@plugin.route('/movies/tmdb/random_popular')
def tmdb_movies_play_random_popular():
	result = {}
	pages = plugin.get_setting(settings.SETTING_RANDOM_PAGES, int) + 1
	for i in range(1, pages):
		result.update(tmdb_movies_popular(i, raw=True))
	tmdb_movies_play_random(result)


@plugin.route('/movies/tmdb/top_rated/<page>')
def tmdb_movies_top_rated(page, raw=False):
	plugin.set_content('movies')
	from resources.lib.TheMovieDB import Movies
	result = Movies().top_rated(language='en', page=page, append_to_response='external_ids,videos')
	if raw:
		return result
	else:
		return list_tmdb_movies(result)

@plugin.route('/movies/tmdb/random_top_rated')
def tmdb_movies_play_random_top_rated():
	result = {}
	pages = plugin.get_setting(settings.SETTING_RANDOM_PAGES, int) + 1
	for i in range(1, pages):
		result.update(tmdb_movies_top_rated(i, raw=True))
	tmdb_movies_play_random(result)


@plugin.route('/movies/search')
def movies_search():
	term = plugin.keyboard(heading='Enter search string')
	if term != None and term != '':
		return movies_search_term(term, 1)
	else:
		return

@plugin.route('/movies/search/edit/<term>')
def movies_search_edit(term):
	term = plugin.keyboard(default=term, heading='Enter search string')
	if term != None and term != '':
		return movies_search_term(term, 1)
	else:
		return

@plugin.route('/movies/search_term/<term>/<page>')
def movies_search_term(term, page):
	items = [
		{
			'label': '(TMDb) Search - %s' % term,
			'path': plugin.url_for('tmdb_movies_search_term', term=term, page=1),
			'icon': nav_base.get_icon_path('movies'),
			'thumbnail': nav_base.get_icon_path('movies')
		},
		{
			'label': '(Trakt) Search - %s' % term,
			'path': plugin.url_for('trakt_movies_search_term', term=term, page=1),
			'icon': nav_base.get_icon_path('movies'),
			'thumbnail': nav_base.get_icon_path('movies')
		},
		{
			'label': 'Edit search string',
			'path': plugin.url_for('movies_search_edit', term=term),
			'icon': nav_base.get_icon_path('search'),
			'thumbnail': nav_base.get_icon_path('search')
		}]
	for item in items:
		item['properties'] = {'fanart_image': FANART}
	return items

@plugin.route('/movies/trakt/search')
def trakt_movies_search():
	term = plugin.keyboard(heading='Enter search string')
	if term != None and term != '':
		return trakt_movies_search_term(term, 1)
	else:
		return

@plugin.route('/movies/trakt/search/<term>/<page>')
def trakt_movies_search_term(term, page):
	plugin.set_content('movies')
	results, pages = Trakt.search_for_movie_paginated(term, page)
	return list_trakt_search_items(results, pages, page)

@plugin.route('/movies/trakt/latest_releases')
def trakt_movies_latest_releases(raw=False):
	plugin.set_content('movies')
	results = sorted(Trakt.trakt_get_latest_releases_movies(), key=lambda k: k['listed_at'], reverse=True)
	if raw:
		return results
	else:
		movies = [meta_info.get_trakt_movie_metadata(item['movie']) for item in results]
		items = [make_movie_item(movie) for movie in movies]
		return plugin.finish(items=items)

@plugin.route('/movies/trakt/random_latest_releases')
def trakt_movies_play_random_latest_releases():
	results = trakt_movies_latest_releases(raw=True)
	trakt_movies_play_random(results)

@plugin.route('/movies/trakt/imdb_top_rated_movies/<page>')
def trakt_movies_imdb_top_rated(page, raw=False):
	plugin.set_content('movies')
	results, pages = Trakt.trakt_get_imdb_top_rated_movies(page)
	if raw:
		return results
	else:
		return list_trakt_movies(results, pages, page)

@plugin.route('/movies/trakt/random_imdb_top_rated')
def trakt_movies_play_random_imdb_top_rated():
	result = []
	pages = plugin.get_setting(settings.SETTING_RANDOM_PAGES, int) + 1
	for i in range(1, pages):
		result.extend(trakt_movies_imdb_top_rated(i, raw=True))
	trakt_movies_play_random(result)

@plugin.route('/movies/trakt/watched/<page>')
def trakt_movies_watched(page, raw=False):
	plugin.set_content('movies')
	results, pages = Trakt.trakt_get_watched_movies_paginated(page)
	if raw:
		return results
	else:
		return list_trakt_movies(results, pages, page)

@plugin.route('/movies/trakt/random_watched')
def trakt_movies_play_random_watched():
	result = []
	pages = plugin.get_setting(settings.SETTING_RANDOM_PAGES, int) + 1
	for i in range(1, pages):
		result.extend(trakt_movies_watched(i, raw=True))
	trakt_movies_play_random(result)

@plugin.route('/movies/trakt/collected/<page>')
def trakt_movies_collected(page, raw=False):
	plugin.set_content('movies')
	results, pages = Trakt.trakt_get_collected_movies_paginated(page)
	if raw:
		return results
	else:
		return list_trakt_movies(results, pages, page)

@plugin.route('/movies/trakt/random_collected')
def trakt_movies_play_random_collected():
	result = []
	pages = plugin.get_setting(settings.SETTING_RANDOM_PAGES, int) + 1
	for i in range(1, pages):
		result.extend(trakt_movies_collected(i, raw=True))
	trakt_movies_play_random(result)

@plugin.route('/movies/trakt/popular/<page>')
def trakt_movies_popular(page, raw=False):
	plugin.set_content('movies')
	results, pages = Trakt.trakt_get_popular_movies_paginated(page)
	if raw:
		return results
	else:
		return list_trakt_movies([{u'movie': m} for m in results], pages, page)

@plugin.route('/movies/trakt/random_popular') 
def trakt_movies_play_random_popular():
	result = []
	pages = plugin.get_setting(settings.SETTING_RANDOM_PAGES, int) + 1
	for i in range(1, pages):
		result.extend(trakt_movies_popular(i, raw=True))
	trakt_movies_play_random(result)


@plugin.route('/movies/trakt/trending/<page>')
def trakt_movies_trending(page, raw=False):
	plugin.set_content('movies')
	results, pages = Trakt.trakt_get_trending_movies_paginated(page)
	if raw:
		return results
	else:
		return list_trakt_movies(results, pages, page)

@plugin.route('/movies/trakt/random_trending')
def trakt_movies_play_random_trending():
	result = []
	pages = plugin.get_setting(settings.SETTING_RANDOM_PAGES, int) + 1
	for i in range(1, pages):
		result.extend(trakt_movies_trending(i, raw=True))
	trakt_movies_play_random(result)


@plugin.route('/movies/tmdb/search')
def tmdb_movies_search():
	term = plugin.keyboard(heading='Enter search string')
	if term != None and term != '':
		return tmdb_movies_search_term(term, 1)
	else:
		return

@plugin.route('/movies/tmdb/search_term/<term>/<page>')
def tmdb_movies_search_term(term, page):
	plugin.set_content('movies')
	from resources.lib.TheMovieDB import Search
	result = Search().movie(query=term, language='en', page=page, append_to_response='external_ids,videos')
	return list_tmdb_items(result)

@plugin.route('/movies/trakt/person/<person_id>')
def trakt_movies_person(person_id, raw=False):
	plugin.set_content('actors')
	result = Trakt.get_person_movies(person_id)['cast']
	if raw:
		return result
	else:
		return list_trakt_persons(result)

@plugin.route('/movies/tmdb/genres')
def tmdb_movies_genres():
	plugin.set_content('genres')
	genres = nav_base.get_base_genres()
	items = sorted([
		{
			'label': name,
			'icon': nav_base.get_genre_icon(id),
			'path': plugin.url_for('tmdb_movies_genre', id=id, page=1),
			'context_menu': [
				('Play (random)', 'RunPlugin(%s)' % plugin.url_for('tmdb_movies_play_random_genre', id = id))]
		} for id, name in genres.items()], key=lambda k: k['label'])
	for item in items:
		item['properties'] = {'fanart_image': FANART}
	return plugin.finish(items=items, sort_methods=SORT)

@plugin.route('/movies/genre/<id>/<page>')
def tmdb_movies_genre(id, page, raw=False):
	plugin.set_content('movies')
	from resources.lib.TheMovieDB import Genres
	result = Genres(id).movies(id=id, language='en', page=page)
	if raw:
		return result
	else:
		return list_tmdb_movies(result)

@plugin.route('/movies/tmdb/random_genre/<id>')
def tmdb_movies_play_random_genre(id):
	result = {}
	pages = plugin.get_setting(settings.SETTING_RANDOM_PAGES, int) + 1
	for i in range(1, pages):
		result.update(tmdb_movies_genre(id, i, raw=True))
	tmdb_movies_play_random(result)

@plugin.route('/movies/add_to_library/<src>/<id>')
def movies_add_to_library(src, id):
	from resources.lib.TheMovieDB import Movies
	library_folder = lib_movies.setup_library(plugin.get_setting(settings.SETTING_MOVIES_LIBRARY_FOLDER, unicode))
	if library_folder == False:
		return
	date = None
	if src == 'tmdb':
		movie = Movies(id).info()
		date = text.date_to_timestamp(movie.get('release_date'))
		imdb_id = movie.get('imdb_id')
		if imdb_id:
			src = 'imdb'
			id = imdb_id
			ids = [str(movie.get('id')), str(movie.get('imdb_id', None))]
			try:
				libmovies = RPC.VideoLibrary.GetMovies(properties=['imdbnumber', 'title', 'year'])['movies']
				libmovies = [i for i in libmovies if str(i['imdbnumber']) in ids or (str(i['year']) == str(movie.get('year', 0)) and equals(movie.get['title'], i['title']))]
				libmovie = libmovies[0]
			except:
				libmovie = []
	else:
		ids = [str(id), 'None']
		try:
			libmovies = RPC.VideoLibrary.GetMovies(properties=['imdbnumber', 'title', 'year'])['movies']
			libmovies = [i for i in libmovies if str(i['imdbnumber']) in ids]
			libmovie = libmovies[0]
		except:
			libmovie = []
	if libmovie != []:
		return
	lib_movies.add_movie_to_library(library_folder, src, id)
	tools.scan_library(path=plugin.get_setting(settings.SETTING_MOVIES_LIBRARY_FOLDER, unicode))

@plugin.route('/movies/add_to_library_parsed/<src>/<id>/<player>')
def movies_add_to_library_parsed(src, id, player):
	from resources.lib.TheMovieDB import Movies
	library_folder = lib_movies.setup_library(plugin.get_setting(settings.SETTING_MOVIES_LIBRARY_FOLDER, unicode))
	date = None
	if src == 'tmdb':
		movie = Movies(id).info()
		date = text.date_to_timestamp(movie.get('release_date'))
		imdb_id = movie.get('imdb_id')
		if imdb_id:
			if imdb_id != None and imdb_id != '':
				src = 'imdb'
				id = imdb_id
	lib_movies.add_movie_to_library(library_folder, src, id, player)
	tools.scan_library(path=plugin.get_setting(settings.SETTING_MOVIES_LIBRARY_FOLDER, unicode))

def movies_add_all_to_library(items, noscan=False):
	library_folder = lib_movies.setup_library(plugin.get_setting(settings.SETTING_MOVIES_LIBRARY_FOLDER, unicode))
	if 'results' in items:
		ids = '\n'.join([str(r['id']) for r in items['results']])
	else:
		ids = '\n'.join([i['movie']['ids']['imdb'] if i['movie']['ids']['imdb'] != None and i['movie']['ids']['imdb'] != '' else str(i['movie']['ids']['tmdb']) for i in items])
	movies_batch_add_file = plugin.get_setting(settings.SETTING_MOVIES_BATCH_ADD_FILE_PATH, unicode)
	if xbmcvfs.exists(movies_batch_add_file):
		batch_add_file = xbmcvfs.File(movies_batch_add_file)
		pre_ids = batch_add_file.read()
		xids = pre_ids.split('\n')
		for id in xids:
			if id != '' and id != None and id not in ids:
				ids = ids + str(id) + '\n'
		batch_add_file.close()
		xbmcvfs.delete(movies_batch_add_file)
	batch_add_file = xbmcvfs.File(movies_batch_add_file, 'w')
	batch_add_file.write(str(ids))
	batch_add_file.close()
	xbmc.executebuiltin('RunPlugin(plugin://plugin.video.openmeta/movies/batch_add_to_library)')

@plugin.route('/movies/batch_add_to_library')
def movies_batch_add_to_library():
	from resources.lib.TheMovieDB import Movies
	movie_batch_file = plugin.get_setting(settings.SETTING_MOVIES_BATCH_ADD_FILE_PATH, unicode)
	if xbmcvfs.exists(movie_batch_file):
		try:
			f = open(xbmc.translatePath(movie_batch_file), 'r')
			r = f.read()
			f.close()
			ids = r.split('\n')
		except:
			title = '%s not found'.replace('%s ','')
			return dialogs.notify(title='Movies', msg=title, delay=2000, image=ICON)
		library_folder = lib_movies.setup_library(plugin.get_setting(settings.SETTING_MOVIES_LIBRARY_FOLDER, unicode))
		for id in ids:
			if ',' in id:
				csvs = id.split(',')
				for csv in csvs:
					if not str(csv).startswith('tt') and csv != '':
						movie = Movies(csv).info()
						csv = movie.get('imdb_id')
					lib_movies.batch_add_movies_to_library(library_folder, csv)
			else:
				if not str(id).startswith('tt') and id != '':
					movie = Movies(id).info()
					id = movie.get('imdb_id')
				lib_movies.batch_add_movies_to_library(library_folder, id)
		os.remove(xbmc.translatePath(movie_batch_file))
		lib_movies.update_library()
		return True

def list_tmdb_movies(result):
	genres_dict = nav_base.get_base_genres()
	movies = [meta_info.get_movie_metadata(item, genres_dict) for item in result['results']]
	items = [make_movie_item(movie) for movie in movies]
	if 'page' in result:
		page = int(result['page'])
		pages = int(result['total_pages'])
		args = nav_base.caller_args()
		if pages > page:
			args['page'] = page + 1
			args['confirm'] = 'yes'
			items.append(
				{
					'label': '%s/%s  [I]Next page[/I]  >>' % (page, pages + 1),
					'icon': nav_base.get_icon_path('item_next'),
					'path': plugin.url_for(nav_base.caller_name(), **args),
					'properties': {'fanart_image': FANART}
				})
	return plugin.finish(items=items, sort_methods=SORT)

def list_tmdb_items(result):
	genres_dict = nav_base.get_base_genres()
	movies = [meta_info.get_movie_metadata(item, None) for item in result['results']]
	items = [make_movie_item(movie) for movie in movies]
	if 'page' in result:
		page = int(result['page'])
		pages = int(result['total_pages'])
		args = nav_base.caller_args()
		if pages > page:
			args['page'] = page + 1
			items.append(
				{
					'label': '%s/%s  [I]Next page[/I]  >>' % (page, pages + 1),
					'icon': nav_base.get_icon_path('item_next'),
					'path': plugin.url_for(nav_base.caller_name(), **args),
					'properties': {'fanart_image': FANART}
				})
	return plugin.finish(items=items, sort_methods=SORT)

def list_trakt_persons(results):
	genres_dict = dict([(x['slug'], x['name']) for x in Trakt.trakt_get_genres('movies')])
	movies = [meta_info.get_trakt_movie_metadata(item['movie'], genres_dict) for item in results]
	items = [make_movie_item(movie) for movie in movies]
	return plugin.finish(items=items)

def list_trakt_search_items(results, pages, page):
	movies = [meta_info.get_trakt_movie_metadata(item['movie'], None) for item in results]
	items = [make_movie_item(movie) for movie in movies]
	page = int(page)
	pages = int(pages)
	if pages > 1:
		args = nav_base.caller_args()
		args['page'] = page + 1
		items.append(
			{
				'label': '%s/%s  [I]Next page[/I]  >>' % (page, pages + 1),
				'icon': nav_base.get_icon_path('item_next'),
				'path': plugin.url_for(nav_base.caller_name(), **args),
				'properties': {'fanart_image': FANART}
			})
	return plugin.finish(items=items)

def list_trakt_movies(results, pages, page):
	genres_dict = dict([(x['slug'], x['name']) for x in Trakt.trakt_get_genres('movies')])
	movies = [meta_info.get_trakt_movie_metadata(item['movie'], genres_dict) for item in results]
	items = [make_movie_item(movie) for movie in movies]
	page = int(page)
	pages = int(pages)
	if pages > 1:
		args = nav_base.caller_args()
		args['page'] = page + 1
		args['confirm'] = 'yes'
		items.append(
			{
				'label': '%s/%s  [I]Next page[/I]  >>' % (page, pages + 1),
				'icon': nav_base.get_icon_path('item_next'),
				'path': plugin.url_for(nav_base.caller_name(), **args),
				'properties': {'fanart_image': FANART}
			})
	return plugin.finish(items=items, sort_methods=SORTRAKT)

@plugin.route('/movies/play/<src>/<id>')
def movies_play(src, id):
	from resources.lib.TheMovieDB import Find
	tmdb_id = None
	if src == 'tmdb':
		tmdb_id = id
	elif src == 'imdb':
		info = Find(id).info(external_source='imdb_id')
		try:
			tmdb_id = info['movie_results'][0]['id']
		except (KeyError, TypeError):
			pass
	if tmdb_id:
		play_movies.play_movie(tmdb_id)
	else:
		plugin.set_resolved_url(handle=int(sys.argv[1]))

@plugin.route('/movies/play_by_name/<name>/<lang>')
def movies_play_by_name(name, lang='en'):
	from resources.lib.TheMovieDB import Search
	items = Search().movie(query=name, language=lang, page=1)['results']
	if not items:
		header = 'Movie not found'
		return dialogs.ok(header, 'No movie information found on TMDB for %s' % name)
	if len(items) > 1:
		selection = dialogs.select(('movie'), ['%s (%s)' % ((s['title']), text.parse_year(s['release_date'])) for s in items])
	else:
		selection = 0
	if selection != -1:
		id = items[selection]['id']
		movies_play('tmdb', id)

def trakt_movies_play_random(movies, convert_list=False):
	for movie in movies:
		movie['type'] = 'movie'
		if convert_list:
			movie['movie'] = movie
	playrandom.trakt_play_random(movies)

def tmdb_movies_play_random(list):
	movies = list['results']
	for movie in movies:
		movie['type'] = 'movie'
	playrandom.tmdb_play_random(movies)

def make_movie_item(movie_info):
	try:
		tmdb_id = movie_info.get('tmdb')
	except:
		tmdb_id = ''
	if tmdb_id == '': 
		try:
			tmdb_id = info['tmdb']
		except:
			tmdb_id = False
	try:
		imdb_id = movie_info.get('imdb')
	except:
		imdb_id = ''
	if imdb_id == '':
		try:
			imdb_id = info['imdb']
		except:
			imdb_id = False
	if tmdb_id:
		id = tmdb_id 
		src = 'tmdb'
	elif imdb_id:
		id = imdb_id 
		src = 'imdb'
	else:
		title = '%s not found'.replace('%s ','')
		dialogs.notify(msg='tmdb or imdb id', title=title, delay=2000, image=nav_base.get_icon_path('movies'))
	if xbmc.getCondVisibility('system.hasaddon(script.extendedinfo)'):
		context_menu = [
			('OpenInfo', 'RunScript(script.extendedinfo,info=extendedinfo,id=%s)' % id),
			('Movie trailer', 'RunScript(script.extendedinfo,info=playtrailer,id=%s)' % id),
			('Add to library','RunPlugin(%s)' % plugin.url_for('movies_add_to_library', src=src, id=id))]
	else:
		context_menu = [
			('Add to library','RunPlugin(%s)' % plugin.url_for('movies_add_to_library', src=src, id=id))]
	return {
		'label': movie_info['title'],
		'path': plugin.url_for('movies_play', src=src, id=id),
		'context_menu': context_menu,
		'thumbnail': movie_info['poster'],
		'icon': movie_info['poster'],
		'banner': movie_info['fanart'],
		'poster': movie_info['poster'],
		'properties': {'fanart_image': movie_info['fanart']},
		'is_playable': True,
		'info_type': 'video',
		'stream_info': {'video': {}},
		'info': movie_info
		}