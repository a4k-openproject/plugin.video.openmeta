import datetime
import xbmc
from addon import update_library
from resources.lib.xswift2 import plugin
from resources.lib.video_player import PLAYER
from resources.lib.settings import SETTING_TOTAL_SETUP_DONE

def go_idle(duration):
	while not xbmc.abortRequested and duration > 0:
		if PLAYER.isPlayingVideo():
			PLAYER.currentTime = PLAYER.getTime()
		xbmc.sleep(1000)
		duration -= 1

def future(seconds):
	return datetime.datetime.now() + datetime.timedelta(seconds=seconds)

def main():
	go_idle(15)
	if plugin.get_setting(SETTING_TOTAL_SETUP_DONE, bool) == False:
		xbmc.executebuiltin('RunPlugin(plugin://plugin.video.openmeta/setup/total)')
		plugin.set_setting(SETTING_TOTAL_SETUP_DONE, 'true')
	next_update = future(0)
	while not xbmc.abortRequested:
		if next_update <= future(0):
			next_update = future(8*60*60)
			update_library()
		go_idle(30*60)

if __name__ == '__main__':
	main()