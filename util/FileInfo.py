#!/usr/bin/env python
import platform
import os
import stat
import sys


os_type = platform.system()

def _get_mode_info(mode, filename):
    perms = '-'
    type = 'F'
    link = ''
    if stat.S_ISDIR(mode):
        perms = 'd'
        type = 'D'
    elif stat.S_ISLNK(mode):
        perms = 'l'
        type = 'L'
        link = os.readlink(filename)
    mode = stat.S_IMODE(mode)
    for who in 'USR', 'GRP', 'OTH':
        for what in 'R', 'W', 'X':
            if mode & getattr(stat, 'S_I' + what + who):
                perms = perms + what.lower()
            else:
                perms = perms + '-'
    return perms, type, link


def get_file_info(path='.', include_current_and_parent_dir=False):
    dict_file_info = []
    files=os.listdir(path)
    files.sort()
    if include_current_and_parent_dir:
        files = ['.', '..'] + files
    for name in files:
        full_path = os.path.join(path, name)
        try:
            stat_info = os.lstat(full_path)
        except:
            sys.stderr.write('%s: No such file or directory\n' % full_path)
            continue
        permissions, type_name, link_name = _get_mode_info(stat_info.st_mode, full_path)
        num_of_link = stat_info.st_nlink
        size = stat_info.st_size
        last_mtime = int(stat_info.st_mtime)
        user = None
        group = None
        if os_type == 'Linux':
            import pwd, grp
            try:
                user = pwd.getpwuid(stat_info.st_uid)[0]
            except KeyError:
                user = stat_info.st_uid
            try:
                group = grp.getgrgid(stat_info.st_gid)[0]
            except KeyError:
                group = stat_info.st_gid
        dict_file_info.append({
            'name': name,
            'type': type_name,
            'size': size,
            'user': user,
            'group': group,
            'perm': permissions,
            'nlink': num_of_link,
            'mtime': last_mtime,
            'link': link_name})
    sorted_file_info = sorted(dict_file_info, key=lambda file_info:(file_info['type'], file_info['name']))
    return sorted_file_info
