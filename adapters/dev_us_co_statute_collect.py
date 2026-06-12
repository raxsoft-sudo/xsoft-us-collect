#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CO 주법전 (archive.org CC0 벌크) — 2026-06-13.

전(前) = leg.colorado.gov LexisNexis → PRO 미러 채택(매트릭스 그룹A).
★ 구조 실측 (metadata API) = item gov.co.crs.bulk / license CC0(PD mark) /
  최상위 r폴더 13개(r71.2020.08.01 … r83.2023.06 최신, history/ 과거판 제외) /
  본문 = r83.2023.06/gov.co.crs.*.rtf 51건(title 46 + constitution·index·prefatory·als) [측정].
  현행성 = 2023.06.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _us_archive_cc0_core import run  # noqa: E402

CONFIG = {
    "state": "co",
    "item": "gov.co.crs.bulk",
    "ext": ".rtf",
    "stat_re": r"^gov\.co\.crs\..*\.rtf$",
    "release_re": r"(r\d+\.[\d.]+)/",
    "release_num_re": r"r(\d+)",
    "asof": "2023.06",
}

if __name__ == "__main__":
    run(CONFIG)
