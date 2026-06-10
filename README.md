# xsoft-us-collect

미국 6개 주(WI·NY·NJ·OH·MO·RI) 법전 수집 — GitHub Actions(미국 Azure IP) 실행용.

## 배경
한국 IP 지오블록으로 직접 수집 불가한 주 법전을 GHA ubuntu-latest 러너(미국 IP)에서 받아 artifact로 회수한다.

## 구조
```
adapters/
  dev_us_nj_statute_collect.py   # NJ — 벌크 ZIP 1회
  dev_us_ri_statute_collect.py   # RI — 정적 HTML 크롤
  dev_us_wi_statute_collect.py   # WI — 챕터 HTML/PDF
  dev_us_oh_statute_collect.py   # OH — 타이틀→챕터→섹션 HTML
  dev_us_mo_statute_collect.py   # MO — revisor.mo.gov 섹션 HTML
  dev_us_ny_statute_collect.py   # NY — OpenLeg API v3 + HTML 폴백
.github/workflows/collect.yml    # matrix workflow
```

## 실행 방법
1. GitHub Actions > collect workflow > Run workflow
2. states: JSON 배열 (예: `["nj"]` 시험잡 권장)
3. smoke: 0=전수, N>0=N건 후 중단

## 환경변수 / 시크릿
- `NY_OPENLEG_KEY` : GitHub repo Secret 등록 필요 (NY API v3 키)
- `RAW_DIR` : workflow 자동 설정 (`$GITHUB_WORKSPACE/out/us-<주>/statute`)
- `SMOKE` : workflow_dispatch inputs.smoke 연동

## artifact 회수
각 주 잡 완료 후 `statute-<주>.tar.gz` artifact 다운로드 → ext4 /home/xsoft/xsoft_data/raw/ 에 압축해제.

## 시크릿 하드코딩 정책
NY_OPENLEG_KEY 등 모든 키는 `os.environ["NY_OPENLEG_KEY"]`로만 참조. 코드 내 하드코딩 0.
