"""Classes for files."""

import os

from typing import List, Optional, Union

from cyberfusion.Common import get_tmp_file
from cyberfusion.QueueSupport import Queue
from cyberfusion.QueueSupport.items.command import CommandItem
from cyberfusion.QueueSupport.items.copy import CopyItem
from cyberfusion.QueueSupport.items.unlink import UnlinkItem

from cyberfusion.FileSupport.encryption import (
    EncryptionProperties,
    encrypt_file,
    decrypt_file,
)
from cyberfusion.FileSupport.exceptions import DecryptionError


class _DestinationFile:
    """Represents destination file."""

    def __init__(
        self, *, path: str, encryption_properties: Optional[EncryptionProperties] = None
    ) -> None:
        """Set attributes.

        If 'encryption_properties' is specified, and the destination file already
        exists, it must be encrypted using the same properties (it is decrypted).
        """
        self.path = path
        self.encryption_properties = encryption_properties

    @property
    def _exists(self) -> bool:
        """Get if exists."""
        return os.path.exists(self.path)

    def decrypt(self) -> Optional[str]:
        """Decrypt file."""
        if not self._exists or not self.encryption_properties:
            return None

        try:
            return decrypt_file(self.encryption_properties, self.path)
        except DecryptionError as e:
            raise DecryptionError(
                f"Decrypting the destination file at '{self.path}' failed. Note that the file must already be encrypted using the specified encryption properties."
            ) from e


class DestinationFileReplacement:
    """Represents file that will replace destination file."""

    def __init__(
        self,
        queue: Queue,
        *,
        contents: str,
        destination_file_path: str,
        default_comment_character: Optional[str] = None,
        command: Optional[List[str]] = None,
        reference: Optional[str] = None,
        encryption_properties: Optional[EncryptionProperties] = None,
    ) -> None:
        """Set attributes.

        'default_comment_character' has no effect when 'contents' is not string.

        If 'encryption_properties' is specified, and the destination file already
        exists, it must be encrypted using the same properties (it is decrypted).
        """
        self.queue = queue
        self._contents = contents
        self.default_comment_character = default_comment_character
        self.command = command
        self.reference = reference
        self.encryption_properties = encryption_properties

        self.tmp_path = get_tmp_file()
        self.destination_file = _DestinationFile(
            path=destination_file_path, encryption_properties=encryption_properties
        )

        self.write_to_file(self.tmp_path)

    @property
    def contents(self) -> str:
        """Get contents."""
        if self._contents != "" and not self._contents.endswith(
            "\n"
        ):  # Some programs require EOL
            self._contents += "\n"

        if not self.default_comment_character:
            return self._contents

        default_comment = f"{self.default_comment_character} Update this file via your management interface.\n"
        default_comment += (
            f"{self.default_comment_character} Your changes will be overwritten.\n"
        )
        default_comment += "\n"

        return default_comment + self._contents

    def write_to_file(self, path: str) -> None:
        """Write contents to file."""
        contents: Union[str, bytes]

        if self.encryption_properties:
            open_mode = "wb"

            contents = encrypt_file(
                self.encryption_properties,
                self.contents,
            )
        else:
            open_mode = "w"

            contents = self.contents

        with open(path, open_mode) as f:
            f.write(contents)

    def add_to_queue(self) -> None:
        """Add items for replacement to queue."""
        add_copy_item = True

        decrypted_contents = self.destination_file.decrypt()

        # If encrypted, only add CopyItem when unencrypted contents changed.
        # CopyItem does not account for encryption, so without this check the
        # file would always be copied.

        if decrypted_contents:
            add_copy_item = decrypted_contents != self.contents

        # Copy and unlink instead of move. MoveItem copies metadata (which
        # means mode etc. of destination file is incorrect, as set to the tmp
        # file until corrected by later queue items). CopyItem does not copy
        # metadata, so if the destination file already exists, its mode etc.
        # is unchanged.

        if add_copy_item:
            copy_item = CopyItem(
                source=self.tmp_path,
                destination=self.destination_file.path,
                reference=self.reference,
            )

            self.queue.add(copy_item)

            if self.command and copy_item.outcomes:
                self.queue.add(
                    CommandItem(command=self.command, reference=self.reference),
                )

        self.queue.add(
            UnlinkItem(
                path=self.tmp_path,
                hide_outcomes=True,
                reference=self.reference,
            ),
        )
