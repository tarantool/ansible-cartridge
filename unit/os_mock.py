class OsPathExistsMock:
    def __init__(self):
        self.existent_paths = set()

    def __call__(self, path):
        return path in self.existent_paths

    def set_exists(self, path):
        self.existent_paths.add(path)

    def set_not_exists(self, path):
        self.existent_paths.discard(path)


class OsPathGetMTimeMock:
    def __init__(self):
        self.known_mtimes = dict()

    def __call__(self, path):
        return self.known_mtimes[path]

    def set_m_time(self, path, m_time):
        self.known_mtimes.update({path: m_time})
