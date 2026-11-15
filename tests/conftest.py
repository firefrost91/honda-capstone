import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def pytest_configure(config):
    config.addinivalue_line("markers", "index: needs a built index and the embedding model")
    config.addinivalue_line("markers", "llm: runs the language model (slow)")
