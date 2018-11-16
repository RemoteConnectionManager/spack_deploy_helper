import os
import uuid


class WorkspaceManager():
    def __init__(self, path):
        self.base_path = path

    def create(self):
        uuid_ = uuid.uuid4()
        path = os.path.join(self.base_path, str(uuid_))
        os.mkdir(path)
        print('Created a new workspace in: ' + path)
        return uuid

    def list(self):
        print('The current workspaces are:')
        for root, dirs, files in os.walk(self.base_path, topdown=False):
            for name in dirs:
                print(" * " + name)

    def remove(self, uuid_):
        path = os.path.join(self.base_path, str(uuid_))
        try:
            os.rmdir(path)
        except OSError:
            print('error: failed to remove the directory ' + path)