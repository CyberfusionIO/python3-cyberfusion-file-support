import os
import uuid
from pathlib import Path
from typing import Generator

import pytest

from cyberfusion.QueueSupport import Queue


def get_path() -> str:
    """Get path.

    Path is in home directory. This is needed because on macOS, files created
    in /tmp/ are owned by the 'wheel' group, which has GID 0. For several tests,
    this causes unexpected results when they expect that a regular file is owned
    by the creating user.
    """
    return os.path.join(Path.home(), str(uuid.uuid4()))


@pytest.fixture
def queue() -> Queue:
    return Queue()


@pytest.fixture
def non_existent_path() -> str:
    return get_path()


@pytest.fixture
def existent_path() -> Generator[str, None, None]:
    path = get_path()

    with open(path, "w"):
        pass

    yield path

    if os.path.exists(path):
        os.unlink(path)
