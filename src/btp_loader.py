"""BTP packet loader wrapper for backtest."""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Iterator

import numpy as np

TOOLS = Path("C:/HIST_B3/generator_v3/tools")
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from btp import BtpPacket, open_packet, read_header  # noqa: E402

ROOT = Path("C:/HIST_B3/generator_v3")


def packet_path(asset: str, day: str, root: Path = ROOT) -> Path:
    return root / "packet" / asset / f"{day}.btp"


def open_day(asset: str, day: str, root: Path = ROOT) -> BtpPacket:
    return open_packet(packet_path(asset, day, root))


def list_days(asset: str, root: Path = ROOT) -> list[str]:
    folder = root / "packet" / asset
    return [p.stem for p in sorted(folder.glob("*.btp"))]


def iter_days(
    asset: str,
    start: str | None = None,
    end: str | None = None,
    root: Path = ROOT,
) -> Iterator[BtpPacket]:
    for day in list_days(asset, root):
        if start and day < start:
            continue
        if end and day > end:
            continue
        yield open_day(asset, day, root)
