from pathlib import Path
import shutil
import uuid

ROOT = Path(__file__).resolve().parents[1]
TEST_TMP = ROOT / "data" / "local" / "test-tmp"


class _TempDir:
    def __init__(self):
        TEST_TMP.mkdir(parents=True, exist_ok=True)
        self.name = str(TEST_TMP / ("case-" + uuid.uuid4().hex))
        Path(self.name).mkdir()

    def cleanup(self):
        shutil.rmtree(self.name, ignore_errors=True)

    def __enter__(self):
        return self.name

    def __exit__(self, exc_type, exc, tb):
        self.cleanup()
        return False


def temporary_directory():
    return _TempDir()
