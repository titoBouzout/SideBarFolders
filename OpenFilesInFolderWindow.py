# coding=utf8
import sublime, sublime_plugin
import os.path as op

def normalize(path):
	return op.normcase(op.normpath(op.realpath(path)))

class open_files_in_folder_window_listener(sublime_plugin.EventListener):
	def on_load(self, view):
		if view.file_name():
			window = view.window()
			windows = sublime.windows()
			transient = window is None
			if transient or len(windows) == 1:
				pass
			elif sublime.load_settings('Side Bar Folders.sublime-settings').get('open_files_in_folder_window', False):
				path = normalize(view.file_name())
				folders = window.folders()
				for item in folders:
					if path.startswith(normalize(item)): # already in best window
						return
				for _window in sublime.windows():
					if _window.id() != window.id():
						folders = _window.folders()
						for item in folders:
							if path.startswith(normalize(item)): # moving to best window
								window.run_command('close')
								_view = _window.open_file(path)
								self.focus_view(_view)
								return

	def focus_view(self, view):
		window = view.window()
		window.focus_view(view)
		window.run_command('focus_neighboring_group')
		window.focus_view(view)
