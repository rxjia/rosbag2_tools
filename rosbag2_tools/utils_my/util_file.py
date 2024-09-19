import os
import re


def detect_walk_file(dir_path, rematch=None):
    """ example: rematch=r'.*\.json$' """
    l_files = []
    for root, dirs, files in os.walk(dir_path):
        if rematch is None:
            json_fnames = [os.path.join(root, fname) for fname in files]
        else:
            json_fnames = [os.path.join(root, fname) for fname in files if re.match(rematch, fname)]
        l_files.extend(json_fnames)
    l_files.sort()
    return l_files