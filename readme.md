# SideBar Folders

### Description

Provides a new item "Folders" in the menubar, to allow a quick switch of the folders opened in the sidebar; for Sublime Text. See: http://www.sublimetext.com/

For some users.. (me :P), the ST project system is too much.. I just want to be able to switch folders without saving or tracking project files, and keeping Tabs intact.. well, this package does just that.

The menuitem fills up automatically, you don't need to do anything.

Aditionally you may enable "open_files_in_folder_window" which gonna move any file you open to the windows that has a folder with that path.

### Installation

Download or clone the contents of this repository to a folder named exactly as the package name into the Packages/ folder of ST.

### Keyboard Shortcuts

You may add the following shortcut to your `Default.sublime-keymap` to list the folders in a quick panel. With this you can quickly change folders from the keyboard.

	[
		{ "keys": ["super+shift+o"], "command": "side_bar_folders_quick_switch" }
	]

### Contributors

@titoBouzout
@facelessuser
@Jainil
