from __future__ import annotations

import re
import struct
import zlib
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PromptExtractionResult:
    positive: list[str]
    negative: list[str]
    raw_text: str


def extract_generation_prompts(image_path: Path) -> PromptExtractionResult | None:
    raw_parameters = _extract_sd_parameters(image_path)
    if not raw_parameters:
        raw_parameters = _extract_exif_user_comment(image_path)
    if not raw_parameters:
        return None

    positive, negative = _parse_prompt_lists(raw_parameters)
    return PromptExtractionResult(positive=positive, negative=negative, raw_text=raw_parameters)


def _extract_sd_parameters(image_path: Path) -> str | None:
    if image_path.suffix.lower() != ".png":
        return None

    try:
        with image_path.open("rb") as f:
            if f.read(8) != b"\x89PNG\r\n\x1a\n":
                return None

            while True:
                length_bytes = f.read(4)
                if len(length_bytes) != 4:
                    return None

                length = int.from_bytes(length_bytes, "big")
                chunk_type = f.read(4)
                data = f.read(length)
                f.read(4)  # CRC

                if len(chunk_type) != 4 or len(data) != length:
                    return None

                if chunk_type == b"tEXt":
                    sep = data.find(b"\x00")
                    if sep > 0 and data[:sep] == b"parameters":
                        return data[sep + 1 :].decode("latin-1")

                elif chunk_type == b"zTXt":
                    sep = data.find(b"\x00")
                    if sep > 0 and data[:sep] == b"parameters" and sep + 2 <= len(data):
                        if data[sep + 1] != 0:
                            continue
                        try:
                            decompressed = zlib.decompress(data[sep + 2 :])
                        except zlib.error:
                            continue
                        return decompressed.decode("latin-1")

                elif chunk_type == b"iTXt":
                    sep = data.find(b"\x00")
                    if sep > 0 and data[:sep] == b"parameters":
                        pos = sep + 1
                        if pos + 2 > len(data):
                            continue
                        compression_flag = data[pos]
                        compression_method = data[pos + 1]
                        pos += 2

                        lang_end = data.find(b"\x00", pos)
                        if lang_end < 0:
                            continue
                        pos = lang_end + 1

                        translated_end = data.find(b"\x00", pos)
                        if translated_end < 0:
                            continue
                        pos = translated_end + 1

                        text_bytes = data[pos:]
                        if compression_flag == 1:
                            if compression_method != 0:
                                continue
                            try:
                                text_bytes = zlib.decompress(text_bytes)
                            except zlib.error:
                                continue
                        return text_bytes.decode("utf-8")

                if chunk_type == b"IEND":
                    break
    except OSError:
        return None

    return None


def _extract_exif_user_comment(image_path: Path) -> str | None:
    try:
        payload = image_path.read_bytes()
    except OSError:
        return None

    search_offset = 0
    marker = b"Exif\x00\x00"
    while True:
        start = payload.find(marker, search_offset)
        if start < 0:
            return None

        tiff_offset = start + len(marker)
        user_comment = _read_user_comment_from_tiff(payload[tiff_offset:])
        if user_comment:
            return user_comment

        search_offset = start + 1


def _read_user_comment_from_tiff(tiff_data: bytes) -> str | None:
    if len(tiff_data) < 8:
        return None

    byte_order = tiff_data[:2]
    if byte_order == b"II":
        endian = "<"
    elif byte_order == b"MM":
        endian = ">"
    else:
        return None

    if _unpack_u16(tiff_data, 2, endian) != 42:
        return None

    ifd0_offset = _unpack_u32(tiff_data, 4, endian)
    exif_ifd_entry_offset = _find_tag_entry_offset(tiff_data, ifd0_offset, 0x8769, endian)
    if exif_ifd_entry_offset is None:
        return None

    exif_ifd_offset = _unpack_u32(tiff_data, exif_ifd_entry_offset + 8, endian)
    user_comment_field_offset = _find_tag_entry_offset(tiff_data, exif_ifd_offset, 0x9286, endian)
    if user_comment_field_offset is None:
        return None

    data = _read_field_bytes(tiff_data, user_comment_field_offset, endian)
    if not data:
        return None

    return _decode_user_comment(data)


def _find_tag_entry_offset(data: bytes, ifd_offset: int, tag_id: int, endian: str) -> int | None:
    if ifd_offset < 0 or ifd_offset + 2 > len(data):
        return None

    count = _unpack_u16(data, ifd_offset, endian)
    base = ifd_offset + 2
    for i in range(count):
        entry_offset = base + i * 12
        if entry_offset + 12 > len(data):
            return None
        tag = _unpack_u16(data, entry_offset, endian)
        if tag == tag_id:
            return entry_offset
    return None


def _read_field_bytes(data: bytes, field_offset: int, endian: str) -> bytes | None:
    field_type = _unpack_u16(data, field_offset + 2, endian)
    count = _unpack_u32(data, field_offset + 4, endian)
    value_or_offset = data[field_offset + 8 : field_offset + 12]

    type_sizes = {
        1: 1,  # BYTE
        2: 1,  # ASCII
        7: 1,  # UNDEFINED
    }
    unit = type_sizes.get(field_type)
    if unit is None:
        return None

    total_size = count * unit
    if total_size <= 4:
        return value_or_offset[:total_size]

    value_offset = _unpack_u32(data, field_offset + 8, endian)
    if value_offset < 0 or value_offset + total_size > len(data):
        return None

    return data[value_offset : value_offset + total_size]


def _decode_user_comment(data: bytes) -> str | None:
    if data.startswith(b"ASCII\x00\x00\x00"):
        return data[8:].decode("utf-8", errors="ignore").strip("\x00")
    if data.startswith(b"UNICODE\x00"):
        body = data[8:]
        for encoding in ("utf-16-be", "utf-16-le", "utf-8"):
            try:
                return body.decode(encoding, errors="ignore").replace("\x00", "")
            except UnicodeError:
                continue
        return None
    if data.startswith(b"JIS\x00\x00\x00\x00\x00"):
        return data[8:].decode("shift_jis", errors="ignore").strip("\x00")

    return data.decode("utf-8", errors="ignore").strip("\x00")


def _unpack_u16(data: bytes, offset: int, endian: str) -> int:
    return struct.unpack_from(f"{endian}H", data, offset)[0]


def _unpack_u32(data: bytes, offset: int, endian: str) -> int:
    return struct.unpack_from(f"{endian}I", data, offset)[0]


def _parse_prompt_lists(parameters: str) -> tuple[list[str], list[str]]:
    normalized = parameters.replace("\r\n", "\n")
    steps_split = re.split(r"\nSteps:\s*", normalized, maxsplit=1)
    body = steps_split[0]

    if "Negative prompt:" in body:
        positive_part, negative_part = body.split("Negative prompt:", maxsplit=1)
    else:
        positive_part, negative_part = body, ""

    positive = _tokenize_prompt_terms(positive_part)
    negative = _tokenize_prompt_terms(negative_part)
    return positive, negative


def _tokenize_prompt_terms(part: str) -> list[str]:
    terms: list[str] = []
    for raw in part.replace("\n", ",").split(","):
        token = raw.strip()
        if not token:
            continue

        token = token.strip('"\'')
        weighted = re.match(r"^\((.+):\s*-?\d+(?:\.\d+)?\)$", token)
        if weighted:
            token = weighted.group(1).strip()

        if token:
            terms.append(token)

    return terms
