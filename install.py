# -*- coding: utf-8 -*-
# Created by: CallMeCore

import sys, os

def resource_path(relative_path):
    """ Get the absolute path to the resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)
	
if __name__ == '__main__':
    data_json_path = resource_path('data.json')
    print(data_json_path)
    with open(data_json_path) as f:
        data = f.read()
        print(data)