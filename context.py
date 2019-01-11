import xbmc

def main():
	info = xbmc.getInfoLabel
	if info('ListItem.Episode'):
		url = 'plugin://plugin.video.openmeta/tv/play_by_name/%s/%s/%s/en' % (info('ListItem.TVShowTitle'), info('ListItem.Season'), info('ListItem.Episode'))
	elif info('ListItem.IMDBNumber'):
		url = 'plugin://plugin.video.openmeta/movies/play/imdb/%s' % info('ListItem.IMDBNumber')
	elif info('ListItem.Title'):
		url = 'plugin://plugin.video.openmeta/movies/play_by_name/%s/en' % info('ListItem.Title')
	else:
		url = 'plugin://plugin.video.openmeta/movies/play_by_name/%s/en' % info('ListItem.Label')
	xbmc.executebuiltin('RunPlugin(%s)' % url)

if __name__ == '__main__':
	main()