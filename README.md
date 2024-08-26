# python3-cyberfusion-file-support

Library for idempotent writing to files.

# Install

## PyPI

Run the following command to install the package from PyPI:

    pip3 install python3-cyberfusion-file-support

## Debian

Run the following commands to build a Debian package:

    mk-build-deps -i -t 'apt -o Debug::pkgProblemResolver=yes --no-install-recommends -y'
    dpkg-buildpackage -us -uc

# Configure

No configuration is supported.

# Usage

## Example

```python
from cyberfusion.QueueSupport import Queue
from cyberfusion.FileSupport import DestinationFileReplacement

queue = Queue()

tmp_file = DestinationFileReplacement(
    queue,
    contents="foobar",
    destination_file_path="/tmp/foobar.txt",
    default_comment_character=None,
    command=["true"],
)

print(tmp_file.differences)

tmp_file.add_copy_to_queue()

queue.process(preview=...)
```
