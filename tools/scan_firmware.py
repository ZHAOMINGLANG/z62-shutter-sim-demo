#!/usr/bin/env python3
"""
firmware scan helper for Nikon Z62-style firmware analysis.
Goal:
  - scan binary for likely shutter/audio strings
  - find RIFF/WAV signatures
  - print candidate offsets and candidate text around them
  - provide a reusable starting point before real patching
"""

import argparse
import re
from pathlib import Path

CANDIDATE_PATTERNS = [
    "shutter", "capture", "release", "silent", "mute", "beep", "WAV", "RIFF",
    "SHUTTER", "speaker", "audio", "pcm", "i2s", "dac", "codec", "play",
    "sound", "volume", "burst", "exposure", "photo", "movie"
]


def read_bytes(path: Path) -> bytes:
    return path.read_bytes()


def find_strings(buf: bytes, min_len: int = 4):
    text = []
    pattern = re.compile(rb"[\x20-\x7E]{%d,}" % min_len)
    for m in pattern.finditer(buf):
        s = m.group().decode('ascii', errors='ignore')
        if s.strip():
            text.append((m.start(), s))
    return text


def find_keyword_offsets(buf: bytes, keywords):
    matches = []
    lower = buf.lower()
    for kw in keywords:
        k = kw.lower().encode('ascii', 'ignore')
        pos = 0
        while True:
            idx = lower.find(k, pos)
            if idx < 0:
                break
            matches.append((kw, idx, idx + len(k)))
            pos = idx + 1
    return matches


def find_riff_offsets(buf: bytes):
    results = []
    for i in range(len(buf) - 4):
        if buf[i:i + 4] == b'RIFF':
            results.append(i)
    return results


def find_candidate_context(buf: bytes, offset, radius=96):
    start = max(0, offset - radius)
    end = min(len(buf), offset + radius)
    chunk = buf[start:end]
    # dump as ascii or escaped repr
    text = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
    return {
        'offset': offset,
        'start': start,
        'end': end,
        'ascii_preview': text
    }


def main():
    ap = argparse.ArgumentParser(description='Scan a firmware binary for shutter/audio-related clues.')
    ap.add_argument('firmware', type=Path, help='Path to the firmware binary')
    ap.add_argument('--minlen', type=int, default=4)
    ap.add_argument('--radius', type=int, default=96)
    args = ap.parse_args()

    path = args.firmware
    buf = read_bytes(path)

    print(f'[INFO] file: {path}')
    print(f'[INFO] size: {len(buf)} bytes')
    print('')

    print('[STEP 1] searching for likely shutter/audio keywords...')
    matches = find_keyword_offsets(buf, CANDIDATE_PATTERNS)
    if matches:
        # show unique first 200 hits to keep output concise
        seen = set()
        for kw, start, end in matches[:200]:
            key = (kw, start)
            if key in seen:
                continue
            seen.add(key)
            print(f'  {kw}: offset 0x{start:x}..0x{end:x}')
    else:
        print('  no obvious matches found')
    print('')

    print('[STEP 2] searching for RIFF/WAV markers...')
    riff = find_riff_offsets(buf)
    if riff:
        for off in riff[:50]:
            print(f'  RIFF @ 0x{off:x}')
            ctx = find_candidate_context(buf, off, radius=args.radius)
            print('   preview:', ctx['ascii_preview'][:200])
    else:
        print('  no RIFF markers found')
    print('')

    print('[STEP 3] printing a few high-entropy strings for manual inspection...')
    strings = find_strings(buf, min_len=args.minlen)
    # show only top 80 strings matching candidate patterns and some long strings
    shown = 0
    for off, s in strings:
        low = s.lower()
        if any(p in low for p in ['shutter', 'capture', 'audio', 'speaker', 'wave', 'riif', 'sound', 'mute', 'silent', 'play', 'codec', 'dac', 'i2s', 'bmp', 'pcm', 'vol']):
            print(f'  0x{off:x}: {s[:120]}')
            shown += 1
            if shown >= 80:
                break
    print('')

    print('[SUMMARY]')
    print('  - Candidate keyword hits are a starting point for string-based reverse engineering.')
    print('  - RIFF offsets often indicate embedded WAV/audio assets or encoded data tables.')
    print('  - Next step: import firmware into Ghidra/r2 and inspect XREFs of these offsets.')


if __name__ == '__main__':
    main()
