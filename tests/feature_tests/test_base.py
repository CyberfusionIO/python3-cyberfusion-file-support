import os
from typing import Union

import pytest

from cyberfusion.FileSupport import DestinationFileReplacement
from cyberfusion.QueueSupport import Queue


@pytest.mark.parametrize("contents", ["foobar\n", b"foobar"])
def test_destination_file_replacement_not_exists(
    queue: Queue, non_existent_path: str, contents: Union[str, bytes]
) -> None:
    assert not os.path.exists(non_existent_path)

    destination_file_replacement = DestinationFileReplacement(
        queue, contents=contents, destination_file_path=non_existent_path
    )
    destination_file_replacement.add_to_queue()

    queue.process(preview=False)

    assert os.path.exists(non_existent_path)
    assert (
        open(non_existent_path, "rb" if isinstance(contents, bytes) else "r").read()
        == contents
    )
    assert not os.path.exists(destination_file_replacement.tmp_path)


@pytest.mark.parametrize("contents", ["foobar\n", b"foobar"])
def test_destination_file_replacement_exists(
    queue: Queue, existent_path: str, contents: Union[str, bytes]
) -> None:
    assert os.path.exists(existent_path)
    assert open(existent_path, "r").read() != contents

    destination_file_replacement = DestinationFileReplacement(
        queue, contents=contents, destination_file_path=existent_path
    )
    destination_file_replacement.add_to_queue()

    queue.process(preview=False)

    assert (
        open(existent_path, "rb" if isinstance(contents, bytes) else "r").read()
        == contents
    )
    assert not os.path.exists(destination_file_replacement.tmp_path)
