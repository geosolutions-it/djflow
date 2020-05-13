import sys


class Tee:
    """
    Class duplicating stdout and stderr to a specified log file and
    """

    def __init__(self, name, mode):
        self.file_name = name
        self.mode = mode
        self.file = None

        self.stdout = sys.stdout
        self.stderr = sys.stderr

        sys.stdout = self
        sys.stderr = self

    def write(self, data):

        self.file.write(data)
        self.stdout.write(data)

    def flush(self):
        self.file.flush()

    def __enter__(self):
        self.file = open(self.file_name, self.mode)

    def __exit__(self, _type, _value, _traceback):
        sys.stdout = self.stdout
        sys.stderr = self.stderr
        self.file.close()
