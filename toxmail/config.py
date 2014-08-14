# dynamic config
import json
import os


class Config(dict):
    def __init__(self, path):
        self.path = path
        self.load()

    def load(self):
        if os.path.exists(self.path):
            with open(self.path) as f:
                content = f.read()
                self.update(json.loads(content))

    def save(self):
        data = json.dumps(self, indent=4, sort_keys=True)
        with open(self.path, 'w') as f:
            f.write(data)
