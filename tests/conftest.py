import os
from cyberfusion.Common import get_tmp_file
import subprocess
import uuid
from pathlib import Path
from typing import Generator

import pytest

from cyberfusion.QueueSupport import Queue

from cyberfusion.FileSupport import EncryptionProperties
from cyberfusion.FileSupport.encryption import MessageDigestEnum


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


@pytest.fixture
def encryption_password() -> str:
    return subprocess.check_output(["openssl", "rand", "-hex", "128"]).decode()


@pytest.fixture
def encryption_password_file_path(
    encryption_password: str,
) -> Generator[str, None, None]:
    tmp_file = get_tmp_file()

    with open(tmp_file, "w") as f:
        f.write(encryption_password)

    yield tmp_file

    os.unlink(tmp_file)


@pytest.fixture
def encryption_properties(
    encryption_password: str, encryption_password_file_path: str
) -> EncryptionProperties:
    return EncryptionProperties(
        cipher_name="aes-256-cbc",
        message_digest=MessageDigestEnum.SHA1,
        password_file_path=encryption_password_file_path,
    )
