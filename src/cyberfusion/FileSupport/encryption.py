"""Utilities for file encryption."""

import subprocess
from dataclasses import dataclass
from enum import Enum

from cyberfusion.FileSupport.exceptions import EncryptionError, DecryptionError


class MessageDigestEnum(str, Enum):
    """Message digests supported by OpenSSL."""

    MD2 = "md2"
    MD5 = "md5"
    SHA = "sha"
    SHA1 = "sha1"


@dataclass
class EncryptionProperties:
    """Properties to encrypt files, needed by OpenSSL."""

    cipher_name: str  # Get options with `openssl list -cipher-algorithms`
    message_digest: MessageDigestEnum
    password_file_path: str  # Create password with `openssl rand -hex 128`


def encrypt_file(encryption_properties: EncryptionProperties, contents: str) -> bytes:
    """Get contents for file to encrypt."""
    try:
        return subprocess.check_output(
            [
                "openssl",
                "enc",
                "-" + encryption_properties.cipher_name,
                "-md",
                encryption_properties.message_digest,
                "-pass",
                "file:" + encryption_properties.password_file_path,
            ],
            input=contents.encode(),
        )
    except subprocess.CalledProcessError as e:
        raise EncryptionError from e


def decrypt_file(encryption_properties: EncryptionProperties, path: str) -> str:
    """Get contents of encrypted file."""
    try:
        return subprocess.check_output(
            [
                "openssl",
                "enc",
                "-d",
                "-" + encryption_properties.cipher_name,
                "-md",
                encryption_properties.message_digest,
                "-pass",
                "file:" + encryption_properties.password_file_path,
                "-in",
                path,
            ]
        ).decode()
    except subprocess.CalledProcessError as e:
        raise DecryptionError from e
