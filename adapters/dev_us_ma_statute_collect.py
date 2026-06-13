#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""매사추세츠 법전 (malegislature.gov) — 정적 다단 경로 측정 2026-06-13 (오빠 지시 B).

정적 200 도달 확정(헤더보정 07a8725) → Part→Title→Chapter 다단을 diag로 측정.
  루트 GeneralLaws = Part 진입점 5개(PartI~PartV) 정적 실재(run27440421293 _dump_path_tree).
★ 이번 측정 = index_url=PartI 로 두고 _dump_path_tree(숫자없는 진입점 인식)로
  Title 링크가 정적인지 깊이분포로 정밀 관찰. in 식 _dump_hrefs 맹점(숫자포함만) 차단.
  - 정적 Title 확인 시 = link_re/chapter_re 관찰 보정 후 단계별 enum 경로 확정.
  - JS 렌더(Title href 0) 재확인 시 = 막힘 확정·defer(추정 chapter_re 금지·계명1).
실행 = GHA(미국 IP) 정적 코어. link_re 미기재(관찰 후 보정). 로컬 금지(지오블록)."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _us_html_statute_core import run  # noqa: E402

CONFIG = {
    "state": "ma",
    "base": "https://malegislature.gov",
    # diag 임시 = Chapter 페이지가 섹션 링크를 정적 렌더하는지 측정(Part 인덱스는 JS=0건 확인).
    "index_url": "https://malegislature.gov/Laws/GeneralLaws/PartI/TitleI/Chapter2",
    "ext": ".html",
    # link_re/chapter_re = GHA --diag 관찰 후 보정(추정 금지·계명1).
}

if __name__ == "__main__":
    run(CONFIG)
