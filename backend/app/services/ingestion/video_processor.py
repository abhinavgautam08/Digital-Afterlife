"""
Video processing module for Phase 2.
Extracts duration, dimensions (width, height), and container metadata for MP4, MOV, and WEBM.
Handles missing FFmpeg gracefully without crashing or corrupting original files.
Includes independent pure-Python parsers for MP4 atoms and WebM EBML structures.
"""
from typing import Dict, Any, Optional
import io
import struct

from backend.app.core.logging import logger

try:
    from mutagen.mp4 import MP4
    HAS_MUTAGEN_MP4 = True
except ImportError:
    HAS_MUTAGEN_MP4 = False


def parse_mp4_atoms(file_bytes: bytes) -> Dict[str, Any]:
    """
    Pure Python parser for MP4/MOV container atoms (mvhd, tkhd)
    to extract duration and dimensions without external FFmpeg requirements.
    """
    data = file_bytes
    duration_sec: Optional[float] = None
    width: Optional[int] = None
    height: Optional[int] = None

    try:
        # Search for 'mvhd' atom
        mvhd_pos = data.find(b"mvhd")
        if mvhd_pos != -1 and mvhd_pos + 28 <= len(data):
            version = data[mvhd_pos + 4]
            if version == 0:
                # 32-bit timescale and duration
                timescale, duration = struct.unpack(">II", data[mvhd_pos + 16 : mvhd_pos + 24])
                if timescale > 0:
                    duration_sec = round(duration / float(timescale), 2)
            elif version == 1 and mvhd_pos + 36 <= len(data):
                # 64-bit duration
                timescale = struct.unpack(">I", data[mvhd_pos + 24 : mvhd_pos + 28])[0]
                duration = struct.unpack(">Q", data[mvhd_pos + 28 : mvhd_pos + 36])[0]
                if timescale > 0:
                    duration_sec = round(duration / float(timescale), 2)

        # Search for 'tkhd' atom for video dimensions
        tkhd_pos = data.find(b"tkhd")
        if tkhd_pos != -1:
            version = data[tkhd_pos + 4]
            offset = 84 if version == 0 else 96
            end_pos = tkhd_pos + offset
            if end_pos <= len(data):
                w_fixed, h_fixed = struct.unpack(">II", data[end_pos - 8 : end_pos])
                extracted_w = w_fixed >> 16
                extracted_h = h_fixed >> 16
                if 10 < extracted_w < 10000 and 10 < extracted_h < 10000:
                    width = extracted_w
                    height = extracted_h

    except Exception as e:
        logger.debug(f"Direct MP4 atom parse notice: {e}")

    return {
        "duration_seconds": duration_sec,
        "width": width,
        "height": height
    }


def parse_webm_metadata(file_bytes: bytes) -> Dict[str, Any]:
    """
    Pure Python parser for WebM (EBML) container duration and video dimensions.
    Extracts Segment Info Duration & TimecodeScale, and Video PixelWidth & PixelHeight.
    No FFmpeg or external binaries required.
    """
    duration_sec: Optional[float] = None
    width: Optional[int] = None
    height: Optional[int] = None

    if not file_bytes.startswith(b"\x1A\x45\xDF\xA3"):
        return {"duration_seconds": None, "width": None, "height": None}

    try:
        # Default Matroska timecode scale is 1,000,000 nanoseconds = 1 millisecond
        timecode_scale_ns = 1_000_000

        # Scan for TimecodeScale (\x2A\xD7\xB1)
        tc_pos = file_bytes.find(b"\x2A\xD7\xB1")
        if tc_pos != -1 and tc_pos + 4 < len(file_bytes):
            vlen = file_bytes[tc_pos + 3]
            if vlen == 0x81 and tc_pos + 5 <= len(file_bytes):
                timecode_scale_ns = file_bytes[tc_pos + 4]
            elif vlen == 0x82 and tc_pos + 6 <= len(file_bytes):
                timecode_scale_ns = struct.unpack(">H", file_bytes[tc_pos + 4 : tc_pos + 6])[0]
            elif vlen == 0x83 and tc_pos + 7 <= len(file_bytes):
                timecode_scale_ns = int.from_bytes(file_bytes[tc_pos + 4 : tc_pos + 7], "big")
            elif vlen == 0x84 and tc_pos + 8 <= len(file_bytes):
                timecode_scale_ns = struct.unpack(">I", file_bytes[tc_pos + 4 : tc_pos + 8])[0]

        # Scan for Duration (\x44\x89)
        dur_pos = file_bytes.find(b"\x44\x89")
        if dur_pos != -1 and dur_pos + 3 < len(file_bytes):
            vlen = file_bytes[dur_pos + 2]
            if vlen == 0x84 and dur_pos + 7 <= len(file_bytes):
                raw_dur = struct.unpack(">f", file_bytes[dur_pos + 3 : dur_pos + 7])[0]
                duration_sec = round((raw_dur * timecode_scale_ns) / 1e9, 2)
            elif vlen == 0x88 and dur_pos + 11 <= len(file_bytes):
                raw_dur = struct.unpack(">d", file_bytes[dur_pos + 3 : dur_pos + 11])[0]
                duration_sec = round((raw_dur * timecode_scale_ns) / 1e9, 2)

        # Scan for PixelWidth (\xB0)
        w_pos = file_bytes.find(b"\xB0")
        if w_pos != -1 and w_pos + 2 < len(file_bytes):
            vlen = file_bytes[w_pos + 1]
            if vlen == 0x81 and w_pos + 3 <= len(file_bytes):
                width = file_bytes[w_pos + 2]
            elif vlen == 0x82 and w_pos + 4 <= len(file_bytes):
                width = struct.unpack(">H", file_bytes[w_pos + 2 : w_pos + 4])[0]
            elif vlen == 0x84 and w_pos + 6 <= len(file_bytes):
                width = struct.unpack(">I", file_bytes[w_pos + 2 : w_pos + 6])[0]

        # Scan for PixelHeight (\xBA)
        h_pos = file_bytes.find(b"\xBA")
        if h_pos != -1 and h_pos + 2 < len(file_bytes):
            vlen = file_bytes[h_pos + 1]
            if vlen == 0x81 and h_pos + 3 <= len(file_bytes):
                height = file_bytes[h_pos + 2]
            elif vlen == 0x82 and h_pos + 4 <= len(file_bytes):
                height = struct.unpack(">H", file_bytes[h_pos + 2 : h_pos + 4])[0]
            elif vlen == 0x84 and h_pos + 6 <= len(file_bytes):
                height = struct.unpack(">I", file_bytes[h_pos + 2 : h_pos + 6])[0]

    except Exception as e:
        logger.debug(f"WebM EBML metadata parse notice: {e}")

    return {
        "duration_seconds": duration_sec,
        "width": width,
        "height": height
    }


def process_video(
    file_bytes: bytes,
    file_format: str,
    uuid_name: str
) -> Dict[str, Any]:
    """
    Safely processes video artifacts.
    Extracts duration and dimensions via pure-Python parsers (MP4/MOV atoms or WebM EBML).
    No FFmpeg installation required.
    """
    duration_seconds: Optional[float] = None
    width: Optional[int] = None
    height: Optional[int] = None
    meta: Dict[str, Any] = {"format": file_format}

    if file_format == "webm":
        webm_info = parse_webm_metadata(file_bytes)
        duration_seconds = webm_info.get("duration_seconds")
        width = webm_info.get("width")
        height = webm_info.get("height")
    elif file_format in ("mp4", "mov", "m4v"):
        # Attempt mutagen MP4 parse first if available
        if HAS_MUTAGEN_MP4:
            try:
                mp4_obj = MP4(io.BytesIO(file_bytes))
                if mp4_obj.info is not None:
                    duration_seconds = round(float(getattr(mp4_obj.info, "length", 0.0)), 2)
                    bitrate = getattr(mp4_obj.info, "bitrate", None)
                    if bitrate:
                        meta["bitrate"] = bitrate
            except Exception as e:
                logger.debug(f"Mutagen video parse notice: {e}")

        # Fallback to direct atom parsing
        atom_info = parse_mp4_atoms(file_bytes)
        if duration_seconds is None and atom_info["duration_seconds"]:
            duration_seconds = atom_info["duration_seconds"]
        if width is None and atom_info["width"]:
            width = atom_info["width"]
        if height is None and atom_info["height"]:
            height = atom_info["height"]

    return {
        "duration_seconds": duration_seconds,
        "width": width,
        "height": height,
        "thumbnail_path": None,
        "extracted_text": None,
        "original_created_at": None,
        "metadata": meta
    }
