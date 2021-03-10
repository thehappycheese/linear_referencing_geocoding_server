import os
import shutil


def delete_folder_content(folder):
	"""deletes all files in a folder. creates the folder first if it does not exist."""
	if not os.path.exists(folder):
		os.mkdir(folder)
	for filename in os.listdir(folder):
		file_path = os.path.join(folder, filename)
		try:
			if os.path.isfile(file_path) or os.path.islink(file_path):
				os.unlink(file_path)
			elif os.path.isdir(file_path):
				shutil.rmtree(file_path)
		except Exception as e:
			print('Failed to delete %s. Reason: %s' % (file_path, e))