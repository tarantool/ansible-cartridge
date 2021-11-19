class StatResult:
    def __init__(self, st_mtime=0):
        self.st_mtime = st_mtime


class OsPathExistsMock:
    def __init__(self):
        self.existent_paths = set()

    def __call__(self, path):
        return path in self.existent_paths

    def set_exists(self, path):
        self.existent_paths.add(path)

    def set_not_exists(self, path):
        self.existent_paths.discard(path)


class OsLstatMock:
    def __init__(self):
        self.known_mtimes = dict()

    def __call__(self, path):
        return self.known_mtimes[path]

    def set_m_time(self, path, m_time):
        if not self.known_mtimes.get(path):
            self.known_mtimes[path] = StatResult()
        self.known_mtimes[path].st_mtime = m_time
