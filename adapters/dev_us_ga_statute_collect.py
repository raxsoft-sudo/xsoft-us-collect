#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GA 주법전 (archive.org CC0 벌크) — 2026-06-13.

전(前) = LexisNexis 독점(공식 직접 불가) → PRO 미러 채택(매트릭스 그룹A).
★ 구조 실측 (metadata API) = item gov.ga.ocga.2024 (Official Code of Georgia
  Annotated·최신 2024) / license CC0 / release 폴더 없음 = 볼륨 단위 최상위 /
  본문 = 볼륨 PDF 52건("TNN-TNN (VNN) YYYY.pdf" + 헌법 2권, 텍스트 레이어 OCR) [측정].
  현행성 = 2024. granularity = 볼륨(타이틀 묶음·각 볼륨 전문 포함).
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _us_archive_cc0_core import run  # noqa: E402

CONFIG = {
    "state": "ga",
    "item": "gov.ga.ocga.2024",
    "ext": ".pdf",
    "stat_re": r".*\.pdf$",
    "release_re": None,
    "release_num_re": None,
    "asof": "2024",
}

if __name__ == "__main__":
    run(CONFIG)
