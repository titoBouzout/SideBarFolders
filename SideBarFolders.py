# coding=utf8
import sublime, sublime_plugin
import os

def Window():
	return sublime.active_window()

s = {}

class Pref:
	def load(self):
		Pref.folders = s.get('folders', [])

	def reload(self):
		Pref.folders = s.get('folders', [])
		for window in sublime.windows():
			try:
				project_data = window.project_data()
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

	def save_folders(self):
		for window in sublime.windows():
			try:
				for folder in window.project_data()['folders']:
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
	s = sublime.load_settings('Side Bar Folders.sublime-settings');
	Pref = Pref()
	Pref.load();
	s.add_on_change('reload', lambda:Pref.reload())
	Pref.bucle()

class side_bar_folders_start_blank(sublime_plugin.WindowCommand):
	def run(self):
		project = Window().project_data()
		project['folders'] = []
		Window().set_project_data(project);
		Window().run_command('prompt_add_folder');

	def is_enabled(self):
		Pref.save_folders() # <--- this works as an onpopupshowing..
		return True

class side_bar_folders_load(sublime_plugin.WindowCommand):
	def run(self, index = -1):
		folder = (Pref.folders[::-1])[index];
		project = Window().project_data()
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