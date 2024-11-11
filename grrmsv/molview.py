import subprocess

from grrmsv.structure import Structure
from grrmsv.utils import tostring, get_temp_file_name

import config


def show_single_xyz(xyz_file: str):
    subprocess.Popen([config.VIEWER_PATH, xyz_file])


def show_multi_xyz(xyz_file: str):
    subprocess.Popen([config.VIEWER_PATH, xyz_file])


def show_structure(structure: Structure, name: str='temp.xyz'):
    prefix = name.rstrip('.xyz')
    file = get_temp_file_name(prefix=prefix, suffix='.xyz')
    structure.save_xyz_file(file, title=tostring(structure.name).replace('\n', ' '))
    show_single_xyz(file)
