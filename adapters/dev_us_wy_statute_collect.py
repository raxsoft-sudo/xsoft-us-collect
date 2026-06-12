#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""WY 주법전 (archive.org CC0 벌크) — 2026-06-13.

전(前) = wyoleg.gov LexisNexis(독점·SPA) → PRO 미러 채택(매트릭스 그룹A).
★ 구조 실측 (metadata API) = item gov.wy.code / license CC0 1.0 /
  release 7개(release78.2021.05 … release84.2022.10 최신) /
  본문 = release84.2022.10/gov.wy.code.*.rtf 45건(타이틀 단위 전문) [측정].
  현행성 = 2022.10 (보강용). court/ag.opinions 는 code prefix 아니라 제외.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _us_archive_cc0_core import run  # noqa: E402

CONFIG = {
    "state": "wy",
    "item": "gov.wy.code",
    "ext": ".rtf",
    "stat_re": r"^gov\.wy\.code\..*\.rtf$",
    "release_re": r"(release[\d.]+)/",
    "release_num_re": r"release(\d+)",
    "asof": "2022.10",
}

if __name__ == "__main__":
    run(CONFIG)
