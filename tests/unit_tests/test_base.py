from typing import Generator
from cyberfusion.Common import get_tmp_file
import pytest
from cyberfusion.QueueSupport.items.copy import CopyItem

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
    UnlinkItemUnlinkOutcome,
)

CONTENTS = "foobar\n"
COMMAND = ["true"]


# _DestinationFile


def test_destination_file_not_exists_decrypt(non_existent_path: str) -> None:
    assert _DestinationFile(path=non_existent_path).decrypt() is None


def test_destination_file_exists_no_encryption_properties_decrypt(
    existent_path: Generator[str, None, None],
) -> None:
    assert _DestinationFile(path=existent_path).decrypt() is None


def test_destination_file_encrypted_contents_failed(
    existent_path: str, encryption_properties: EncryptionProperties
) -> None:
    with pytest.raises(
        DecryptionError,
        match=f"Decrypting the destination file at '{existent_path}' failed. Note that the file must already be encrypted using the specified encryption properties.",
    ):
        _DestinationFile(
            path=existent_path, encryption_properties=encryption_properties
        ).decrypt()


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


def test_destination_file_replacement_not_changed_when_encrypted_not_changed(
    queue: Queue,
    non_existent_path: Generator[str, None, None],
    encryption_properties: EncryptionProperties,
) -> None:
    with open(non_existent_path, "wb") as f:
        f.write(encrypt_file(encryption_properties, CONTENTS))

    assert not DestinationFileReplacement(
        queue,
        contents=CONTENTS,
        destination_file_path=non_existent_path,
        encryption_properties=encryption_properties,
    ).changed


def test_destination_file_replacement_changed_when_encrypted_changed(
    queue: Queue,
    non_existent_path: Generator[str, None, None],
    encryption_properties: EncryptionProperties,
) -> None:
    with open(non_existent_path, "wb") as f:
        f.write(encrypt_file(encryption_properties, CONTENTS + "-example"))

    assert DestinationFileReplacement(
        queue,
        contents=CONTENTS,
        destination_file_path=non_existent_path,
        encryption_properties=encryption_properties,
    ).changed


def test_destination_file_replacement_changed_when_changed(
    queue: Queue, non_existent_path: str
) -> None:
    assert DestinationFileReplacement(
        queue, contents=CONTENTS, destination_file_path=non_existent_path
    ).changed


def test_destination_file_replacement_not_changed_when_not_changed(
    queue: Queue, existent_path: Generator[str, None, None]
) -> None:
    with open(existent_path, "w") as f:
        f.write(CONTENTS)

    assert not DestinationFileReplacement(
        queue, contents=CONTENTS, destination_file_path=existent_path
    ).changed


# DestinationFileReplacement: add_to_queue


def test_destination_file_replacement_not_copy_item_in_queue_when_encrypted_not_changed(
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

    destination_file_replacement.add_to_queue()

    assert not any(
        isinstance(item_mapping.item, CopyItem) for item_mapping in queue.item_mappings
    )

    # Contents not changed, yet files are not the same (unencrypted vs encrypted)

    assert open(destination_file_replacement.tmp_path, "rb").read() != CONTENTS


def test_destination_file_replacement_not_command_item_in_queue_when_encrypted_not_changed(
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
        command=COMMAND,
    )

    destination_file_replacement.add_to_queue()

    _, outcomes = queue.process(preview=True)

    assert CommandItemRunOutcome(command=COMMAND) not in outcomes


def test_destination_file_replacement_copy_item_in_queue_when_encrypted_changed(
    queue: Queue,
    non_existent_path: Generator[str, None, None],
    encryption_properties: EncryptionProperties,
) -> None:
    with open(non_existent_path, "wb") as f:
        f.write(encrypt_file(encryption_properties, CONTENTS + "-example"))

    DestinationFileReplacement(
        queue,
        contents=CONTENTS,
        destination_file_path=non_existent_path,
        encryption_properties=encryption_properties,
    ).add_to_queue()

    assert any(
        isinstance(item_mapping.item, CopyItem) for item_mapping in queue.item_mappings
    )


def test_destination_file_replacement_command_item_in_queue_when_encrypted_changed(
    queue: Queue,
    non_existent_path: Generator[str, None, None],
    encryption_properties: EncryptionProperties,
) -> None:
    with open(non_existent_path, "wb") as f:
        f.write(encrypt_file(encryption_properties, CONTENTS + "-example"))

    DestinationFileReplacement(
        queue,
        contents=CONTENTS,
        destination_file_path=non_existent_path,
        encryption_properties=encryption_properties,
        command=COMMAND,
    ).add_to_queue()

    _, outcomes = queue.process(preview=True)

    assert CommandItemRunOutcome(command=COMMAND) in outcomes


def test_destination_file_replacement_copy_item_in_queue_when_changed(
    queue: Queue, non_existent_path: str
) -> None:
    class_ = DestinationFileReplacement(
        queue, contents=CONTENTS, destination_file_path=non_existent_path
    )

    class_.add_to_queue()

    assert (
        len(
            [
                item_mapping.item
                for item_mapping in queue.item_mappings
                if isinstance(item_mapping.item, CopyItem)
            ]
        )
        == 1
    )


def test_destination_file_replacement_copy_item_in_queue_when_not_changed(
    queue: Queue, existent_path: Generator[str, None, None]
) -> None:
    with open(existent_path, "w") as f:
        f.write(CONTENTS)

    class_ = DestinationFileReplacement(
        queue, contents=CONTENTS, destination_file_path=existent_path
    )

    class_.add_to_queue()

    assert (
        len(
            [
                item_mapping.item
                for item_mapping in queue.item_mappings
                if isinstance(item_mapping.item, CopyItem)
            ]
        )
        == 1
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

    class_.add_to_queue()

    _, outcomes = queue.process(preview=True)

    assert CommandItemRunOutcome(command=COMMAND) in outcomes


def test_destination_file_replacement_not_command_item_in_queue_when_no_outcomes_no_encryption_properties(
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

    class_.add_to_queue()

    _, outcomes = queue.process(preview=True)

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

    _, outcomes = queue.process(preview=True)

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

    class_.add_to_queue()

    assert (
        UnlinkItemUnlinkOutcome(path=class_.tmp_path)
        in queue.item_mappings[1].item.outcomes
    )

    _, outcomes = queue.process(preview=False)

    assert not any(isinstance(x, UnlinkItemUnlinkOutcome) for x in outcomes)


def test_destination_file_replacement_unlink_item_in_queue_when_changed(
    queue: Queue, non_existent_path: str
) -> None:
    class_ = DestinationFileReplacement(
        queue,
        contents=CONTENTS,
        destination_file_path=non_existent_path,
    )

    class_.add_to_queue()

    assert (
        UnlinkItemUnlinkOutcome(path=class_.tmp_path)
        in queue.item_mappings[1].item.outcomes
    )

    _, outcomes = queue.process(preview=False)

    assert not any(isinstance(x, UnlinkItemUnlinkOutcome) for x in outcomes)


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

    for item_mapping in queue.item_mappings:
        assert item_mapping.item.reference == REFERENCE
