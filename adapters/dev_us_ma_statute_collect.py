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
다음 단계 (별도 세션) = 둘 중 하나 :
  A. 본 어댑터를 _us_spa_statute_core 로 전환 → --netcap 으로 Title/Chapter 트리
     API(XHR) 발굴 → apicollect 열거 (collect_spa.yml).
  B. 권위 있는 Part/Title/Chapter 목록 확보(리서치 = Part I~V 확정) → Chapter URL 생성
     → 정적 Chapter 페이지에서 Section 링크 수집(2단 코어 그대로).
라이선스 = 퍼블릭도메인(government edicts). 주석·notes 비혼입. 로컬 금지(지오블록)."""
import re
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _us_html_statute_core import run  # noqa: E402

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
