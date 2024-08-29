import pytest

from cyberfusion.FileSupport import EncryptionProperties, encrypt_file, decrypt_file
from cyberfusion.FileSupport.exceptions import EncryptionError, DecryptionError


def test_encrypt_file_error(
    encryption_properties: EncryptionProperties, non_existent_path: str
) -> None:
    encryption_properties.password_file_path = non_existent_path

    with pytest.raises(EncryptionError):
        encrypt_file(encryption_properties, contents="foobar")


def test_decrypt_file_error(
    encryption_properties: EncryptionProperties, non_existent_path: str
) -> None:
    with pytest.raises(DecryptionError):
        decrypt_file(encryption_properties, path=non_existent_path)
