import os

import pytest

from cyberfusion.FileSupport import (
    DestinationFileReplacement,
    EncryptionProperties,
    decrypt_file,
)
from cyberfusion.QueueSupport import Queue


@pytest.mark.parametrize(
    "contents",
    [
        "foobar\n",
    ],
)
def test_destination_file_replacement_not_exists(
    queue: Queue, non_existent_path: str, contents: str
) -> None:
    assert not os.path.exists(non_existent_path)

    destination_file_replacement = DestinationFileReplacement(
        queue, contents=contents, destination_file_path=non_existent_path
    )
    destination_file_replacement.add_to_queue()

    queue.process(preview=False)

    assert os.path.exists(non_existent_path)
    assert open(non_existent_path, "r").read() == contents
    assert not os.path.exists(destination_file_replacement.tmp_path)


@pytest.mark.parametrize(
    "contents",
    [
        "foobar\n",
    ],
)
def test_destination_file_replacement_exists(
    queue: Queue, existent_path: str, contents: str
) -> None:
    assert os.path.exists(existent_path)
    assert open(existent_path, "r").read() != contents

    destination_file_replacement = DestinationFileReplacement(
        queue, contents=contents, destination_file_path=existent_path
    )
    destination_file_replacement.add_to_queue()

    queue.process(preview=False)

    assert open(existent_path, "r").read() == contents
    assert not os.path.exists(destination_file_replacement.tmp_path)


def test_destination_file_encrypted(
    queue: Queue, non_existent_path: str, encryption_properties: EncryptionProperties
) -> None:
    CONTENTS = "foobar\n"

    destination_file_replacement = DestinationFileReplacement(
        queue,
        contents=CONTENTS,
        destination_file_path=non_existent_path,
        encryption_properties=encryption_properties,
    )

    assert (
        decrypt_file(encryption_properties, destination_file_replacement.tmp_path)
        == CONTENTS
    )
