"""Classes for files."""

import difflib

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
    def exists(self) -> bool:
        """Get if exists."""
        return os.path.exists(self.path)

    @property
    def contents(self) -> Optional[str]:
        """Get contents."""
        if not self.exists:
            return None

        if not self.encryption_properties:
            with open(self.path, "r") as f:
                return f.read()

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
        ):  # Some programs require newline to consider last line completed
            raise ValueError

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

    @property
    def changed(self) -> bool:
        """Get if destination file will change."""
        if not self.destination_file.exists:
            return True

        return self.destination_file.contents != self.contents

    @property
    def differences(self) -> List[str]:
        """Get differences with destination file.

        No differences are returned when contents is not string.
        """
        results = []

        for line in difflib.unified_diff(
            (
                self.destination_file.contents.splitlines()
                if self.destination_file.contents
                else []
            ),
            self.contents.splitlines(),
            fromfile=self.tmp_path,
            tofile=self.destination_file.path,
            lineterm="",
            n=0,
        ):
            results.append(line)

        return results

    def add_to_queue(self) -> None:
        """Add items for replacement to queue."""
        if self.changed:
            # Copy when changed and always unlink, instead of move when changed
            # and unlink when changed. MoveItem copies metadata (which means
            # mode etc. of destination file is incorrect, as set to the tmp file
            # until corrected by later queue items). CopyItem does not copy
            # metadata, so if the destination file already exists, its mode
            # etc. is unchanged.

            self.queue.add(
                CopyItem(
                    source=self.tmp_path,
                    destination=self.destination_file.path,
                    reference=self.reference,
                ),
            )

            if self.command:
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
