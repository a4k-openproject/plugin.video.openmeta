import os, time
import xbmc, xbmcvfs, xbmcplugin
from resources.lib import text
from resources.lib import Trakt
from resources.lib import tools
from resources.lib import dialogs
from resources.lib import executor
from resources.lib import settings
from resources.lib import nav_base
from resources.lib import meta_info
from resources.lib import properties
from resources.lib import lib_tvshows
from resources.lib import play_tvshows
from resources.lib.TheTVDB import TVDB
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
	xbmcplugin.SORT_METHOD_DURATION,
	xbmcplugin.SORT_METHOD_MPAA_RATING]

@plugin.route('/tv')
def tv():
	items = [
		{
			'label': 'Genres (TMDb)',
			'path': plugin.url_for('tmdb_tv_genres'),
			'icon': nav_base.get_icon_path('genres'),
			'thumbnail': nav_base.get_icon_path('genres')
		},
		{
			'label': 'On the air (TMDb)',
			'path': plugin.url_for('tmdb_tv_now_playing', page=1),
			'icon': nav_base.get_icon_path('ontheair'),
			'thumbnail': nav_base.get_icon_path('ontheair')
		},
		{
			'label': 'Popular (TMDb)',
			'path': plugin.url_for('tmdb_tv_most_popular', page=1),
			'icon': nav_base.get_icon_path('popular'),
			'thumbnail': nav_base.get_icon_path('popular')
		},
		{
			'label': 'Top rated (TMDb)',
			'path': plugin.url_for('tmdb_tv_top_rated', page=1),
			'icon': nav_base.get_icon_path('top_rated'),
			'thumbnail': nav_base.get_icon_path('top_rated')
		},
		{
			'label': 'Most watched (Trakt)',
			'path': plugin.url_for('trakt_tv_watched', page=1),
			'icon': nav_base.get_icon_path('traktwatchlist'),
			'thumbnail': nav_base.get_icon_path('traktwatchlist')
		},
		{
			'label': 'Most collected (Trakt)',
			'path': plugin.url_for('trakt_tv_collected', page=1),
			'icon': nav_base.get_icon_path('traktcollection'),
			'thumbnail': nav_base.get_icon_path('traktcollection')
		},
		{
			'label': 'Most collected Netflix (Trakt)',
			'path': plugin.url_for('trakt_netflix_tv_collected', page=1),
			'icon': nav_base.get_icon_path('traktcollection'),
			'thumbnail': nav_base.get_icon_path('traktcollection')
		},
		{
			'label': 'Popular (Trakt)',
			'path': plugin.url_for('tv_trakt_popular', page=1),
			'icon': nav_base.get_icon_path('traktrecommendations'),
			'thumbnail': nav_base.get_icon_path('traktrecommendations')
		},
		{
			'label': 'Trending (Trakt)',
			'path': plugin.url_for('trakt_tv_trending', page=1),
			'icon': nav_base.get_icon_path('trending'),
			'thumbnail': nav_base.get_icon_path('trending')
		},
		{
			'label': 'Search tv shows',
			'path': plugin.url_for('tv_search'),
			'icon': nav_base.get_icon_path('search'),
			'thumbnail': nav_base.get_icon_path('search')
		}]
	for item in items:
		item['properties'] = {'fanart_image': FANART}
	return items

@plugin.route('/tv/trakt/search')
def trakt_tv_search():
	term = plugin.keyboard(heading='Enter search string')
	if term != None and term != '':
		return trakt_tv_search_term(term, 1)
	else:
		return

@plugin.route('/tv/trakt/search_term/<term>/<page>')
def trakt_tv_search_term(term, page):
	results, pages = Trakt.search_for_tvshow_paginated(term, page)
	return list_trakt_search_items(results, pages, page)

def list_trakt_search_items(results, pages, page):
	plugin.set_content('tvshows')
	shows = [meta_info.get_tvshow_metadata_trakt(item['show'], None) for item in results]
	items = [make_tvshow_item(show) for show in shows if show.get('tvdb_id')]
	page = int(page)
	pages = int(pages)
	if pages > 1:
		args = nav_base.caller_args()
		nextpage = page + 1
		args['page'] = page + 1
		items.append(
			{
				'label': '%s/%s  [I]Next page[/I]  >>' % (nextpage, pages),
				'icon': nav_base.get_icon_path('item_next'),
				'path': plugin.url_for(nav_base.caller_name(), **args),
				'properties': {'fanart_image': FANART}
			})
	return plugin.finish(items=items)

def list_trakt_tvshows(results, pages, page):
	plugin.set_content('tvshows')
	genres_dict = trakt_get_genres()
	shows = [meta_info.get_tvshow_metadata_trakt(item['show'], genres_dict) for item in results]
	items = [make_tvshow_item(show) for show in shows if show.get('tvdb_id')]
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
	return plugin.finish(items=items, sort_methods=SORT)

@plugin.route('/tv/trakt/watched/<page>')
def trakt_tv_watched(page, raw=False):
	results, total_items = Trakt.trakt_get_watched_shows_paginated(page)
	if raw:
		return results
	else:
		return list_trakt_tvshows_watched_paginated(results, total_items, page)

def list_trakt_tvshows_watched_paginated(results, total_items, page):
	plugin.set_content('tvshows')
	genres_dict = trakt_get_genres()
	shows = [meta_info.get_tvshow_metadata_trakt(item['show'], genres_dict) for item in results]
	items = [make_tvshow_item(show) for show in shows if show.get('tvdb_id')]
	nextpage = int(page) + 1
	pages = int(total_items) // 99 + (int(total_items) % 99 > 0)
	if int(pages) > int(page):
		items.append(
			{
				'label': '%s/%s  [I]Next page[/I]  >>' % (nextpage, pages),
				'icon': nav_base.get_icon_path('item_next'),
				'path': plugin.url_for('trakt_tv_watched', page=int(page) + 1),
				'properties': {'fanart_image': FANART}
			})
	return plugin.finish(items=items, sort_methods=SORT)

@plugin.route('/tv/trakt/netflix_collected/<page>')
def trakt_netflix_tv_collected(page, raw=False):
	results, pages = Trakt.trakt_get_netflix_collected_shows(page)
	if raw:
		return results
	else:
		return list_trakt_tvshows(results, pages, page)

@plugin.route('/tv/trakt/collected/<page>')
def trakt_tv_collected(page, raw=False):
	results, total_items = Trakt.trakt_get_collected_shows_paginated(page)
	if raw:
		return results
	else:
		return list_trakt_tvshows_collected_paginated(results, total_items, page)

def list_trakt_tvshows_collected_paginated(results, total_items, page):
	plugin.set_content('tvshows')
	genres_dict = trakt_get_genres()
	shows = [meta_info.get_tvshow_metadata_trakt(item['show'], genres_dict) for item in results]
	items = [make_tvshow_item(show) for show in shows if show.get('tvdb_id')]
	nextpage = int(page) + 1
	pages = int(total_items) // 99 + (int(total_items) % 99 > 0)
	if int(pages) > int(page):
		items.append(
			{
				'label': '%s/%s  [I]Next page[/I]  >>' % (nextpage, pages),
				'icon': nav_base.get_icon_path('item_next'),
				'path': plugin.url_for('trakt_tv_collected', page=int(page) + 1),
				'properties': {'fanart_image': FANART}
			})
	return plugin.finish(items=items, sort_methods=SORT)

@plugin.route('/tv/trakt/popular/<page>')
def tv_trakt_popular(page, raw=False):
	results, pages = Trakt.trakt_get_popular_shows_paginated(page)
	if raw:
		return results
	else:
		return list_trakt_tvshows_popular_paginated(results, pages, page)

def list_trakt_tvshows_popular_paginated(results, pages, page):
	plugin.set_content('tvshows')
	genres_dict = trakt_get_genres()
	shows = [meta_info.get_tvshow_metadata_trakt(item, genres_dict) for item in results]
	items = [make_tvshow_item(show) for show in shows if show.get('tvdb_id')]
	nextpage = int(page) + 1
	if pages > page:
		items.append(
			{
				'label': '%s/%s  [I]Next page[/I]  >>' % (nextpage, pages),
				'icon': nav_base.get_icon_path('item_next'),
				'path': plugin.url_for('tv_trakt_popular', page=int(page) + 1),
				'properties': {'fanart_image': FANART}
			})
	return plugin.finish(items=items, sort_methods=SORT)

@plugin.route('/tv/trakt/trending/<page>')
def trakt_tv_trending(page, raw=False):
	results, pages = Trakt.trakt_get_trending_shows_paginated(page)
	if raw:
		return results
	else:
		list_trakt_tvshows_trending_paginated(results, pages, page)

def list_trakt_tvshows_trending_paginated(results, pages, page):
	plugin.set_content('tvshows')
	genres_dict = trakt_get_genres()
	shows = [meta_info.get_tvshow_metadata_trakt(item['show'], genres_dict) for item in results]
	items = [make_tvshow_item(show) for show in shows if show.get('tvdb_id')]
	nextpage = int(page) + 1
	if pages > page:
		items.append(
			{
				'label': '%s/%s  [I]Next page[/I]  >>' % (nextpage, pages),
				'icon': nav_base.get_icon_path('item_next'),
				'path': plugin.url_for('trakt_tv_trending', page=int(page) + 1),
				'properties': {'fanart_image': FANART}
			})
	return plugin.finish(items=items, sort_methods=SORT)

@plugin.route('/tv/search')
def tv_search():
	term = plugin.keyboard(heading='Enter search string')
	if term != None and term != '':
		return tv_search_term(term, 1)
	else:
		return

@plugin.route('/tv/search/edit/<term>')
def tv_search_edit(term):
	term = plugin.keyboard(default=term, heading='Enter search string')
	if term != None and term != '':
		return tv_search_term(term, 1)
	else:
		return

@plugin.route('/tv/search_term/<term>/<page>')
def tv_search_term(term, page):
	items = [
		{
			'label': '(TMDb) Search - %s' % term,
			'path': plugin.url_for('tmdb_tv_search_term', term=term, page=1),
			'icon': nav_base.get_icon_path('tv'),
			'thumbnail': nav_base.get_icon_path('tv')},
		{
			'label': '(TVDb) Search - %s' % term,
			'path': plugin.url_for('tvdb_tv_search_term', term=term, page=1),
			'icon': nav_base.get_icon_path('tv'),
			'thumbnail': nav_base.get_icon_path('tv')},
		{
			'label': '(Trakt) Search - %s' % term,
			'path': plugin.url_for('trakt_tv_search_term', term=term, page=1),
			'icon': nav_base.get_icon_path('tv'),
			'thumbnail': nav_base.get_icon_path('tv')},
		{
			'label': 'Edit search string',
			'path': plugin.url_for('tv_search_edit', term=term),
			'icon': nav_base.get_icon_path('search'),
			'thumbnail': nav_base.get_icon_path('search')
		}]
	for item in items:
		item['properties'] = {'fanart_image': FANART}
	return items

@plugin.route('/tv/tmdb/search')
def tmdb_tv_search():
	term = plugin.keyboard(heading='Enter search string')
	if term != None and term != '':
		return tmdb_tv_search_term(term, 1)
	else:
		return

@plugin.route('/tv/tmdb/search_term/<term>/<page>')
def tmdb_tv_search_term(term, page):
	plugin.set_content('tvshows')
	from resources.lib.TheMovieDB import Search
	result = Search().tv(query=term, language='en', page=page)
	items = list_tvshows(result)
	return plugin.finish(items=items, sort_methods=SORT)

@plugin.cached_route('/tv/tmdb/genres', TTL=60)
def tmdb_tv_genres():
	plugin.set_content('genres')
	genres = nav_base.get_tv_genres()
	items = sorted([
		{
			'label': name,
			'icon': nav_base.get_genre_icon(id),
			'path': plugin.url_for('tmdb_tv_genre', id=id, page=1)
		} for id, name in genres.items()], key=lambda k: k['label'])
	for item in items:
		item['properties'] = {'fanart_image': FANART}
	return items

@plugin.cached_route('/tv/genre/<id>/<page>', TTL=60)
def tmdb_tv_genre(id, page, raw=False):
	plugin.set_content('tvshows')
	from resources.lib.TheMovieDB import Discover
	result = Discover().tv(with_genres=id, page=page, language='en')
	if raw:
		return result
	else:
		return list_tvshows(result)

@plugin.cached_route('/tv/tmdb/now_playing/<page>', TTL=60)
def tmdb_tv_now_playing(page, raw=False):
	plugin.set_content('tvshows')
	from resources.lib.TheMovieDB import TV
	result = TV().on_the_air(page=page, language='en')
	if raw:
		return result
	else:
		return list_tvshows(result)

@plugin.cached_route('/tv/tmdb/most_popular/<page>', TTL=60)
def tmdb_tv_most_popular(page, raw=False):
	plugin.set_content('tvshows')
	from resources.lib.TheMovieDB import TV
	result = TV().popular(page=page, language='en')
	if raw:
		return result
	else:
		return list_tvshows(result)

@plugin.cached_route('/tv/tmdb/top_rated/<page>', TTL=60)
def tmdb_tv_top_rated(page, raw=False):
	plugin.set_content('tvshows')
	from resources.lib.TheMovieDB import TV
	result = TV().top_rated(page=page, language='en')
	if raw:
		return result
	else:
		return list_tvshows(result)

@plugin.route('/tv/tvdb/search')
def tvdb_tv_search():
	term = plugin.keyboard(heading='Enter search string')
	if term != None and term != '':
		return tvdb_tv_search_term(term, 1)
	else:
		return

@plugin.route('/tv/tvdb/search_term/<term>/<page>')
def tvdb_tv_search_term(term, page):
	plugin.set_content('tvshows')
	search_results = TVDB.search(term, language='en')
	items = []
	load_full_tvshow = lambda tvshow : TVDB.get_show(tvshow['id'], full=True)
	for tvdb_show in executor.execute(load_full_tvshow, search_results, workers=10):
		info = build_tvshow_info(tvdb_show)
		items.append(make_tvshow_item(info))
	return items

def get_tvdb_id_from_name(name, lang):
	search_results = TVDB.search(name, language=lang)
	if not search_results:
		header = 'TV show not found'
		dialogs.ok(header, 'no show information found for %s in tvdb' % text.to_utf8(name))
		return
	items = []
	for show in search_results:
		if 'firstaired' in show:
			show['year'] = int(show['firstaired'].split('-')[0].strip())
		else:
			show['year'] = 'unknown'
		items.append(show)
	if len(items) > 1:
		selection = dialogs.select('Choose TV Show', ['%s (%s)' % (text.to_utf8(s['seriesname']), s['year']) for s in items])
	else:
		selection = 0
	if selection != -1:
		return items[selection]['id']

def get_tvdb_id_from_imdb_id(imdb_id):
	tvdb_id = TVDB.search_by_imdb(imdb_id)
	if not tvdb_id:
		header = 'TV show not found'
		dialogs.ok(header, 'no show information found for %s in tvdb' % imdb_id)
		return
	return tvdb_id

@plugin.route('/tv/trakt/updated/<page>')
def tv_trakt_updated(page):
	results, pages = Trakt.trakt_updated_shows(page)
	return list_trakt_tvshows_trending_paginated(results, pages, page)

def list_trakt_tvshows_updated_paginated(results, pages, page):
	plugin.set_content('tvshows')
	genres_dict = trakt_get_genres()
	shows = [meta_info.get_tvshow_metadata_trakt(item['show'], genres_dict) for item in results]
	items = [make_tvshow_item(show) for show in shows if show.get('tvdb_id')]
	nextpage = int(page) + 1
	if pages > page:
		items.append(
			{
				'label': '%s/%s  [I]Next page[/I]  >>' % (nextpage, pages),
				'icon': nav_base.get_icon_path('item_next'),
				'path': plugin.url_for('tv_trakt_updated', page=int(page) + 1),
				'properties': {'fanart_image': FANART}
			})
	return items

@plugin.route('/tv/play/<id>/<season>/<episode>')
def tv_play(id, season, episode):
	play_tvshows.play_episode(id, season, episode)

@plugin.route('/tv/play_by_name/<name>/<season>/<episode>/<lang>', options={'lang': 'en'})
def tv_play_by_name(name, season, episode, lang):
	tvdb_id = get_tvdb_id_from_name(name, lang)
	if tvdb_id: tv_play(tvdb_id, season, episode)

@plugin.route('/tv/tvdb/<id>/')
def tv_tvshow(id):
	plugin.set_content('seasons')
	return plugin.finish(items=list_seasons_tvdb(id), sort_methods=SORT)


@plugin.route('/tv/tvdb/<id>/<season_num>/')
def tv_season(id, season_num):
	plugin.set_content('episodes')
	return plugin.finish(items=list_episodes_tvdb(id, season_num), sort_methods=SORT)

@plugin.route('/tv/add_to_library_parsed/<id>/<player>')
def tv_add_to_library_parsed(id, player):
	if id.startswith('tt'):
		try:
			id = TVDB.search_by_imdb(id)
		except:
			header = 'TV show not found'
			return dialogs.ok(header, 'no show information found for %s in TheTVDb' % id)
	library_folder = lib_tvshows.setup_library(plugin.get_setting(settings.SETTING_TV_LIBRARY_FOLDER, unicode))
	show = TVDB[int(id)]
	imdb = show['imdb_id']
	library_folder = lib_tvshows.setup_library(plugin.get_setting(settings.SETTING_TV_LIBRARY_FOLDER, unicode))
	if lib_tvshows.add_tvshow_to_library(library_folder, show, player):
		properties.set_property('clean_library', 1)
	tools.scan_library(path=plugin.get_setting(settings.SETTING_TV_LIBRARY_FOLDER, unicode))

@plugin.route('/tv/add_to_library/<id>')
def tv_add_to_library(id):
	library_folder = lib_tvshows.setup_library(plugin.get_setting(settings.SETTING_TV_LIBRARY_FOLDER, unicode))
	show = TVDB[int(id)]
	imdb = show['imdb_id']
	library_folder = lib_tvshows.setup_library(plugin.get_setting(settings.SETTING_TV_LIBRARY_FOLDER, unicode))
	if lib_tvshows.add_tvshow_to_library(library_folder, show):
		properties.set_property('clean_library', 1)
	tools.scan_library(path=plugin.get_setting(settings.SETTING_TV_LIBRARY_FOLDER, unicode))

def tv_add_all_to_library(items, noscan=False):
	library_folder = lib_tvshows.setup_library(plugin.get_setting(settings.SETTING_TV_LIBRARY_FOLDER, unicode))
	ids = ''
	if 'results' in items:
		preids = []
		for tvdb_show, tmdb_show in executor.execute(tmdb_to_tvdb, items['results'], workers=10):
			if tvdb_show is not None:
				preids.append(tvdb_show['id'])
		ids = '\n'.join(preids)
	else:
		ids = '\n'.join([str(i['show']['ids']['tvdb']) if i['show']['ids']['tvdb'] != None and i['show']['ids']['tvdb'] != '' else i['show']['ids']['imdb'] for i in items])
	shows_batch_add_file = plugin.get_setting(settings.SETTING_TV_BATCH_ADD_FILE_PATH, unicode)
	if xbmcvfs.exists(shows_batch_add_file):
		batch_add_file = xbmcvfs.File(shows_batch_add_file)
		pre_ids = batch_add_file.read()
		xids = pre_ids.split('\n')
		for id in xids:
			if id != '' and id != None and id not in ids:
				ids = ids + str(id) + '\n'
		batch_add_file.close()
		xbmcvfs.delete(shows_batch_add_file)
	batch_add_file = xbmcvfs.File(shows_batch_add_file, 'w')
	batch_add_file.write(str(ids))
	batch_add_file.close()
	xbmc.executebuiltin('RunPlugin(plugin://plugin.video.openmeta/tv/batch_add_to_library)')

@plugin.route('/tv/batch_add_to_library')
def tv_batch_add_to_library():
	tv_batch_file = plugin.get_setting(settings.SETTING_TV_BATCH_ADD_FILE_PATH, unicode)
	if xbmcvfs.exists(tv_batch_file):
		try:
			f = open(xbmc.translatePath(tv_batch_file), 'r')
			r = f.read()
			f.close()
			ids = r.split('\n')
		except:
			title = '%s not found'.replace('%s ','')
			return dialogs.notify(title='TV shows', msg=title, delay=2000, image=ICON)
		library_folder = lib_tvshows.setup_library(plugin.get_setting(settings.SETTING_TV_LIBRARY_FOLDER, unicode))
		ids_index = 0
		for id in ids:
			if id == None or id == 'None':
				pass
			elif ',' in id:
				csvs = id.split(',')
				for csv in csvs:
					if csv == None or csv == 'None':
						pass
					elif str(csv).startswith('tt') and csv != '':
						tvdb_id = get_tvdb_id_from_imdb_id(csv)
					else:
						tvdb_id = csv
					show = TVDB[int(tvdb_id)]
					lib_tvshows.batch_add_tvshows_to_library(library_folder, show)
			else:
				if id == None or id == 'None' or id == '':
					pass
				elif str(id).startswith('tt'):
					tvdb_id = get_tvdb_id_from_imdb_id(id)
				else:
					tvdb_id = id
				try:
					show = TVDB[int(tvdb_id)]
					lib_tvshows.batch_add_tvshows_to_library(library_folder, show)
				except:
					dialogs.notify(title='Failed to add', msg='%s' % id, delay=2000, image=ICON)
			ids_index += 1
		os.remove(xbmc.translatePath(tv_batch_file))
		lib_tvshows.update_library()
		return True

def list_tvshows(response):
	items = []
	results = response['results']
	for tvdb_show, tmdb_show in executor.execute(tmdb_to_tvdb, results, workers=10):
		if tvdb_show is not None:
			info = build_tvshow_info(tvdb_show, tmdb_show)
			items.append(make_tvshow_item(info))
	if xbmc.abortRequested:
		return
	if 'page' in response:
		page = response['page']
		args = nav_base.caller_args()
		if page < response['total_pages']:
			args['page'] = str(page + 1)
			items.append(
				{
					'label': '%s/%s  [I]Next page[/I]  >>' % (page + 1, response['total_pages']),
					'icon': nav_base.get_icon_path('item_next'),
					'path': plugin.url_for(nav_base.caller_name(), **args),
					'properties': {'fanart_image': FANART}
				})
	return items

def trakt_get_genres():
	genres_dict = dict([(x['slug'], x['name']) for x in Trakt.trakt_get_genres('movies')])
	genres_dict.update(dict([(x['slug'], x['name']) for x in Trakt.trakt_get_genres('shows')]))
	return genres_dict

def list_trakt_episodes(result, with_time=False):
	genres_dict = trakt_get_genres()
	items = []
	for item in result:
		if 'episode' in item:
			episode = item['episode']
		else:
			episode = item
		if 'show' in item:
			show = item['show']
		try:
			id = episode['show']['ids']['tvdb']
		except:
			id = episode['ids'].get('tvdb')
		if not id:
			continue
		try:
			season_num = episode['season']
		except:
			season_num = episode.get('season')
		try:
			episode_num = episode['number']
		except:
			episode_num = episode.get('number')
		if show:
			tvshow_title = show.get('title').encode('utf-8')
		else:
			try:
				tvshow_title = (episode['show']['title']).encode('utf-8')
			except:
				tvshow_title = str(episode.get('title')).encode('utf-8')
		if episode['title'] != None:
			try:
				episode_title = episode['title'].encode('utf-8')
			except:
				episode_title = episode.get('title').encode('utf-8')
		else:
			episode_title = 'TBA'
		info = meta_info.get_tvshow_metadata_trakt(item['show'], genres_dict)
		info['season'] = episode['season'] 
		info['episode'] = episode['number']
		info['title'] = episode['title']
		info['aired'] = episode.get('first_aired','')
		info['premiered'] = episode.get('first_aired','')
		info['rating'] = episode.get('rating', '')
		info['plot'] = episode.get('overview','')
		info['tagline'] = episode.get('tagline')
		info['votes'] = episode.get('votes','')
		label = '%s - S%02dE%02d - %s' % (tvshow_title, season_num, episode_num, episode_title)
		if with_time and info['premiered']:
			airtime = time.strptime(item['first_aired'], '%Y-%m-%dt%H:%M:%S.000Z')
			airtime = time.strftime('%Y-%m-%d %H:%M', airtime)
			label = '%s - S%02dE%02d - %s' % (tvshow_title, season_num, episode_num, episode_title)
		if xbmc.getCondVisibility('system.hasaddon(script.extendedinfo)'):
			context_menu = [
				('OpenInfo', 'RunScript(script.extendedinfo,info=extendedepisodeinfo,tvshow=%s,season=%s,episode=%s)' % (tvshow_title, season_num, episode_num))]
		else:
			context_menu = []
		items.append(
			{
				'label': label,   ####### TODO NOT WORKING AS INTENDED, ONLY PICKS UP "episode['title']"  #######
				'path': plugin.url_for('tv_play', id=id, season=season_num, episode=episode_num),
				'context_menu': context_menu,
				'info': info,
				'is_playable': True,
				'info_type': 'video',
				'stream_info': {'video': {}},
				'thumbnail': info['poster'],
				'poster': info['poster'],
				'icon': 'DefaultVideo.png',
				'properties': {'fanart_image': info['fanart']}
			})
	return plugin.finish(items=items, sort_methods=SORTRAKT, cache_to_disc=False, update_listing=True)

def build_tvshow_info(tvdb_show, tmdb_show=None):
	tvdb_info = meta_info.get_tvshow_metadata_tvdb(tvdb_show)
	tmdb_info = meta_info.get_tvshow_metadata_tmdb(tmdb_show)
	info = {}
	info.update(tvdb_info)
	info.update(dict((k,v) for k,v in tmdb_info.iteritems() if v))
	return info

def make_tvshow_item(info):
	from resources.lib.TheMovieDB import TV, Find
	try:
		tvdb_id = info['tvdb']
	except:
		tvdb_id = ''
	if tvdb_id == '': 
		try:
			tvdb_id = info['tvdb_id']
		except:
			tvdb_id = ''
	try:
		tmdb_id = info['tmdb']
	except:
		tmdb_id = ''
	if tmdb_id == '': 
		try:
			tmdb_id = info['id']
		except:
			tmdb_id = ''
	try:
		imdb_id = info['imdb_id']
	except:
		imdb_id = ''
	if imdb_id == '': 
		try:
			imdb_id = info['imdb']
		except:
			imdb_id = ''
	if not info['poster']:
		info['poster'] = None
	if not info['fanart']:
		info['fanart'] = None
	if info['poster'] == None or info['poster'] == '':
		if tmdb_id != None and tmdb_id != '':
			show = TV(tmdb_id).info()
			if show['poster_path'] != None and show['poster_path'] != '':
				info['poster'] = u'https://image.tmdb.org/t/p/w500%s' % show['poster_path']
			if info['fanart'] == None or info['fanart'] == '':
				if show['backdrop_path'] != None and show['backdrop_path'] != '':
					info['fanart'] = u'https://image.tmdb.org/t/p/original%s' % show['backdrop_path']
	if info['poster'] == None or info['poster'] == '':
		if tvdb_id != None and tvdb_id != '':
			show = TVDB.get_show(int(tvdb_id), full=False)
			if show != None:
				if show['seriesname'] != None and show['seriesname'] != '':
					if show.get('poster', '') != None and show.get('poster', '') != '':
						info['poster'] = show.get('poster', '')
					if info['fanart'] == None or info['fanart'] == '':
						if show.get('fanart', '') != None and show.get('fanart', '') != '':
							info['fanart'] = show.get('fanart', '')
	if info['poster'] == None or info['poster'] == '':
		if imdb_id != None and imdb_id != '':
			preshow = Find(imdb_id).info(external_source='imdb_id')
			proshow = preshow['tv_results']
			if proshow != []:
				show = proshow[0]
			else:
				show = []
			if show != []:
				if show['poster_path'] != None and show['poster_path'] != '':
					info['poster'] = u'https://image.tmdb.org/t/p/w500%s' % show['poster_path']
				if info['fanart'] == None or info['fanart'] == '':
					if show['backdrop_path'] != None and show['backdrop_path'] != '':
						info['fanart'] = u'https://image.tmdb.org/t/p/original%s' % show['backdrop_path']
	if info['fanart'] == None or info['fanart'] == '':
		info['fanart'] = FANART
	if xbmc.getCondVisibility('system.hasaddon(script.extendedinfo)'):
		context_menu = [
			('OpenInfo', 'RunScript(script.extendedinfo,info=extendedtvinfo,tvdb_id=%s)' % tvdb_id),
			('TV trailer', 'RunScript(script.extendedinfo,info=playtvtrailer,tvdb_id=%s)' % tvdb_id),
			('Add to library', 'RunPlugin(%s)' % plugin.url_for('tv_add_to_library', id=tvdb_id))]
	else:
		context_menu = [
			('Add to library', 'RunPlugin(%s)' % plugin.url_for('tv_add_to_library', id=tvdb_id))]
	return {
		'label': text.to_utf8(info['title']),
		'path': plugin.url_for('tv_tvshow', id=tvdb_id),
		'context_menu': context_menu,
		'thumbnail': info['poster'],
		'icon': 'DefaultVideo.png',
		'poster': info['poster'],
		'properties': {'fanart_image': info['fanart']},
		'info_type': 'video',
		'stream_info': {'video': {}},
		'info': info
		}

@plugin.cached(TTL=60)
def list_seasons_tvdb(id):
	id = int(id)
	show = TVDB[id]
	show_info = meta_info.get_tvshow_metadata_tvdb(show, banners=False)
	title = show_info['name']
	items = []
	for (season_num, season) in show.items():
		if season_num == 0 and not False:
			continue
		elif not season.has_aired(flexible=False):
			continue
		season_info = meta_info.get_season_metadata_tvdb(show_info, season)
		if xbmc.getCondVisibility('system.hasaddon(script.extendedinfo)'):
			context_menu = [
				('OpenInfo', 'RunScript(script.extendedinfo,info=seasoninfo,tvshow=%s,season=%s)' % (title, season_num))]
		else:
			context_menu = []
		items.append(
			{
				'label': u'Season %s' % season_num,
				'path': plugin.url_for('tv_season', id=id, season_num=season_num),
				'context_menu': context_menu,
				'info': season_info,
				'thumbnail': season_info['poster'],
				'icon': 'DefaultVideo.png',
				'poster': season_info['poster'],
				'properties': {'fanart_image': season_info['fanart']}
			})
	return items

@plugin.cached(TTL=60)
def list_episodes_tvdb(id, season_num):
	id = int(id)
	season_num = int(season_num)
	show = TVDB[id]
	show_info = meta_info.get_tvshow_metadata_tvdb(show, banners=False)
	title = show_info['name']
	season = show[season_num]
	season_info = meta_info.get_season_metadata_tvdb(show_info, season, banners=True)
	items = []
	for (episode_num, episode) in season.items():
		if not season_num == 0 and not episode.has_aired(flexible=False):
			break
		episode_info = meta_info.get_episode_metadata_tvdb(season_info, episode)
		if xbmc.getCondVisibility('system.hasaddon(script.extendedinfo)'):
			context_menu = [
				('OpenInfo', 'RunScript(script.extendedinfo,info=extendedepisodeinfo,tvshow=%s,season=%s,episode=%s)' % (title, season_num, episode_num))]
		else:
			context_menu = []
		items.append(
			{
				'label': episode_info['title'],
				'path': plugin.url_for('tv_play', id=id, season=season_num, episode=episode_num),
				'context_menu': context_menu,
				'info': episode_info,
				'is_playable': True,
				'info_type': 'video',
				'stream_info': {'video': {}},
				'thumbnail': episode_info['poster'],
				'poster': season_info['poster'],
				'icon': 'DefaultVideo.png',
				'properties': {'fanart_image': episode_info['fanart']}
			})
	return items

def tmdb_to_tvdb(tmdb_show):
	from resources.lib.TheMovieDB import TV
	tvdb_show = None
	name = tmdb_show['original_name']
	try:
		year = int(text.parse_year(tmdb_show['first_air_date']))
	except:
		year = ''
	results = [x['id'] for x in TVDB.search(name, year)]
	if len(results) != 1:
		id = TV(tmdb_show['id']).external_ids().get('tvdb_id', None)
		if id:
			results = [id]
	if results:
		tvdb_show = TVDB[results[0]]
	return tvdb_show, tmdb_show