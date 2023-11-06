class StaticTracker:
    def __init__(self):
        self.bbox = None

    def init(self, _, bbox):
        self.bbox = bbox

    def update(self, _):
        return True, self.bbox
