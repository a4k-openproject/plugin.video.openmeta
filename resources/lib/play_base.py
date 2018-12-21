import json, traceback
import xbmc
from resources.lib import text
from resources.lib import tools
from resources.lib import Trakt
from resources.lib import dialogs
from resources.lib import listers
from resources.lib import properties
from resources.lib.xswift2 import plugin

@plugin.cached(TTL=60, cache='Trakt')
def get_trakt_ids(*args, **kwargs):
	try:
		return Trakt.find_trakt_ids(*args, **kwargs)
	except:
		return None

def action_cancel(clear_playlist=True):
	if clear_playlist:
		xbmc.PlayList(xbmc.PLAYLIST_VIDEO).clear()
	plugin.set_resolved_url()
	xbmc.executebuiltin('Dialog.Close(okdialog, true)')

def action_play(item):
	plugin.play_video(item)

def action_playmedia(item):
	xbmc.executebuiltin('PlayMedia("%s")' % item)

def get_video_link(players, params):
	lister = listers.Lister()
	for lang, lang_params in params.items():
		for key, value in lang_params.items():
			if isinstance(value, basestring):
				params[lang][key + '_+'] = value.replace(' ', '+')
				params[lang][key + '_-'] = value.replace(' ', '-')
				params[lang][key + '_escaped'] = value.replace(' ', '%2520')
				params[lang][key + '_escaped+'] = value.replace(' ', '%252B')
	selection = None
	try:
		if len(players) > 1:
			index = dialogs.select('Play using...', [player.title for player in players])
			if index == -1:
				return None
			players = [players[index]]
		resolve_f = lambda p: resolve_player(p, lister, params)
		result = resolve_f(players[0])
		if result:
			title, links = result
			if len(links) == 1:
				selection = links[0]
			else:
				index = dialogs.select('Play using...', [x['label'] for x in links])
				if index > -1:
					selection = links[index]
		else:
			message = 'Video not found'
			dialogs.ok('Error', message)
	finally:
		lister.stop()
	return selection

def on_play_video(players, params, trakt_ids=None):
	assert players
	action_cancel()
	selection = get_video_link(players, params)
	if not selection:
		return
	link = selection['path']
	if link.startswith('videodb://'):
		return xbmc.executebuiltin('ActivateWindow(10025,"%s")' % link)
	elif link.endswith('.strm'):
		return action_playmedia(link)
	else:
		if trakt_ids:
			properties.set_property('script.trakt.ids', json.dumps(trakt_ids))
		return link
	return None

def resolve_player(player, lister, params):
	results = []
	for command_group in player.commands:  
		if xbmc.abortRequested or not lister.is_active():
			return
		command_group_results = []
		for command in command_group:
			if xbmc.abortRequested or not lister.is_active():
				return
			lang = command.get('language', 'en')
			if not lang in params:
				continue
			parameters = params[lang]
			link = text.apply_parameters(text.to_unicode(command['link']), parameters)
			if link == 'movies' and player.media == 'movies':
				video = tools.get_movie_from_library(parameters['imdb'])
				if video:
					command_group_results.append(video)
			elif link == 'tvshows' and player.media == 'tvshows':
				video = tools.get_episode_from_library(parameters['id'], parameters['season'], parameters['episode'])
				if not video:
					video = tools.get_episode_from_library(parameters['tmdb'], parameters['season'], parameters['episode'])
				if video:
					command_group_results.append(video)
			elif not command.get('steps'):
				command_group_results.append(
					{
						'label': player.title,
						'path': text.urlencode_path(link),
						'action': command.get('action', 'PLAY')
					})
			else:
				steps = [text.to_unicode(step) for step in command['steps']]
				files, dirs = lister.get(link, steps, parameters)
				if files:
					command_group_results += [
						{
							'label': f['label'],
							'path': (f['path']),
							'action': command.get('action', 'PLAY')
						} for f in files]
			if command_group_results:
				break
		results += command_group_results
	if results:
		return player.title, results