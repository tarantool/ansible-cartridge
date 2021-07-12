import os


def path_join(parts):
    return os.path.join(*parts)


def add_trailing_slash(path):
    if path.endswith(os.path.sep):
        return path

    return path + os.path.sep


class FilterModule(object):
    def filters(self):
        return {
            'cartridge_path_join': path_join,
            'cartridge_add_trailing_slash': add_trailing_slash,
        }
