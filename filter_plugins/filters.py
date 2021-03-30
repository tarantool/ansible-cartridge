import os


def path_join(parts):
    return os.path.join(*parts)


class FilterModule(object):
    def filters(self):
        return {
            'cartridge_path_join': path_join,
        }
