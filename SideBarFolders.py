# coding=utf8
import sublime, sublime_plugin
import os
import codecs
import re

MENU = '''[
	{"caption": "Help", "id": "help" },
	{
		"caption": "Folders",
		"id": "folders",
		"mnemonic": "d",
		"children": [
			{ "caption": "-" , "id": "open" },
			{ "command": "side_bar_folders_start_blank", "caption": "Load Folder…"},
			{ "command": "side_bar_folders_start_blank", "caption": "Append Folder…", "args": {"append": true}},
			{ "caption": "-", "id": "edit" },
			{ "command": "open_file", "args": { "file": "${packages}/User/Side Bar Folders.sublime-settings" }, "caption": "Edit Folders"},
			{ "command": "side_bar_folders_sidebar_clear", "caption": "Clear Sidebar"},
			{ "command": "side_bar_folders_remove_current", "caption": "Remove Current Folder"},
			{ "caption": "-" , "id": "history" },
			{
				"caption": "%(buried_label)s Folder",
				"children": [
					{ "command": "side_bar_folders_swap", "caption": "Use \\"%(buried_label)s\\" Folder List as Default "},
					{ "caption": "-" },
					// Folder history goes here
%(buried_entries)s
				]
			},
			// Folder history goes here
			{ "caption": "-" , "id": "options-separator" },
%(entries)s
			{ "caption": "-" , "id": "options" },
			{ "command": "side_bar_folders_audit_all", "caption": "Clear Missing Folders"},
			{ "caption": "-" , "id": "end" }
		]
	}
]
'''

FOLDER_ENTRY = '%(indent)s{ "command": "side_bar_folders_load", "args":{ "index": %(index)d%(append)s }},'


def Window():
	return sublime.active_window()

s = {}
Pref = {}

# when closing a project, project_data returns "None"
def get_project_data(window):
	project_data = window.project_data()
	if project_data is None or 'folders' not in project_data:
		project_data = {}
		project_data['folders'] = []
	return project_data

def get_project_path(window):
	file_name = window.project_file_name()
	return None if file_name is None else os.path.dirname(file_name)

def is_sidebar_open():
	window = Window()
	if int(sublime.version()) >= 3099:
		return window.is_sidebar_visible()
	view = window.active_view()
	if view:
		sel1 = view.sel()[0]
		window.run_command('focus_side_bar')
		window.run_command('move', {"by": "characters", "forward": True})
		sel2 = view.sel()[0]
		if sel1 != sel2:
			window.run_command('move', {"by": "characters", "forward": False})
			return False # print('sidebar is closed')
		else:
			group, index = window.get_view_index(view)
			window.focus_view(view)
			window.focus_group(group)
			return True # print('sidebar is open')
	return True # by default assume is open if no view is opened

def is_subdir(path, directory):
	path = os.path.realpath(path)
	directory = os.path.realpath(directory)

	try:
		relative = os.path.relpath(path, directory)

		if relative.startswith(os.pardir):
			return False
		else:
			return True
	except:
		return False

class Menu(object):
	@staticmethod
	def prepare_menu():
		path = os.path.join(sublime.packages_path(), "User", "Side Bar Folders")
		if not os.path.exists(path):
			os.makedirs(path)
		menu = os.path.join(path, "Main.sublime-menu")
		if not os.path.exists(menu):
			Menu.generate_menu(len(Pref.folders))
		return

	@staticmethod
	def generate_menu_item(index, append=False, indent=3):
		return FOLDER_ENTRY % {
			"indent":"	" * indent,
			"index": index,
			"append": ", \"append\": true" if append else ""
		}

	@staticmethod
	def generate_menu(count):
		menu = os.path.join(sublime.packages_path(), "User", "Side Bar Folders", "Main.sublime-menu")
		swap_append = s.get('swap_append_load', False)
		try:
			with codecs.open(menu, "w", encoding="utf-8") as f:
				f.write(
					MENU % {
						"buried_label": "Append" if not swap_append else "Load",
						"buried_entries": '\n'.join([Menu.generate_menu_item(x, not swap_append, 5) for x in range(0, count)]),
						"entries": '\n'.join([Menu.generate_menu_item(x, swap_append) for x in range(0, count)])
					}
				)
		except:
			pass

class Pref:
	def load(self):
		Pref.folders = s.get('folders', [])

	def reload_prefs(self):
		Pref.history = s.get('history_limit', 66)
		Pref.swap = s.get("swap_append_load", False)
		Pref.shorter_labels = s.get('shorter_labels', True)
		Pref.label_replace_regexp = s.get('label_replace_regexp', True)
		Pref.label_unix_style = s.get('label_unix_style', False)
		Pref.label_characters = s.get('label_characters', 51)
		Pref.auto_load_folders_list = s.get('auto_load_folders_list', [])
		Pref.home = os.path.expanduser("~")

		Menu.generate_menu(len(Pref.folders))
		Pref.reload()

	def reload(self):
		Pref.folders = s.get('folders', [])
		for window in sublime.windows():
			try:
				project_data = get_project_data(window)
				for folder in range(len(project_data['folders'])):
					for k in range(len(Pref.folders)):
						if Pref.folders[k]['path'] == project_data['folders'][folder]['path']:
							project_data['folders'][folder] = Pref.folders[k]
							window.set_project_data(project_data)
			except:
				pass
		Pref.save()

	def adjust_history(self):
		limit = Pref.history
		if limit > 0:
			count = len(Pref.folders)
			if count > limit:
				Pref.folders = Pref.folders[-limit:]

	def save(self):
		Pref.adjust_history()
		Pref.folders = sorted(Pref.folders, key=lambda x: x["display"].lower() if 'display' in x and Pref.shorter_labels else Pref.display_name(x["path"].lower()), reverse=True)
		if s.get('folders', []) != Pref.folders:
			s.set('folders', Pref.folders)
			sublime.save_settings('Side Bar Folders.sublime-settings')
			Menu.generate_menu(len(Pref.folders))

	def save_folders(self):
		for window in sublime.windows():
			try:
				for folder in get_project_data(window)['folders']:
					Pref.append(folder, window)
			except:
				pass
		Pref.save()

	def normalize_folder(self, folder, window):
		# If a path is given that is relative (from a project of disk)
		# Convert the relative path to absolute
		normalize = False
		if sublime.platform() == "windows":
			if re.match(r"(^[A-Za-z]{1}:(?:\\|/))", folder) is None:
				normalize = True
		elif not folder.startswith("/"):
			normalize = True

		project_path = get_project_path(window)
		if project_path is not None and normalize:
			folder = os.path.normpath(os.path.join(project_path, folder))
		return folder

	def display_name(self, folder):
		if not Pref.shorter_labels:
			return folder
		display = folder
		if folder.startswith(Pref.home):
			display = folder.replace(Pref.home, "~", 1)
		if Pref.label_replace_regexp != '':
			display = re.sub(Pref.label_replace_regexp.replace('\\', '\\\\'), '', display, 1, re.I)
		if Pref.label_unix_style:
			display = display.replace('\\', '/')
		if len(display) > Pref.label_characters:
			chars = int(Pref.label_characters/2)
			display = display[:chars] + "…" + display[-chars:]
		return display

	def append(self, folder, window):
		if len(Pref.folders) >= Pref.history:
			return
		folder["path"] = Pref.normalize_folder(folder["path"], window)
		for k in range(len(Pref.folders)):
			if Pref.folders[k]['path'] == folder['path']:
				Pref.folders[k] = folder
				return
		Pref.folders.append(folder)

	def bucle(self):
		Pref.save_folders()
		sublime.set_timeout(lambda:Pref.bucle(), 60*1000)

class side_bar_folders_start_blank(sublime_plugin.WindowCommand):
	def run(self, append = False):
		project = get_project_data(Window())
		if not append:
			project['folders'] = []
			Window().set_project_data(project)
		Window().run_command('prompt_add_folder')

	def is_enabled(self, append = False):
		Pref.save_folders() # <--- this works as an onpopupshowing..
		return True

class side_bar_folders_load(sublime_plugin.WindowCommand):
	def run(self, index =- 1, append = False):
		folder = (Pref.folders[::-1])[index]
		if self.audit_folder(folder, index):
			return
		project = get_project_data(Window())
		if not append:
			project['folders'] = []
		project['folders'].append(folder)
		Window().set_project_data(project)
		if not is_sidebar_open():
			Window().run_command('toggle_side_bar')

	def audit_folder(self, folder, index):
		abort = False
		if not os.path.exists(folder['path']):
			if sublime.ok_cancel_dialog('Folder does not currently exist! Do you want to remove the folder from the history?'):
				if index < len(Pref.folders):
					del Pref.folders[len(Pref.folders) - index - 1]
				Pref.save()
			abort = True
		return abort

	def is_visible(self, index = -1, append = False):
		try:
			return (Pref.folders[::-1])[index] != None
		except:
			return False

	def description(self, index = -1, append = False):
		try:
			item = (Pref.folders[::-1])[index]
			return item["display"] if 'display' in item and Pref.shorter_labels else Pref.display_name(item["path"])
		except:
			return ''

class side_bar_folders_audit_all(sublime_plugin.WindowCommand):
	def run(self):
		if sublime.ok_cancel_dialog('Are you sure?'):
			folders = []
			for item in Pref.folders:
				if os.path.exists(item['path']):
					folders.append(item)
			Pref.folders = folders
			Pref.save()

class side_bar_folders_remove_current(sublime_plugin.WindowCommand):
	def run(self):
		if sublime.ok_cancel_dialog('Are you sure?'):
			project = get_project_data(Window())
			to_delete = {}
			if project and 'folders' in project and project['folders']:
				for item in project['folders']:
					to_delete[item['path']] = ''
			if to_delete:
				project['folders'] = []
				Window().set_project_data(project)

				folders = []
				for item in Pref.folders:
					if item['path'] not in to_delete:
						folders.append(item)
				Pref.folders = folders
				Pref.save()

class side_bar_folders_clear(sublime_plugin.WindowCommand):
	def run(self):
		if sublime.ok_cancel_dialog('Are you sure?'):
			Pref.folders = []
			Pref.save()

class side_bar_folders_sidebar_clear(sublime_plugin.WindowCommand):
	def run(self):
		if sublime.ok_cancel_dialog('Remove all folders?'):
			project = get_project_data(Window())
			project['folders'] = []
			Window().set_project_data(project)

	def is_visible(self):
		return len(get_project_data(Window())['folders']) > 0

class side_bar_folders_listener(sublime_plugin.EventListener):
	def on_activated(self, view):
		Pref.save_folders()
		something_changed = False
		project = get_project_data(Window())
		if Pref.auto_load_folders_list:
			for folder in Pref.auto_load_folders_list:
				folder = {'path': os.path.normpath(folder), 'follow_symlinks': True}
				if folder not in project['folders']:
					something_changed = True
					project['folders'].append(folder)
			if something_changed:
				Window().set_project_data(project)

class side_bar_folders_auto_add_folder_listener(sublime_plugin.EventListener):
	def on_activated(self, view):
		f = view.file_name()
		if not f or view.settings().has('side_bar_folders_auto_load_folder'):
			return
		path = os.path.dirname(f)
		view.settings().set('side_bar_folders_auto_load_folder', 1)
		window = Window()
		project_data = window.project_data()
		if project_data and 'folders' in project_data and any(is_subdir(path, folder['path']) for folder in project_data['folders']):
			return
		if s.get('auto_load_folder_for_opened_file') and path and os.path.exists(path):
			for folder in Pref.folders:
				if is_subdir(path, folder['path']):
					if not project_data or "folders" not in project_data:
						project_data = {'folders': [{'path': folder['path'], 'follow_symlinks': True}]}
					else:
						project_data["folders"].append({'path': folder['path'], 'follow_symlinks': True})

					window.set_project_data(project_data)
					break
			sublime.set_timeout(lambda: window.run_command('reveal_in_side_bar'), 100)

class side_bar_folders_swap(sublime_plugin.WindowCommand):
	def run(self):
		current_swap = s.get("swap_append_load", False)
		s.set("swap_append_load", not current_swap)
		sublime.save_settings('Side Bar Folders.sublime-settings')

class side_bar_folders_quick_switch(sublime_plugin.WindowCommand):
	def run(self):
		folder_list = list(map(lambda folder: folder['path'], s.get('folders', [])))
		folder_list.reverse()
		self.display_list(folder_list)

	def display_list(self, list):
		Window().show_quick_panel(list, self.on_done)

	def on_done(self, index = -1, append = False):
		folder = (Pref.folders[::-1])[index]
		if self.audit_folder(folder, index):
			return
		project = get_project_data(Window())
		if not append:
			project['folders'] = []
		project['folders'].append(folder)
		Window().set_project_data(project)
		if not is_sidebar_open():
			Window().run_command('toggle_side_bar')

	def audit_folder(self, folder, index):
		abort = False
		if not os.path.exists(folder['path']):
			if sublime.ok_cancel_dialog('Folder does not currently exist! Do you want to remove the folder from the history?'):
				if index < len(Pref.folders):
					del Pref.folders[len(Pref.folders) - index - 1]
				Pref.save()
			abort = True
		return abort

	def is_visible(self, index = -1, append = False):
		try:
			return (Pref.folders[::-1])[index] != None
		except:
			return False

	def description(self, index = -1, append = False):
		try:
			item = (Pref.folders[::-1])[index]
			return item["display"] if 'display' in item and Pref.shorter_labels else Pref.display_name(item["path"])
		except:
			return ''

def plugin_loaded():
	global s, Pref
	s = sublime.load_settings('Side Bar Folders.sublime-settings')
	Pref = Pref()
	Pref.load()
	Pref.reload_prefs()
	s.clear_on_change('reload_prefs')
	s.add_on_change('reload_prefs', lambda:Pref.reload_prefs())
	Menu.prepare_menu()
	Pref.bucle()