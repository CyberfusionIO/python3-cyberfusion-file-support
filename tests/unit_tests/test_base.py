from typing import Generator
from cyberfusion.Common import get_tmp_file
import pytest

from cyberfusion.FileSupport import (
    DestinationFileReplacement,
    _DestinationFile,
    EncryptionProperties,
    encrypt_file,
    DecryptionError,
)
from cyberfusion.QueueSupport import Queue
from cyberfusion.QueueSupport.outcomes import (
    CommandItemRunOutcome,
    CopyItemCopyOutcome,
    UnlinkItemUnlinkOutcome,
)

CONTENTS = "foobar\n"
COMMAND = ["true"]


# _DestinationFile


def test_destination_file_not_exists(non_existent_path: str) -> None:
    assert not _DestinationFile(path=non_existent_path).exists


def test_destination_file_exists(existent_path: Generator[str, None, None]) -> None:
    assert _DestinationFile(path=existent_path).exists


def test_destination_file_not_exists_contents(non_existent_path: str) -> None:
    assert _DestinationFile(path=non_existent_path).contents is None


def test_destination_file_encrypted_contents_failed(
    existent_path: str, encryption_properties: EncryptionProperties
) -> None:
    with pytest.raises(
        DecryptionError,
        match=f"Decrypting the destination file at '{existent_path}' failed. Note that the file must already be encrypted using the specified encryption properties.",
    ):
        _DestinationFile(
            path=existent_path, encryption_properties=encryption_properties
        ).contents


def test_destination_file_exists_contents(
    existent_path: Generator[str, None, None],
) -> None:
    with open(existent_path, "w") as f:
        f.write(CONTENTS)

    assert _DestinationFile(path=existent_path).contents == CONTENTS


# DestinationFileReplacement: contents


def test_destination_file_replacement_raises_contents_without_newline(
    queue: Queue, non_existent_path: str
):
    CONTENTS = "foobar"

    assert not CONTENTS.endswith("\n")

    contents = DestinationFileReplacement(
        queue, contents=CONTENTS, destination_file_path=non_existent_path
    ).contents

    assert contents == CONTENTS + "\n"


def test_destination_file_replacement_not_raises_no_contents_without_newline(
    queue: Queue, non_existent_path: str
):
    DestinationFileReplacement(
        queue, contents="", destination_file_path=non_existent_path
    ).contents


# DestinationFileReplacement: default_comment_character


def test_destination_file_replacement_contents_with_default_comment_character_adds(
    queue: Queue, non_existent_path: str
) -> None:
    assert (
        DestinationFileReplacement(
            queue,
            contents=CONTENTS,
            destination_file_path=non_existent_path,
            default_comment_character="#",
        ).contents
        == f"# Update this file via your management interface.\n# Your changes will be overwritten.\n\n{CONTENTS}"
    )


def test_destination_file_replacement_contents_without_default_comment_character_not_adds(
    queue: Queue, non_existent_path: str
) -> None:
    assert (
        DestinationFileReplacement(
            queue,
            contents=CONTENTS,
            destination_file_path=non_existent_path,
            default_comment_character=None,
        ).contents
        == CONTENTS
    )


# DestinationFileReplacement: write_to_file


def test_destination_file_write_to_file_contents(
    queue: Queue, non_existent_path: Generator[str, None, None]
) -> None:
    PATH = get_tmp_file()

    destination_file_path = DestinationFileReplacement(
        queue, contents=CONTENTS, destination_file_path=non_existent_path
    )

    destination_file_path.write_to_file(PATH)

    assert open(PATH, "r").read() == CONTENTS


# DestinationFileReplacement: changed


def test_destination_file_replacement_changed_when_differences(
    queue: Queue, existent_path: Generator[str, None, None]
) -> None:
    destination_file_replacement = DestinationFileReplacement(
        queue, contents=CONTENTS, destination_file_path=existent_path
    )

    assert destination_file_replacement.destination_file.exists
    assert destination_file_replacement.differences

    assert destination_file_replacement.changed is True


def test_destination_file_replacement_changed_when_new_destination_file(
    queue: Queue, non_existent_path: Generator[str, None, None]
) -> None:
    destination_file_replacement = DestinationFileReplacement(
        queue, contents="", destination_file_path=non_existent_path
    )

    assert not destination_file_replacement.destination_file.exists
    assert not destination_file_replacement.differences

    assert destination_file_replacement.changed is True


def test_destination_file_replacement_not_changed(
    queue: Queue, existent_path: Generator[str, None, None]
) -> None:
    with open(existent_path, "w") as f:
        f.write(CONTENTS)

    destination_file_replacement = DestinationFileReplacement(
        queue, contents=CONTENTS, destination_file_path=existent_path
    )

    assert destination_file_replacement.destination_file.exists
    assert not destination_file_replacement.differences

    assert destination_file_replacement.changed is False


def test_destination_file_replacement_not_changed_when_encrypted(
    queue: Queue,
    non_existent_path: Generator[str, None, None],
    encryption_properties: EncryptionProperties,
) -> None:
    with open(non_existent_path, "wb") as f:
        f.write(encrypt_file(encryption_properties, CONTENTS))

    destination_file_replacement = DestinationFileReplacement(
        queue,
        contents=CONTENTS,
        destination_file_path=non_existent_path,
        encryption_properties=encryption_properties,
    )

    assert destination_file_replacement.destination_file.exists
    assert not destination_file_replacement.differences

    # Contents not changed, yet files are not the same (unencrypted vs encrypted)

    assert destination_file_replacement.changed is False
    assert open(destination_file_replacement.tmp_path, "rb").read() != CONTENTS


# DestinationFileReplacement: differences


def test_destination_file_replacement_differences_when_differences(
    queue: Queue, existent_path: Generator[str, None, None]
) -> None:
    differences = DestinationFileReplacement(
        queue, contents=CONTENTS, destination_file_path=existent_path
    ).differences

    assert differences[2] == "@@ -0,0 +1 @@"
    assert differences[3] == "+foobar"


def test_destination_file_replacement_differences_when_not_differences(
    queue: Queue, existent_path: Generator[str, None, None]
) -> None:
    with open(existent_path, "w") as f:
        f.write(CONTENTS)

    assert (
        DestinationFileReplacement(
            queue, contents=CONTENTS, destination_file_path=existent_path
        ).differences
        == []
    )


def test_destination_file_replacement_differences_when_destination_file_not_exists(
    queue: Queue, non_existent_path: str
) -> None:
    differences = DestinationFileReplacement(
        queue, contents=CONTENTS, destination_file_path=non_existent_path
    ).differences

    assert differences[2] == "@@ -0,0 +1 @@"
    assert differences[3] == "+foobar"


# DestinationFileReplacement: add_to_queue


def test_destination_file_replacement_copy_item_in_queue_when_changed(
    queue: Queue, non_existent_path: str
) -> None:
    class_ = DestinationFileReplacement(
        queue, contents=CONTENTS, destination_file_path=non_existent_path
    )

    assert class_.changed

    class_.add_to_queue()

    outcomes = queue.process(preview=True)

    assert (
        CopyItemCopyOutcome(source=class_.tmp_path, destination=non_existent_path)
        in outcomes
    )


def test_destination_file_replacement_not_copy_item_in_queue_when_not_changed(
    queue: Queue, existent_path: Generator[str, None, None]
) -> None:
    with open(existent_path, "w") as f:
        f.write(CONTENTS)

    class_ = DestinationFileReplacement(
        queue, contents=CONTENTS, destination_file_path=existent_path
    )

    assert not class_.changed

    class_.add_to_queue()

    outcomes = queue.process(preview=True)

    assert (
        CopyItemCopyOutcome(source=class_.tmp_path, destination=existent_path)
        not in outcomes
    )


def test_destination_file_replacement_command_item_in_queue_when_changed(
    queue: Queue, non_existent_path: str
) -> None:
    class_ = DestinationFileReplacement(
        queue,
        contents=CONTENTS,
        destination_file_path=non_existent_path,
        command=COMMAND,
    )

    assert class_.changed

    class_.add_to_queue()

    outcomes = queue.process(preview=True)

    assert CommandItemRunOutcome(command=COMMAND) in outcomes


def test_destination_file_replacement_not_command_item_in_queue_when_not_changed(
    queue: Queue, existent_path: str
) -> None:
    with open(existent_path, "w") as f:
        f.write(CONTENTS)

    class_ = DestinationFileReplacement(
        queue,
        contents=CONTENTS,
        destination_file_path=existent_path,
        command=COMMAND,
    )

    assert not class_.changed

    class_.add_to_queue()

    outcomes = queue.process(preview=True)

    assert CommandItemRunOutcome(command=COMMAND) not in outcomes


def test_destination_file_replacement_not_command_item_in_queue_when_not_command(
    queue: Queue, non_existent_path: str
) -> None:
    class_ = DestinationFileReplacement(
        queue,
        contents=CONTENTS,
        destination_file_path=non_existent_path,
        command=None,
    )

    class_.add_to_queue()

    outcomes = queue.process(preview=True)

    assert not any(isinstance(x, CommandItemRunOutcome) for x in outcomes)


def test_destination_file_replacement_unlink_item_in_queue_when_not_changed(
    queue: Queue, existent_path: str
) -> None:
    with open(existent_path, "w") as f:
        f.write(CONTENTS)

    class_ = DestinationFileReplacement(
        queue,
        contents=CONTENTS,
        destination_file_path=existent_path,
    )

    assert not class_.changed

    class_.add_to_queue()

    assert UnlinkItemUnlinkOutcome(path=class_.tmp_path) in queue.items[0].outcomes
    assert not any(
        isinstance(x, UnlinkItemUnlinkOutcome) for x in queue.process(preview=False)
    )


def test_destination_file_replacement_unlink_item_in_queue_when_changed(
    queue: Queue, non_existent_path: str
) -> None:
    class_ = DestinationFileReplacement(
        queue,
        contents=CONTENTS,
        destination_file_path=non_existent_path,
    )

    assert class_.changed

    class_.add_to_queue()

    assert UnlinkItemUnlinkOutcome(path=class_.tmp_path) in queue.items[1].outcomes
    assert not any(
        isinstance(x, UnlinkItemUnlinkOutcome) for x in queue.process(preview=False)
    )


# DestinationFileReplacement: reference


def test_destination_file_replacement_reference_passed(
    queue: Queue,
    non_existent_path: str,
) -> None:
    REFERENCE = "test"

    destination_file_replacement = DestinationFileReplacement(
        queue,
        contents="test\n",
        destination_file_path=non_existent_path,
        reference=REFERENCE,
    )
    destination_file_replacement.add_to_queue()

    for item in queue.items:
        assert item.reference == REFERENCE
