import os
import shutil
import errno


def make_folder_or_delete_folder_content(folder):
	import os
	try:
		os.makedirs('my_folder')
	except OSError as e:
		if e.errno != errno.EEXIST:
			raise
	"""deletes all files)"""
	for filename in os.listdir(folder):
		file_path = os.path.join(folder, filename)
		try:
			if os.path.isfile(file_path) or os.path.islink(file_path):
				os.unlink(file_path)
			elif os.path.isdir(file_path):
				shutil.rmtree(file_path)
		except Exception as e:
			print('Failed to delete %s. Reason: %s' % (file_path, e))