#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""매사추세츠 법전 (malegislature.gov General Laws) — ★ HOLD (열거 장벽 측정).

측정 결과 (2026-06-14 GHA 미국 IP diag) :
  (1) Part 인덱스 /Laws/GeneralLaws/PartI = status 200·body 120KB지만 Title 링크 0건
      = CSR(JS 렌더). 정적 HTML에 하위 트리 없음 (run 27479839243).
  (2) Chapter 페이지 /Laws/GeneralLaws/PartI/TitleI/Chapter2 = status 200·정적 렌더.
      섹션 링크 다수 = /Laws/GeneralLaws/Part{R}/Title{R}/Chapter{N}/Section{N}
      (link_re 66건 매칭 · run 27480278804). 본문 단위 = Section 페이지.
  (3) 간헐 타임아웃 = 첫 Chapter diag URLError timed out → 재시도 성공 (리서치 0614
      "타임아웃 빈번·저속 크롤" 경고 일치). collect 시 긴 timeout·저병렬 필요.

남은 장벽 = Part→Title→Chapter 열거. Part 인덱스가 CSR라 정적 파싱 불가.
★ 단계 A 착수 (2026-06-14 standing 8주) = SPA 코어 전환 → --netcap 으로 Title/Chapter 트리
  API(XHR/fetch) 발굴 (IN 동형·관찰 정본·추정 금지·계명1). 발굴 결과로 chapter_re/api_re 보정.
  XHR 트리 부재 시 = 경로 B(권위 Part/Title 목록 → 정적 Chapter Section 수집)로 재판단.
라이선스 = 퍼블릭도메인(government edicts). 주석·notes 비혼입. 로컬 금지(지오블록)."""
import re
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _us_spa_statute_core import run  # noqa: E402

CONFIG = {
    "state": "ma",
    "base": "https://malegislature.gov",
    "index_url": "https://malegislature.gov/Laws/GeneralLaws",
    # ★ 확정 측정 = Chapter 페이지의 Section 링크 패턴(run 27480278804). 열거 장벽 해소 후 사용.
    "link_re": re.compile(
        r'href=["\'](/Laws/GeneralLaws/Part[IVX]+/Title[IVX]+/Chapter\d+[A-Za-z]?/Section[0-9A-Za-z]+)["\']',
        re.IGNORECASE,
    ),
    # chapter_re = Part 인덱스 CSR라 정적 열거 불가 = netcap/권위목록 확보 후 보정(추정 금지·계명1).
    "ext": ".html",
}

if __name__ == "__main__":
    run(CONFIG)
