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
		"children": [
			{ "caption": "-" , "id": "open" },
			{ "command": "side_bar_folders_start_blank", "caption": "Load Folder…"},
			{ "command": "side_bar_folders_start_blank", "caption": "Append Folder…", "args": {"append": true}},
			{ "command": "side_bar_folders_sidebar_clear", "caption": "Clear"},
			{ "caption": "-", "id": "edit" },
			{ "command": "open_file", "args": { "file": "${packages}/User/Side Bar Folders.sublime-settings" }, "caption": "Edit"},
			{ "caption": "-" , "id": "history" },
			{
				"caption": "%(buried_label)s",
				"children": [
					// Folder history goes here
%(buried_entries)s
				]
			},
			// Folder history goes here
%(entries)s
			{ "caption": "-" , "id": "options" },
			{ "command": "side_bar_folders_swap", "caption": "Swap Append/Load"},
			{ "caption": "-" , "id": "end" },
		]
	}
]
'''

FOLDER_ENTRY = '%(indent)s{"command": "side_bar_folders_load", "args":{ "index": %(index)d%(append)s }},'


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
		Pref.history = s.get('history_limit', 66)
		Pref.swap = s.get("swap_append_load", False)

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
				if Pref.swap != s.get("swap_append_load", False):
					# Re-generate menu with new swap preference
					Pref.swap = s.get("swap_append_load", False)
					Menu.generate_menu(len(Pref.folders))
				if Pref.history != s.get('history_limit', 66):
					# Set new limit and re-save making adjustments to history list
					Pref.history = s.get('history_limit', 66)
					self.save()
			except:
				pass

	def adjust_history(self):
		limit = Pref.history
		if limit > 0:
			count = len(Pref.folders)
			if count > limit:
				Pref.folders = Pref.folders[-limit:]

	def save(self):
		self.adjust_history()
		if s.get('folders', []) != Pref.folders:
			Pref.folders = sorted(Pref.folders, key=lambda x: x['path'].lower(), reverse=True)
			s.set('folders', Pref.folders)
			sublime.save_settings('Side Bar Folders.sublime-settings')
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

	def display_name(self, folder):
		home = os.path.expanduser("~")
		display = folder
		if folder.startswith(home):
			display = folder.replace(home, "~", 1)
		if len(display) > 51:
			display = display[:25] + "…" + display[-25:]
		return display

	def append(self, folder, window):
		if len(Pref.folders) >= Pref.history:
			return
		folder["path"] = self.normalize_folder(folder["path"], window)
		folder["display"] = self.display_name(folder["path"])
		for k in range(len(Pref.folders)):
			if Pref.folders[k]['path'] == folder['path']:
				Pref.folders[k] = folder
				return
		Pref.folders.append(folder)

	def bucle(self):
		Pref.save_folders()
		sublime.set_timeout(lambda:Pref.bucle(), 60*1000)

def plugin_loaded():
	global s, Pref
	s = sublime.load_settings('Side Bar Folders.sublime-settings');
	Pref = Pref()
	Pref.load();
	s.add_on_change('reload', lambda:Pref.reload())
	Menu.prepare_menu()
	Pref.bucle()

class side_bar_folders_start_blank(sublime_plugin.WindowCommand):
	def run(self, append = False):
		project = get_project_data(Window())
		if not append:
			project['folders'] = []
			Window().set_project_data(project);
		Window().run_command('prompt_add_folder');

	def is_enabled(self, append = False):
		Pref.save_folders() # <--- this works as an onpopupshowing..
		return True

class side_bar_folders_load(sublime_plugin.WindowCommand):
	def run(self, index =- 1, append = False):
		folder = (Pref.folders[::-1])[index];
		if self.audit_folder(folder, index):
			return
		project = get_project_data(Window())
		if not append:
			project['folders'] = []
		try:
			del folder["display"]
		except:
			pass
		project['folders'].append(folder)
		Window().set_project_data(project)

	def audit_folder(self, folder, index):
		abort = False
		if not os.path.exists(folder['path']):
			if sublime.ok_cancel_dialog('Folder does not currently exist! Do you want to remove the folder from the history?'):
				folders = s.get("folders", [])
				if index < len(folders):
					del folders[len(folders) - index - 1]
					s.set("folders", folders)
					sublime.save_settings('Side Bar Folders.sublime-settings')
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
			return item.get("display", item["path"])
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
			Window().set_project_data(project)

	def is_visible(self):
		return len(get_project_data(self.window)['folders']) > 0

class side_bar_folders_listener(sublime_plugin.EventListener):
	def on_activated(self, view):
		Pref.save_folders()

class side_bar_folders_swap(sublime_plugin.WindowCommand):
	def run(self):
		current_swap = s.get("swap_append_load", False)
		s.set("swap_append_load", not current_swap)
		sublime.save_settings('Side Bar Folders.sublime-settings')

	def is_checked(self):
		return s.get("swap_append_load", False)
