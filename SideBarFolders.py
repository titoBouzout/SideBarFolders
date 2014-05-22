# coding=utf8
import sublime, sublime_plugin
import os
import codecs
import re

MENU = '''[
	{"caption": "Help", "mnemonic": "H", "id": "help", "children": [] },
	{
		"caption": "Folders",
		"id": "folders",
		"children": [
			{"command": "side_bar_folders_start_blank", "caption": "Load Folder…"},
			{ "caption": "-" },
			{"command": "side_bar_folders_sidebar_clear", "caption": "Remove All Sidebar Folders"},
			{ "caption": "-" },
			{ "command": "open_file", "args": { "file": "${packages}/User/Side Bar Folders.sublime-settings" }, "caption": "Edit History"},
			{"caption": "-"},
			// Folder history goes here
%(entries)s
			{ "caption": "-" },
			{ "command": "side_bar_folders_clear", "caption": "Clear History" }
		]
	}
]
'''

def Window():
	return sublime.active_window()

s = {}

# when closing a project, project_data returns "None"
def get_project_data(window):
	project_data = window.project_data()
	if project_data is None:
		project_data = {}
		project_data['folders'] = []
	return project_data

def get_project_path(window):
	file_name = window.project_file_name()
	return None if file_name is None else os.path.dirname(file_name)

class Menu(object):
	@staticmethod
	def prepare_menu():
		path = os.path.join(sublime.packages_path(), "User", "Side Bar Folders")
		if not os.path.exists(path):
			os.makedirs(path)
		menu = os.path.join(path, "Main.sublime-menu")
		if not os.path.exists(path):
			Menu.generate_menu(0)
		return

	@staticmethod
	def generate_menu_item(index):
		return '			{"command": "side_bar_folders_load", "args":{ "index": %d }},' % index

	@staticmethod
	def generate_menu(count):
		folders = get_project_data(Window())['folders']
		menu = os.path.join(sublime.packages_path(), "User", "Side Bar Folders", "Main.sublime-menu")
		try:
			with codecs.open(menu, "w", encoding="utf-8") as f:
				f.write(
					MENU % {
						"entries": '\n'.join([Menu.generate_menu_item(x) for x in range(0, count)])
					}
				)
		except:
			pass

class Pref:
	def load(self):
		win = Window()
		Pref.folders = s.get('folders', [])
		Pref.project_folders = len(get_project_data(win)['folders']) if win is not None else -1

	def reload(self):
		Pref.folders = s.get('folders', [])
		for window in sublime.windows():
			try:
				project_data = get_project_data(window)
				for folder in range(len(project_data['folders'])):
					for k in range(len(Pref.folders)):
						if Pref.folders[k]['path'] == project_data['folders'][folder]['path']:
							project_data['folders'][folder] = Pref.folders[k]
							window.set_project_data(project_data);
			except:
				pass

	def adjust_history(self):
		limit = s.get("history_limit", 0)
		if limit > 0:
			count = len(Pref.folders)
			if count > limit:
				Pref.folders = Pref.folders[-limit:]

	def save(self):
		if s.get('folders', []) != Pref.folders:
			Pref.folders = sorted(Pref.folders, key=lambda x: x['path'].lower(), reverse=True);
			s.set('folders', Pref.folders)
			sublime.save_settings('Side Bar Folders.sublime-settings');
			Menu.generate_menu(len(Pref.folders))

	def save_folders(self):
		for window in sublime.windows():
			try:
				for folder in get_project_data(window)['folders']:
					self.append(folder, window)
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

	def append(self, folder, window):
		folder["path"] = self.normalize_folder(folder["path"], window)
		for k in range(len(Pref.folders)):
			if Pref.folders[k]['path'] == folder['path']:
				Pref.folders[k] = folder
				return
		Pref.folders.append(folder)
		self.adjust_history()

	def bucle(self):
		Pref.save_folders()
		sublime.set_timeout(lambda:Pref.bucle(), 60*1000)

def plugin_loaded():
	global s, Pref
	Menu.prepare_menu()
	s = sublime.load_settings('Side Bar Folders.sublime-settings');
	Pref = Pref()
	Pref.load();
	s.add_on_change('reload', lambda:Pref.reload())
	Pref.bucle()

class side_bar_folders_start_blank(sublime_plugin.WindowCommand):
	def run(self):
		project = get_project_data(Window())
		if not s.get("multi_folder_mode", False):
			project['folders'] = []
			Window().set_project_data(project);
		Window().run_command('prompt_add_folder');

	def is_enabled(self):
		Pref.save_folders() # <--- this works as an onpopupshowing..
		return True

class side_bar_folders_load(sublime_plugin.WindowCommand):
	def run(self, index = -1):
		folder = (Pref.folders[::-1])[index];
		project = get_project_data(Window())
		if not s.get("multi_folder_mode", False):
			project['folders'] = []
		project['folders'].append(folder);
		Window().set_project_data(project);

	def is_visible(self, index = -1):
		try:
			return (Pref.folders[::-1])[index] != None
		except:
			return False

	def description(self, index = -1):
		try:
			return (Pref.folders[::-1])[index]['path']
		except:
			return ''

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
			Window().set_project_data(project);

	def is_visible(self):
		return len(get_project_data(self.window)['folders']) > 0 and s.get("multi_folder_mode", False)

class side_bar_folders_listener(sublime_plugin.EventListener):
	def on_activated(self, view):
		Pref.save_folders()
