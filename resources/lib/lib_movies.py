import os, json, urllib
import xbmc, xbmcvfs
from resources.lib import tools
from resources.lib import dialogs
from resources.lib import nav_base
from resources.lib.xswift2 import plugin
from resources.lib.settings import SETTING_MOVIES_LIBRARY_FOLDER

@plugin.cached(TTL=60*2)
def query_movies_server(url):
	response = urllib.urlopen(url)
	return json.loads(response.read())

def update_library():
	library_folder = plugin.get_setting(SETTING_MOVIES_LIBRARY_FOLDER, unicode)
	if not xbmcvfs.exists(library_folder):
		return
	tools.scan_library(path=plugin.get_setting(SETTING_MOVIES_LIBRARY_FOLDER, unicode))

def sync_trakt_collection():
	from resources.lib import lists
	lists.lists_trakt_movies_collection_to_library()

def add_movie_to_library(library_folder, src, id):
	changed = False
	movie_folder = os.path.join(library_folder, str(id) + '/')
	if not xbmcvfs.exists(movie_folder):
		try:
			xbmcvfs.mkdir(movie_folder)
		except:
			pass
	nfo_filepath = os.path.join(movie_folder, str(id) + '.nfo')
	if not xbmcvfs.exists(nfo_filepath):
		changed = True
		nfo_file = xbmcvfs.File(nfo_filepath, 'w')
		if src == 'imdb':
			content = 'https://www.imdb.com/title/%s/' % str(id)
		else:
			content = 'https://www.themoviedb.org/movie/%s' % str(id)
		nfo_file.write(content)
		nfo_file.close()
	strm_filepath = os.path.join(movie_folder, str(id) + '.strm')
	if not xbmcvfs.exists(strm_filepath):
		changed = True
		strm_file = xbmcvfs.File(strm_filepath, 'w')
		content = plugin.url_for('movies_play', src=src, id=id)
		strm_file.write(content)
		strm_file.close()
	return changed

def batch_add_movies_to_library(library_folder, id):
	if id == None:
		return
	changed = False
	movie_folder = os.path.join(library_folder, str(id) + '/')
	if not xbmcvfs.exists(movie_folder):
		try:
			xbmcvfs.mkdir(movie_folder)
		except:
			pass
	nfo_filepath = os.path.join(movie_folder, str(id) + '.nfo')
	if not xbmcvfs.exists(nfo_filepath):
		changed = True
		nfo_file = xbmcvfs.File(nfo_filepath, 'w')
		content = 'https://www.imdb.com/title/%s/' % str(id)
		nfo_file.write(content)
		nfo_file.close()
	strm_filepath = os.path.join(movie_folder, str(id) + '.strm')
	src = 'imdb'
	if not xbmcvfs.exists(strm_filepath):
		changed = True
		strm_file = xbmcvfs.File(strm_filepath, 'w')
		try:
			content = plugin.url_for('movies_play', src=src, id=id)
			strm_file.write(content)
			strm_file.close()
		except:
			pass
	return changed

def setup_library(library_folder):
	if library_folder[-1] != '/':
		library_folder += '/'
	if not xbmcvfs.exists(library_folder):
		xbmcvfs.mkdir(library_folder)
		msg = 'Would you like to automatically set OpenMeta as a movies video source?'
		if dialogs.yesno('Library setup', msg):
			source_thumbnail = nav_base.get_icon_path('movies')
			source_name = 'OpenMeta Movies'
			source_content = "('%s','movies','metadata.themoviedb.org','',2147483647,1,'<settings><setting id=\"RatingS\" value=\"TMDb\" /><setting id=\"certprefix\" value=\"Rated \" /><setting id=\"fanart\" value=\"true\" /><setting id=\"imdbanyway\" value=\"false\" /><setting id=\"keeporiginaltitle\" value=\"false\" /><setting id=\"language\" value=\"en\" /><setting id=\"tmdbcertcountry\" value=\"us\" /><setting id=\"trailer\" value=\"true\" /></settings>',0,0,NULL,NULL)" % library_folder
			tools.add_source(source_name, library_folder, source_content, source_thumbnail)
	return xbmc.translatePath(library_folder)

def auto_movie_setup(library_folder):
	if library_folder[-1] != '/':
		library_folder += '/'
	try:
		xbmcvfs.mkdir(library_folder)
		source_thumbnail = nav_base.get_icon_path('movies')
		source_name = 'OpenMeta Movies'
		source_content = "('%s','movies','metadata.themoviedb.org','',2147483647,1,'<settings><setting id=\"RatingS\" value=\"TMDb\" /><setting id=\"certprefix\" value=\"Rated \" /><setting id=\"fanart\" value=\"true\" /><setting id=\"imdbanyway\" value=\"false\" /><setting id=\"keeporiginaltitle\" value=\"false\" /><setting id=\"language\" value=\"en\" /><setting id=\"tmdbcertcountry\" value=\"us\" /><setting id=\"trailer\" value=\"true\" /></settings>',0,0,NULL,NULL)" % library_folder
		tools.add_source(source_name, library_folder, source_content, source_thumbnail)
		return True
	except:
		False