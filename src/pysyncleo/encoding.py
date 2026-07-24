import logging
import struct
from typing import Tuple

from cryptography.hazmat.primitives.asymmetric.x25519 import (
    X25519PrivateKey,
    X25519PublicKey,
)
from cryptography.hazmat.primitives import ciphers, padding, hashes
from cryptography.hazmat.primitives.ciphers.algorithms import AES
from cryptography.hazmat.primitives.ciphers.modes import CBC
import cryptography.hazmat.primitives.serialization as srlz

from .enums import FrameType, UdpCommandType

_LOGGER = logging.getLogger(__name__)


class SyncleoEncoder:
    def __init__(self, device):
        self.device = device

    def generate_handshake(self) -> bytes:
        raise NotImplementedError

    def encode(self, seq: int, frame_type: FrameType, payload: bytes) -> bytes:
        raise NotImplementedError

    def decode(self, data: bytes) -> Tuple[int, FrameType, bytes]:
        raise NotImplementedError

    def _pack_header(self, seq: int, frame_type: FrameType, payload: bytes) -> bytes:
        return struct.pack("<BBH", seq, frame_type.value, len(payload)) + payload


class PlainEncoder(SyncleoEncoder):
    def generate_handshake(self) -> bytes:
        payload = bytearray([UdpCommandType.HANDSHAKE.value]) + self.device.device_token
        return self.encode(0, FrameType.CMD, payload)

    def encode(self, seq: int, frame_type: FrameType, payload: bytes) -> bytes:
        return self._pack_header(seq, frame_type, payload)

    def decode(self, data: bytes) -> Tuple[int, FrameType, bytes]:
        if len(data) < 4:
            raise ValueError("Frame too short")

        seq, ftype_val, length = struct.unpack("<BBH", data[:4])
        return seq, FrameType(ftype_val), data[4 : 4 + length]


class CryptoV2Encoder(SyncleoEncoder):
    def __init__(self, device):
        super().__init__(device)
        self.privkey = X25519PrivateKey.generate()
        self.pubkey = bytes(
            reversed(
                self.privkey.public_key().public_bytes(
                    encoding=srlz.Encoding.Raw, format=srlz.PublicFormat.Raw
                )
            )
        )

        remote_pub = X25519PublicKey.from_public_bytes(
            bytes(reversed(device.device_pubkey))
        )
        shared_key = bytes(reversed(self.privkey.exchange(remote_pub)))

        digest = hashes.Hash(hashes.SHA256())
        digest.update(shared_key)
        shared_sha256 = digest.finalize()

        self.encinkey = shared_sha256[:16]
        self.encoutkey = shared_sha256[16:]

    def generate_handshake(self) -> bytes:
        cipher = ciphers.Cipher(AES(self.encoutkey), CBC(self.encinkey))
        encryptor = cipher.encryptor()

        encrypted_token = (
            encryptor.update(self.device.device_token) + encryptor.finalize()
        )

        payload = bytearray([0])
        payload.extend(self.pubkey)
        payload.extend(encrypted_token)

        return self._pack_header(
            seq=0, frame_type=FrameType.CMD, payload=bytes(payload)
        )

    def encode(self, seq: int, frame_type: FrameType, payload: bytes) -> bytes:
        i = seq & 0xF
        j = (seq >> 4) & 0xF

        key = self.encoutkey[i:] + self.encoutkey[:i]
        iv = self.encinkey[j:] + self.encinkey[:j]

        _LOGGER.debug(
            "Encrypting seq=%d: key=[%s] iv=[%s] payload=[%s]",
            seq,
            key.hex(),
            iv.hex(),
            payload.hex(),
        )

        aes = AES(key)
        cipher = ciphers.Cipher(aes, CBC(iv))
        encryptor = cipher.encryptor()

        newdata = bytearray([seq]) + payload

        padder = padding.PKCS7(aes.block_size).padder()
        padded_data = padder.update(bytes(newdata)) + padder.finalize()
        ciphertext = encryptor.update(padded_data) + encryptor.finalize()

        return self._pack_header(seq, frame_type, ciphertext)

    def decode(self, data: bytes) -> Tuple[int, FrameType, bytes]:
        if len(data) < 4:
            raise ValueError("Frame too short")

        seq, ftype_val, length = struct.unpack("<BBH", data[:4])
        frame_type = FrameType(ftype_val)
        ciphertext = data[4 : 4 + length]

        if len(ciphertext) == 0:
            return seq, frame_type, ciphertext

        j = seq & 0xF
        k = (seq >> 4) & 0xF

        key = self.encinkey[j:] + self.encinkey[:j]
        iv = self.encoutkey[k:] + self.encoutkey[:k]

        _LOGGER.debug(
            "Decrypting seq=%d: key=[%s] iv=[%s] ciphertext=[%s]",
            seq,
            key.hex(),
            iv.hex(),
            ciphertext.hex(),
        )

        aes = AES(key)
        cipher = ciphers.Cipher(aes, CBC(iv))
        decryptor = cipher.decryptor()

        try:
            decrypted = decryptor.update(ciphertext) + decryptor.finalize()
            unpadder = padding.PKCS7(aes.block_size).unpadder()
            plaintext = unpadder.update(decrypted) + unpadder.finalize()
        except Exception as e:
            _LOGGER.warning("Failed to decrypt frame seq=%d: %s", seq, e)
            raise

        _LOGGER.debug("Decrypted result: [%s]", plaintext.hex())

        if not plaintext or plaintext[0] != (seq & 0xFF):
            raise ValueError(
                f"Decrypted seq mismatch. Expected {seq & 0xFF}, got {plaintext[0]}"
            )

        return seq, frame_type, plaintext[1:]
