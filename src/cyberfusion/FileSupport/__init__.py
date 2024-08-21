"""Classes for files."""

import difflib
import filecmp
import os
from typing import List, Optional, Union

from cyberfusion.Common import get_tmp_file
from cyberfusion.QueueSupport import Queue
from cyberfusion.QueueSupport.items.command import CommandItem
from cyberfusion.QueueSupport.items.copy import CopyItem
from cyberfusion.QueueSupport.items.unlink import UnlinkItem


class _DestinationFile:
    """Represents destination file."""

    def __init__(self, *, path: str) -> None:
        """Set attributes."""
        self.path = path

    @property
    def exists(self) -> bool:
        """Get if exists."""
        return os.path.exists(self.path)

    @property
    def contents(self) -> Optional[str]:
        """Get contents."""
        if self.exists:
            with open(self.path, "r") as f:
                return f.read()

        return None


class DestinationFileReplacement:
    """Represents file that will replace destination file."""

    def __init__(
        self,
        queue: Queue,
        *,
        contents: Union[str, bytes],
        destination_file_path: str,
        default_comment_character: Optional[str] = None,
        command: Optional[List[str]] = None,
        reference: Optional[str] = None,
    ) -> None:
        """Set attributes.

        'default_comment_character' has no effect when 'contents' is not string.
        """
        self.queue = queue
        self._contents = contents
        self.default_comment_character = default_comment_character
        self.command = command
        self.reference = reference

        self.tmp_path = get_tmp_file()
        self.destination_file = _DestinationFile(path=destination_file_path)

        self._write_to_tmp_file()

    @property
    def contents(self) -> Union[str, bytes]:
        """Get contents."""
        if not isinstance(self._contents, str):
            return self._contents

        if self._contents != "" and not self._contents.endswith(
            "\n"
        ):  # Some programs require newline to consider last line completed
            raise ValueError

        if not self.default_comment_character:
            return self._contents

        default_comment = f"{self.default_comment_character} Update this file via your management interface.\n"
        default_comment += f"{self.default_comment_character} Your changes will be overwritten.\n"
        default_comment += "\n"

        return default_comment + self._contents

    def _write_to_tmp_file(self) -> None:
        """Write contents to tmp file."""
        if isinstance(self.contents, bytes):
            open_mode = "wb"
        else:
            open_mode = "w"

        with open(self.tmp_path, open_mode) as f:
            f.write(self.contents)

    @property
    def changed(self) -> bool:
        """Get if destination file will change."""
        return not self.destination_file.exists or not filecmp.cmp(
            self.tmp_path, self.destination_file.path
        )

    @property
    def differences(self) -> List[str]:
        """Get differences with destination file.

        No differences are returned when contents is not string.
        """
        if not isinstance(self._contents, str):
            return []

        results = []

        for line in difflib.unified_diff(
            (
                self.destination_file.contents.splitlines()
                if self.destination_file.contents
                else []
            ),
            self.contents.splitlines(),  # type: ignore[arg-type]
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
                    CommandItem(
                        command=self.command, reference=self.reference
                    ),
                )

        self.queue.add(
            UnlinkItem(
                path=self.tmp_path,
                hide_outcomes=True,
                reference=self.reference,
            ),
        )
