# coding=utf8
import sublime, sublime_plugin
import os
import codecs

MENU = '''[
	{"caption": "Help", "mnemonic": "H", "id": "help", "children": [] },
	{
		"caption": "Folders",
		"id": "folders",
		"children": [
			{"command": "side_bar_folders_start_blank", "caption": "Load Folder…"},
			{ "caption": "-" },
			// Current open folders go here
%(current_sidebar_folders)s
			{"command": "side_bar_folders_sidebar_clear"},
			{ "caption": "-" },
			{ "command": "open_file", "args": { "file": "${packages}/User/Side Bar Folders.sublime-settings" }, "caption": "Edit Items"},
			{"caption": "-"},
			// Folder history goes here
%(entries)s
			{ "caption": "-" },
			{ "command": "side_bar_folders_clear", "caption": "Clear Items" }
		]
	}
]
'''

def Window():
	return sublime.active_window()

s = {}

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
	def generate_open_folders(index):
		return '			{"command": "side_bar_folders_sidebar_clear", "args":{ "index": %d }},' % index

	@staticmethod
	def generate_menu(count):
		folders = get_project_data(Window())['folders']
		menu = os.path.join(sublime.packages_path(), "User", "Side Bar Folders", "Main.sublime-menu")
		with codecs.open(menu, "w", encoding="utf-8") as f:
			f.write(
				MENU % {
					"current_sidebar_folders": '\n'.join([Menu.generate_open_folders(x) for x in range(0, len(folders))]),
					"entries": '\n'.join([Menu.generate_menu_item(x) for x in range(0, count)])
				}
			)

# when closing a project, project_data returns "None"
def get_project_data(window):
	project_data = window.project_data()
	if project_data is None:
		project_data = {}
		project_data['folders'] = []
	return project_data

class Pref:
	def load(self):
		Pref.folders = s.get('folders', [])

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

	def save(self):
		if s.get('folders', []) != Pref.folders:
			Pref.folders = sorted(Pref.folders, key=lambda x: x['path'].lower(),  reverse=True);
			s.set('folders', Pref.folders)
			sublime.save_settings('Side Bar Folders.sublime-settings');
		Menu.generate_menu(len(Pref.folders))

	def save_folders(self):
		for window in sublime.windows():
			try:
				for folder in get_project_data(window)['folders']:
					self.append(folder)
			except:
				pass
		Pref.save();

	def append(self, folder):
		for k in range(len(Pref.folders)):
			if Pref.folders[k]['path'] == folder['path']:
				Pref.folders[k] = folder
				return
		Pref.folders.append(folder)


	def bucle(self):
		Pref.save_folders();
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
			Pref.save();

class side_bar_folders_sidebar_clear(sublime_plugin.WindowCommand):
	def run(self, index=-1):
		project = get_project_data(Window())
		if index == -1:
			project['folders'] = []
		else:
			del project['folders'][index]
		Window().set_project_data(project);

	def description(self, index=-1):
		desc = "Remove All Sidebar Folders…"
		if index != -1:
			try:
				desc = "Remove %s" % get_project_data(self.window)['folders'][index]['path']
			except:
				desc = ''
		return desc

	def is_visible(self):
		return len(get_project_data(self.window)['folders']) > 0 and s.get("multi_folder_mode", False)
