import os, re, csv, sys, time, json, urllib, string, random, shutil, logging, urlparse, datetime, functools, threading, collections
try:
	import cPickle as pickle
except ImportError:
	import pickle
import xbmc, xbmcplugin, xbmcgui, xbmcaddon

VIEW_MODES = {
    'thumbnail': {
        'skin.confluence': 500,
        'skin.aeon.nox': 551,
        'skin.confluence-vertical': 500,
        'skin.jx720': 52,
        'skin.pm3-hd': 53,
        'skin.rapier': 50,
        'skin.simplicity': 500,
        'skin.slik': 53,
        'skin.touched': 500,
        'skin.transparency': 53,
        'skin.xeebo': 55
	}}

def to_utf8(text):
	try:
		return text.encode('utf-8')
	except:
		pass
	return text

class _PersistentDictMixin(object):
	def __init__(self, filename, flag='c', mode=None, file_format='pickle'):
		self.lock = threading.RLock()
		self.flag = flag
		self.mode = mode
		self.file_format = file_format
		self.filename = filename
		if flag != 'n' and os.access(filename, os.R_OK):
			fileobj = open(filename, 'rb' if file_format == 'pickle' else 'r')
			with fileobj:
				self.load(fileobj)

	def id_generator(self, size=6, chars=string.ascii_uppercase + string.digits):
		return ''.join(random.choice(chars) for _ in range(size))

	def sync(self):
		with self.lock:
			self._sync()
            
	def _sync(self):
		if self.flag == 'r':
			return
		filename = self.filename
		tempname = filename + '.' + self.id_generator()   + '.tmp'
		fileobj = open(tempname, 'wb' if self.file_format == 'pickle' else 'w')
		try:
			self.dump(fileobj)
		except Exception as e:
			os.remove(tempname)
			raise
		finally:
			fileobj.close()
		shutil.move(tempname, self.filename)
		if self.mode is not None:
			os.chmod(self.filename, self.mode)

	def close(self):
		self.sync()

	def __enter__(self):
		return self

	def __exit__(self, *exc_info):
		self.close()

	def dump(self, fileobj):
		if self.file_format == 'csv':
			csv.writer(fileobj).writerows(self.raw_dict().items())
		elif self.file_format == 'json':
			json.dump(self.raw_dict(), fileobj, separators=(',', ':'))
		elif self.file_format == 'pickle':
			pickle.dump(dict(self.raw_dict()), fileobj, 2)
		else:
			raise NotImplementedError('Unknown format: ' + repr(self.file_format))

	def load(self, fileobj):
		for loader in (pickle.load, json.load, csv.reader):
			fileobj.seek(0)
			try:
				return self.initial_update(loader(fileobj))
			except Exception as e:
				pass
		raise ValueError('File not in a supported format')

	def raw_dict(self):
		raise NotImplementedError

class _Storage(collections.MutableMapping, _PersistentDictMixin):
	def __init__(self, filename, file_format='pickle'):
		self._items = {}
		_PersistentDictMixin.__init__(self, filename, file_format=file_format)

	def __setitem__(self, key, val):
		self._items.__setitem__(key, val)

	def __getitem__(self, key):
		return self._items.__getitem__(key)

	def __delitem__(self, key):
		self._items.__delitem__(key)

	def __iter__(self):
		return iter(self._items)

	def __len__(self):
		return self._items.__len__

	def raw_dict(self):
		return self._items

	initial_update = collections.MutableMapping.update

	def clear(self):
		super(_Storage, self).clear()
		self.sync()

class TimedStorage(_Storage):
	def __init__(self, filename, file_format='pickle', TTL=None):
		self.TTL = TTL
		_Storage.__init__(self, filename, file_format=file_format)

	def __setitem__(self, key, val, raw=False):
		if raw:
			self._items[key] = val
		else:
			self._items[key] = (val, time.time())

	def __getitem__(self, key):
		val, timestamp = self._items[key]
		if self.TTL and (datetime.datetime.utcnow() - datetime.datetime.utcfromtimestamp(timestamp) > self.TTL):
			del self._items[key]
			return self._items[key][0]
		return val

	def initial_update(self, mapping):
		for key, val in mapping.items():
			_, timestamp = val
			if not self.TTL or (datetime.datetime.utcnow() - datetime.datetime.utcfromtimestamp(timestamp) < self.TTL):
				self.__setitem__(key, val, raw=True)

class ListItem(object):
	def __init__(self, label=None, label2=None, icon=None, thumbnail=None, path=None):
		kwargs = {
			'label': label,
			'label2': label2,
			'iconImage': icon,
			'thumbnailImage': thumbnail,
			'path': path
			}
		kwargs = dict((key, val) for key, val in kwargs.items() if val is not None)
		self._listitem = xbmcgui.ListItem(**kwargs)
		self._icon = icon
		self._path = path
		self._thumbnail = thumbnail
		self._context_menu_items = []
		self.is_folder = True
		self._played = False

	def __repr__(self):
		return ('<ListItem "%s">' % to_utf8(self.label))

	def __str__(self):
		return ('%s (%s)' % (to_utf8(self.label), self.path))

	def get_context_menu_items(self):
		return self._context_menu_items

	def add_context_menu_items(self, items, replace_items=False):
		for label, action in items:
			assert isinstance(label, basestring)
			assert isinstance(action, basestring)
		if replace_items:
			self._context_menu_items = []
		self._context_menu_items.extend(items)
		self._listitem.addContextMenuItems(items, replace_items)

	def get_label(self):
		return self._listitem.getLabel()

	def set_label(self, label):
		return self._listitem.setLabel(label)

	label = property(get_label, set_label)

	def get_label2(self):
		return self._listitem.getLabel2()

	def set_label2(self, label2):
		return self._listitem.setLabel2(label2)

	label2 = property(get_label2, set_label2)

	def is_selected(self):
		return self._listitem.isSelected()

	def select(self, selected_status=True):
		return self._listitem.select(selected_status)

	selected = property(is_selected, select)

	def set_info(self, type, info_labels):
		return self._listitem.setInfo(type, info_labels)

	def get_property(self, key):
		return self._listitem.getProperty(key)

	def set_property(self, key, value):
		return self._listitem.setProperty(key, value)

	def add_stream_info(self, stream_type, stream_values):
		return self._listitem.addStreamInfo(stream_type, stream_values)

	def get_icon(self):
		return self._icon

	def set_icon(self, icon):
		self._icon = icon
		return self._listitem.setIconImage(icon)

	icon = property(get_icon, set_icon)

	def get_thumbnail(self):
		return self._thumbnail

	def set_thumbnail(self, thumbnail):
		self._thumbnail = thumbnail
		return self._listitem.setThumbnailImage(thumbnail)

	thumbnail = property(get_thumbnail, set_thumbnail)

	def get_path(self):
		return self._path

	def set_path(self, path):
		self._path = path
		return self._listitem.setPath(path)

	path = property(get_path, set_path)

	def get_is_playable(self):
		return not self.is_folder

	def set_is_playable(self, is_playable):
		value = 'false'
		if is_playable:
			value = 'true'
		self.set_property('isPlayable', value)
		self.is_folder = not is_playable

	playable = property(get_is_playable, set_is_playable)

	def set_played(self, was_played):
		self._played = was_played

	def get_played(self):
		return self._played

	def as_tuple(self):
		return self.path, self._listitem, self.is_folder

	def as_xbmc_listitem(self):
		return self._listitem

	@classmethod
	def from_dict(cls, label=None, label2=None, icon=None, thumbnail=None, path=None, selected=None, info=None, properties=None, context_menu=None,
					replace_context_menu=False, is_playable=None, info_type='video', stream_info=None, poster=None,banner=None, isTV=False, is_folder=None):
		listitem = cls(label, label2, icon, thumbnail, path)
		if selected is not None:
			listitem.select(selected)
		if info:
			listitem.set_info(info_type, info)
		if is_playable:
			listitem.set_is_playable(True)
			listitem.is_folder = False
		if is_folder:
			listitem.is_folder = True
		if properties:
			if hasattr(properties, 'items'):
				properties = properties.items()
			for key, val in properties:
				listitem.set_property(key, val)
		if stream_info:
			for stream_type, stream_values in stream_info.items():
				listitem.add_stream_info(stream_type, stream_values)
		if context_menu:
			listitem.add_context_menu_items(context_menu, replace_context_menu)
		art = {}
		if poster:
			art['poster'] = poster
			if isTV:
				art['tvshow.poster'] = poster
				art['season.poster'] = poster
		if banner:
			art['banner'] = banner
			if isTV:
				art['tvshow.banner'] = banner
				art['season.banner'] = banner                            
		if thumbnail:
			art['thumb'] = thumbnail
		if art:
			try:
				listitem._listitem.setArt(art)
			except:
				pass
		return listitem

class SortMethod(object):

	@classmethod
	def from_string(cls, sort_method):
		return getattr(cls, sort_method.upper())
    
class XBMCMixin(object):

	_function_cache_name = '.functions'
	_lock = threading.Lock()

	def cached(self, TTL=60 * 24, cache=None):
		cachename = cache
		if cachename is None:
			cachename = self._function_cache_name
		if not hasattr(self, '_unsynced_storages'):
			self._unsynced_storages = {}
		unsynced_storages = self._unsynced_storages
		storage_path = self.storage_path

		def decorating_function(function):

			@functools.wraps(function)
			def wrapper(*args, **kwargs):
				storage = XBMCMixin.get_storage_s(unsynced_storages, storage_path, cachename, file_format='pickle', TTL=TTL)
				kwd_mark = 'f35c2d973e1bbbc61ca60fc6d7ae4eb3'
				key = (function.__name__, kwd_mark,) + args
				if kwargs:
					key += (kwd_mark,) + tuple(sorted(kwargs.items()))
				try:
					result = storage[key]
				except KeyError:
					result = function(*args, **kwargs)
					if result:
						storage[key] = result
						storage.sync()
				return result
			return wrapper
		return decorating_function

	def clear_function_cache(self):
		self.get_storage(self._function_cache_name).clear()

	def list_storages(self):
		return [name for name in os.listdir(self.storage_path) if not name.startswith('.')]

	@staticmethod
	def get_storage_s(unsynced_storages, storage_path, name='main', file_format='pickle', TTL=None):
		filename = os.path.join(storage_path, name)
		storage = unsynced_storages.get(filename)
		if storage is None:
			with XBMCMixin._lock:
				storage = unsynced_storages.get(filename)
				if storage is None:
					if TTL:
						TTL = datetime.timedelta(minutes=TTL)
					try:
						storage = TimedStorage(filename, file_format, TTL)
					except ValueError:
						os.remove(filename)
						storage = TimedStorage(filename, file_format, TTL)
					unsynced_storages[filename] = storage
		return storage
                
	def get_storage(self, name='main', file_format='pickle', TTL=None):
		if not hasattr(self, '_unsynced_storages'):
			self._unsynced_storages = {}
		return XBMCMixin.get_storage_s(self._unsynced_storages, self.storage_path, name, file_format, TTL)
        
	def temp_fn(self, path):
		return os.path.join(xbmc.translatePath('special://temp/'), path)

	def get_string(self, stringid):
		stringid = int(stringid)
		if not hasattr(self, '_strings'):
			self._strings = {}
		if not stringid in self._strings:
			self._strings[stringid] = self.addon.getLocalizedString(stringid)
		return self._strings[stringid]

	def set_content(self, content):
		contents = [
			'actors',
			'addons',
			'countries',
			'directors',
			'episodes',
			'files',
			'genres',
			'images',
			'movies',
			'playlists',
			'plugins',
			'roles',
			'seasons',
			'sets',
			'studios',
			'tags',
			'tvshows',
			'years'
			]
		if content not in contents:
			return False
		else:
			xbmcplugin.setContent(self.handle, content)
			return True

	def get_setting(self, key, converter=None, choices=None):
		value = self.addon.getSetting(id=key)
		if converter is str:
			return value
		elif converter is unicode:
			return value.decode('utf-8')
		elif converter is bool:
			return value == 'true'
		elif converter is int:
			return int(value)
		elif isinstance(choices, (list, tuple)):
			return choices[int(value)]
		elif converter is None:
			try:
				return json.loads(value)
			except:
				return value
		else:
			raise TypeError('Acceptable converters are str, unicode, bool and int. Acceptable choices are instances of list  or tuple.')

	def set_setting(self, key, val):
		if isinstance(val, list) or isinstance(val, dict):
			val = json.dumps(val)
		return self.addon.setSetting(id=key, value=val)

	def open_settings(self):
		self.addon.openSettings()

	def add_to_playlist(self, items, playlist='video'):
		playlists = {'music': 0, 'video': 1}
		assert playlist in playlists.keys(), ('Playlist "%s" is invalid.' % playlist)
		selected_playlist = xbmc.PlayList(playlists[playlist])
		_items = []
		for item in items:
			if not hasattr(item, 'as_xbmc_listitem'):
				item['info_type'] = playlist
				item = ListItem.from_dict(**item)
			_items.append(item)
			selected_playlist.add(item.get_path(), item.as_xbmc_listitem())
		return _items

	def get_view_mode_id(self, view_mode):
		view_mode_ids = VIEW_MODES.get(view_mode.lower())
		if view_mode_ids:
			return view_mode_ids.get(xbmc.getSkinDir())
		return None

	def set_view_mode(self, view_mode_id):
		xbmc.executebuiltin('Container.SetViewMode(%d)' % view_mode_id)

	def keyboard(self, default=None, heading=None, hidden=False):
		if heading is None:
			heading = self.addon.getAddonInfo('name')
		if default is None:
			default = ''
		keyboard = xbmc.Keyboard(default, heading, hidden)
		keyboard.doModal()
		if keyboard.isConfirmed():
			return keyboard.getText()

	def notify(self, msg='', title=None, delay=5000, image=''):
		if title is None:
			title = self.addon.getAddonInfo('name')
		xbmc.executebuiltin('XBMC.Notification("%s", "%s", "%s", "%s", %s")' % (to_utf8(msg), to_utf8(title), delay, to_utf8(image), False))

	def _listitemify(self, item):
		info_type = self.info_type if hasattr(self, 'info_type') else 'video'
		if not hasattr(item, 'as_tuple'):
			if 'info_type' not in item.keys():
				item['info_type'] = info_type
			item = ListItem.from_dict(**item)
		return item

	def _add_subtitles(self, subtitles):
		player = xbmc.Player()
		for _ in xrange(30):
			if player.isPlaying():
				break
			time.sleep(1)
		else:
			raise Exception('No video playing. Aborted after 30 seconds.')
		player.setSubtitles(subtitles)

	def set_resolved_url(self, item=None, subtitles=None):
		if self._end_of_directory:
			raise Exception('Current Kodi handle has been removed. Either set_resolved_url(), end_of_directory(), or finish() has already been called.')
		self._end_of_directory = True
		succeeded = True
		if item is None:
			item = {}
			succeeded = False
		if isinstance(item, basestring):
			item = {'path': item}
		item = self._listitemify(item)
		item.set_played(True)
		xbmcplugin.setResolvedUrl(self.handle, succeeded, item.as_xbmc_listitem())
		if subtitles:
			self._add_subtitles(subtitles)
		return [item]

	def play_video(self, item, player=None):
		try:
			item['info_type'] = 'video'
		except TypeError:
			pass
		item = self._listitemify(item)
		item.set_played(True)
		if player:
			_player = xbmc.Player(player)
		else:
			_player = xbmc.Player()
		_player.play(item.get_path(), item.as_xbmc_listitem())
		return [item]

	def play_audio(self, item, player=None):
		try:
			item['info_type'] = 'audio'
		except TypeError:
			pass
		item = self._listitemify(item)
		item.set_played(True)
		if player:
			_player = xbmc.Player(player)
		else:
			_player = xbmc.Player()
		_player.play(item.get_path(), item.as_xbmc_listitem())
		return [item]

	def add_items(self, items):
		_items = [self._listitemify(item) for item in items]
		tuples = [item.as_tuple() for item in _items]
		xbmcplugin.addDirectoryItems(self.handle, tuples, len(tuples))
		self.added_items.extend(_items)
		return _items

	def end_of_directory(self, succeeded=True, update_listing=False, cache_to_disc=True):
		self._update_listing = update_listing
		if not self._end_of_directory:
			self._end_of_directory = True
			return xbmcplugin.endOfDirectory(self.handle, succeeded, update_listing, cache_to_disc)
		assert False, 'Already called endOfDirectory.'

	def add_sort_method(self, sort_method, label2_mask=None):
		try:
			sort_method = SortMethod.from_string(sort_method)
		except AttributeError:
			pass
		if label2_mask:
			xbmcplugin.addSortMethod(self.handle, sort_method, label2_mask)
		else:
			xbmcplugin.addSortMethod(self.handle, sort_method)

	def finish(self, items=None, sort_methods=None, succeeded=True, update_listing=False, cache_to_disc=True, view_mode=None):
		if items:
			self.add_items(items)
		if sort_methods:
			for sort_method in sort_methods:
				if not isinstance(sort_method, basestring) and hasattr(sort_method, '__len__'):
					self.add_sort_method(*sort_method)
				else:
					self.add_sort_method(sort_method)
		if view_mode is not None:
			try:
				view_mode_id = int(view_mode)
			except ValueError:
				view_mode_id = self.get_view_mode_id(view_mode)
			if view_mode_id is not None:
				self.set_view_mode(view_mode_id)
		self.end_of_directory(succeeded, update_listing, cache_to_disc)
		return self.added_items

class Request(object):
	def __init__(self, url, handle):
		self.url = url
		self.handle = int(handle)
		self.scheme, remainder = url.split(':', 1)
		parts = urlparse.urlparse(remainder)
		self.netloc, self.path, self.query_string = (parts[1], parts[2], parts[4])
		self.args = unpickle_args(urlparse.parse_qs(self.query_string))

def unpickle_args(items):
	pickled= items.pop('_pickled', None)
	if pickled is None:
		return items
	pickled_keys = pickled[0].split(',')
	ret = {}
	for key, vals in items.items():
		if key in pickled_keys:
			ret[key] = [pickle.loads(val) for val in vals]
		else:
			ret[key] = vals
	return ret

def pickle_dict(items):
	ret = {}
	pickled_keys = []
	for key, val in items.items():
		if isinstance(val, basestring):
			ret[key] = val
		else:
			pickled_keys.append(key)
			ret[key] = pickle.dumps(val)
	if pickled_keys:
		ret['_pickled'] = ','.join(pickled_keys)
	return ret

def unpickle_dict(items):
	pickled_keys = items.pop('_pickled', '').split(',')
	ret = {}
	for key, val in items.items():
		if key in pickled_keys:
			ret[key] = pickle.loads(val)
		else:
			ret[key] = val
	return ret

class AmbiguousUrlException(Exception):
	pass

class NotFoundException(Exception):
	pass

class UrlRule(object):
	def __init__(self, url_rule, view_func, name, options):
		self._name = name
		self._url_rule = url_rule
		self._view_func = view_func
		self._options = options or {}
		self._keywords = re.findall(r'\<(.+?)\>', url_rule)
		self._url_format = self._url_rule.replace('<', '{').replace('>', '}')
		rule = self._url_rule
		if rule != '/':
			rule = self._url_rule.rstrip('/') + '/?'
		p = rule.replace('<', '(?P<').replace('>', '>[^/]+?)')
		try:
			self._regex = re.compile('^' + p + '$')
		except re.error as e:
			raise ValueError('There was a problem creating this URL rule. Ensure you do not have any unpaired angle brackets: "<" or ">"')

	def __eq__(self, other):
		return ((self._name, self._url_rule, self._view_func, self._options) == (other._name, other._url_rule, other._view_func, other._options))

	def __ne__(self, other):
		return not self.__eq__(other)

	def match(self, path):
		m = self._regex.search(path)
		if not m:
			raise NotFoundException
		items = dict((key, urllib.unquote_plus(val)) for key, val in m.groupdict().items())
		items = unpickle_dict(items)
		[items.setdefault(key, val) for key, val in self._options.items()]
		return self._view_func, items

	def _make_path(self, items):
		for key, val in items.items():
			if not isinstance(val, basestring):
				raise TypeError('Value "%s" for key "%s" must be an instance of basestring' % (val, key))
			items[key] = urllib.quote_plus(val)
		try:
			path = self._url_format.format(**items)
		except AttributeError:
			path = self._url_format
			for key, val in items.items():
				path = path.replace('{%s}' % key, val)
		return path

	def _make_qs(self, items):
		return urllib.urlencode(pickle_dict(items))

	def make_path_qs(self, items):
		for key, val in items.items():
			if isinstance(val, (int, long)):
				items[key] = str(val)
		url_items = dict((key, val) for key, val in self._options.items() if key in self._keywords)
		url_items.update((key, val) for key, val in items.items() if key in self._keywords)
		path = self._make_path(url_items)
		qs_items = dict((key, val) for key, val in items.items() if key not in self._keywords)
		qs = self._make_qs(qs_items)
		if qs:
			return '?'.join([path, qs])
		return path

	@property
	def regex(self):
		return self._regex

	@property
	def view_func(self):
		return self._view_func

	@property
	def url_format(self):
		return self._url_format

	@property
	def name(self):
		return self._name

	@property
	def keywords(self):
		return self._keywords

def setup_log(name):
	_log = logging.getLogger(name)
	GLOBAL_LOG_LEVEL = logging.DEBUG
	_log.setLevel(GLOBAL_LOG_LEVEL)
	handler = logging.StreamHandler()
	formatter = logging.Formatter('%(asctime)s - %(levelname)s - [%(name)s] %(message)s')
	handler.setFormatter(formatter)
	_log.addHandler(handler)
	return _log

log = setup_log('xswift2')

class Plugin(XBMCMixin):
	def __init__(self, name=None, addon_id=None, filepath=None, info_type=None):
		self._name = name
		self._routes = []
		self._view_functions = {}
		if addon_id:
			self._addon = xbmcaddon.Addon(id=addon_id)
		else:
			self._addon = xbmcaddon.Addon()
		self._addon_id = addon_id or self._addon.getAddonInfo('id')
		self._name = name or self._addon.getAddonInfo('name')
		self._info_type = info_type
		if not self._info_type:
			types = {
				'video': 'video',
				'audio': 'music',
				'image': 'pictures'
				}
			self._info_type = types.get(self._addon_id.split('.')[1], 'video')
		self._current_items = []
		self._request = None
		self._end_of_directory = False
		self._update_listing = False
		self._log = setup_log(self._addon_id)
		self._storage_path = xbmc.translatePath('special://profile/addon_data/%s/.storage/' % self._addon_id)
		if not os.path.isdir(self._storage_path):
			os.makedirs(self._storage_path)

	@property
	def info_type(self):
		return self._info_type

	@property
	def log(self):
		return self._log

	@property
	def id(self):
		return self._addon_id

	@property
	def storage_path(self):
		return self._storage_path

	@property
	def addon(self):
		return self._addon

	@property
	def added_items(self):
		return self._current_items

	def clear_added_items(self):
		self._current_items = []

	@property
	def handle(self):
		return self.request.handle

	@property
	def request(self):
		if self._request is None:
			raise Exception('Please ensure that `plugin.run()` has been called before attempting to access the current request.')
		return self._request

	@property
	def name(self):
		return self._name

	def _parse_request(self, url=None, handle=None):
		if url is None:
			url = sys.argv[0]
			if len(sys.argv) == 3:
				url += sys.argv[2]
		if handle is None:
			handle = sys.argv[1]
		return Request(url, handle)

	def cached_route(self, url_rule, name=None, options=None, TTL=None, cache=None):
		route_decorator = self.route(url_rule, name=name, options=options)
		if TTL:
			cache_decorator = self.cached(TTL, cache=cache)
		else:
			cache_decorator = self.cached(cache=cache)
		def new_decorator(func):
			return route_decorator(cache_decorator(func))
		return new_decorator

	def route(self, url_rule, name=None, options=None):
		def decorator(f):
			view_name = name or f.__name__
			self.add_url_rule(url_rule, f, name=view_name, options=options)
			return f
		return decorator

	def add_url_rule(self, url_rule, view_func, name, options=None):
		rule = UrlRule(url_rule, view_func, name, options)
		if name in self._view_functions.keys():
			self._view_functions[name] = None
		else:
			self._view_functions[name] = rule
		self._routes.append(rule)

	def url_for(self, endpoint, **items):
		try:
			rule = self._view_functions[endpoint]
		except KeyError:
			try:
				rule = (rule for rule in self._view_functions.values() if rule.view_func == endpoint).next()
			except StopIteration:
				raise NotFoundException("%s does not match any known patterns." % endpoint)
		if not rule:
			raise AmbiguousUrlException
		pathqs = rule.make_path_qs(items)
		return 'plugin://%s%s' % (self._addon_id, pathqs)

	def _dispatch(self, path):
		for rule in self._routes:
			try:
				view_func, items = rule.match(path)
			except NotFoundException:
				continue
			listitems = view_func(**items)
			if not self._end_of_directory and self.handle >= 0:
				if listitems is None:
					self.finish(succeeded=False)
				else:
					listitems = self.finish(listitems)
			return listitems
		raise NotFoundException('No matching view found for %s' % path)

	def run(self, test=False):
		self._request = self._parse_request()
		items = self._dispatch(self.request.path)
		if hasattr(self, '_unsynced_storages'):
			for storage in self._unsynced_storages.values():
				storage.close()
		return items

plugin = Plugin()