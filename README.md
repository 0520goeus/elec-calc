# 전기세 얼마

가전제품별 전기요금 계산기 사이트입니다. `python3 build.py`를 실행하면 `dist/`에 사이트 전체가 만들어집니다. 추가 설치는 필요 없습니다.

## 알아서 돌아가는 부분
- GitHub에 올리면 Actions가 사이트를 만들어 GitHub Pages에 배포합니다.
- 매일 00:10(한국 시간)에 다시 만들어서, 달이 바뀌면 제목·표·여름 누진 구간이 그 달 기준으로 바뀝니다.
- 매달 1일과 내용을 고쳐 올릴 때 네이버·Bing에 새 주소를 알립니다(IndexNow).

## 고칠 수 있는 파일
| 파일 | 내용 |
|---|---|
| `appliances.json` | 가전 목록. 한 줄 추가하면 페이지가 하나 늘어납니다. |
| `links.json` | 가전별 제휴 링크. 넣으면 대가성 문구와 함께 표시됩니다. |
| `site.json` | 사이트 주소(`url`), 애드센스 ID(`adsense_client`), 네이버 소유확인 파일 이름(`naver_verification`) |
| `build.py`의 `TARIFF` | 한전 요금표가 바뀌면 여기 숫자만 고치면 됩니다. |

## 수익 연결
1. 애드센스: 승인된 뒤 `site.json`의 `adsense_client`에 `ca-pub-...`를 넣으면 광고와 `ads.txt`가 자동으로 들어갑니다. `github.io` 주소로는 승인 신청이 안 되므로 도메인이 필요합니다.
2. 제휴 링크: `links.json`에 `"jeongiyo": [{"label": "싱글 전기요", "url": "https://link.coupang.com/a/..."}]`처럼 넣습니다.
