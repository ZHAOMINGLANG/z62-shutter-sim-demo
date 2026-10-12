#!/usr/bin/env python3
"""
Z6 II firmware patch kit scaffold.
This file does not patch a real Nikon firmware image directly.
It provides the general workflow for:
  - scanning firmware for shutter/audio keywords
  - creating a payload binary
  - injecting a payload into a firmware image
  - validating the injected output in a VM-like environment

Usage
-----
  python patch.py --help
"""

import argparse
import shutil
from pathlib import Path


def _as_hex_bytes(value: str) -> bytes:
    if value.lower().startswith('0x'):
        value = value[2:]
    if len(value) % 2:
        raise ValueError('hex pattern must have even length, e.g. 00A0E3')
    return bytes.fromhex(value)


def find_pattern(buf: bytes, pattern: bytes) -> int:
    idx = buf.find(pattern)
    if idx < 0:
        raise ValueError(f'pattern {pattern!r} not found')
    return idx


def arm_branch_placeholder(src_off: int, dst_off: int, thumb: bool = False) -> bytes:
    """
    Placeholder branch encoding for demonstration only.
    Real firmware patching requires proper target architecture (ARM/Thumb/AArch64),
    correct instruction encoding, and backup/restore of overwritten instructions.
    """
    # 32-bit ARM placeholder: B <offset> using a small literal branch.
    # This is intentionally not final; it should be replaced by a real arch-aware encoder.
    if thumb:
        return b'\x00\x00\x00\x00'
    # Example placeholder: backing bytes to be swapped out.
    return b'\x00\x00\x00\x00'


def main():
    ap = argparse.ArgumentParser(description='Patch a firmware image by appending a payload and replacing a pattern with a branch.')
    ap.add_argument('firmware', type=Path, help='Path to the source firmware image')
    ap.add_argument('payload', type=Path, help='Path to payload.bin (output of build_payload.sh)')
    ap.add_argument('--pattern', required=True, help='Pattern to replace. ASCII string or hex bytes (0x...)')
    ap.add_argument('--out', type=Path, default=Path('patched_firmware.bin'), help='Output path for patched image')
    ap.add_argument('--arch', choices=['arm', 'aarch64'], default='arm', help='Target architecture (placeholder)')
    args = ap.parse_args()

    fw_path = args.firmware
    payload_path = args.payload
    out_path = args.out

    firmware = fw_path.read_bytes()
    payload = payload_path.read_bytes()
    pattern = _as_hex_bytes(args.pattern) if args.pattern.lower().startswith('0x') else args.pattern.encode('utf-8')

    try:
        idx = find_pattern(firmware, pattern)
    except ValueError as exc:
        print(f'ERROR: {exc}')
        print('Hint: use scan_firmware.py or a disassembler to identify an injection point.')
        raise SystemExit(1)

    # backup original before patching
    backup = fw_path.with_suffix(fw_path.suffix + '.bak')
    if not backup.exists():
        shutil.copyfile(fw_path, backup)

    payload_offset = len(firmware)
    patched = bytearray(firmware)
    patched.extend(payload)

    # Replace the original bytes at idx with a placeholder branch.
    # Replace length should be aligned to real instruction width in actual firmware.
    branch = arm_branch_placeholder(idx, payload_offset, thumb=(args.arch == 'arm'))
    patched[idx: idx + len(branch)] = branch

    out_path.write_bytes(patched)
    print(f'Firmware backed up to: {backup}')
    print(f'Patched firmware written to: {out_path}')
    print(f'Original pattern found at offset: 0x{idx:x}')
    print(f'Payload appended at offset: 0x{payload_offset:x}')
    print('WARNING: This is a template. Real firmware patching requires architecture-aware branch generation and validation.')


if __name__ == '__main__':
    main()
