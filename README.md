# CoAuthor: feeling understood, ideation help, and ownership

Exploratory reanalysis of the public [CoAuthor](https://coauthor.stanford.edu/) dataset (Lee, Liang & Yang, CHI 2022).
**Paper:** [`paper/main.pdf`](paper/main.pdf) (8 pages). All findings are observational associations.

| Layer | What it does | Script |
|---|---|---|
| Survey | Links metadata + surveys; within/between-writer ordinal GEE, sensitivity analyses, bootstrap | `analyze.py` |
| Qualitative | Hash-checked join of 23 preliminary (AI-assisted, not yet human-reviewed) case codes | `join_qualitative.py` |
| Log replay | Replays every Quill delta with per-character provenance; episodes W / P / QA / QR / QN | `process_logs.py` |
| Process models | E1–E4: availability → understanding, AI revision → ownership, pauses and requests, writing after requests | `process_models.py` |
| Microsimulation | Semi-Markov model with writer shrinkage, session heterogeneity, writer stopping; validated on held-out writers and later sessions | `simulate.py` |
| Shared estimators | Cluster-robust logistic / ordinal GEE, cluster OLS | `stats_core.py` |

```bash
python -m venv .venv && . .venv/bin/activate      # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
python download_data.py                            # metadata XLSX -> data/raw/
# interaction logs: unzip coauthor-v1.0 from https://coauthor.stanford.edu/ (one .jsonl per session)
python run_pipeline.py --input data/raw/coauthor_metadata.xlsx --logs path/to/coauthor-v1.0 --out results
python verify_results.py --out results             # compare with reference_results/
python -m unittest discover -s tests               # 9 tests: data guards + replay provenance
```

The full pipeline runs in under a minute. `results/` and `data/` are git-ignored (they contain participant comments);
`reference_results/` holds the frozen aggregate outputs reported in the paper, including `process/` and `simulation/`.

**Key results.** Within-writer understanding → ownership OR 0.847 [0.660, 1.086] (H1 not supported); understanding → ideation help OR 3.396 [2.761, 4.176];
unanswered-request rate (+10 pp) → understanding OR 0.770 [0.687, 0.862]; writer-specific process parameters improve prediction of the same writer's later sessions by +0.068 nats/event [0.041, 0.106].

**Replay checks.** Replayed human share of inserted characters matches metadata `written_by_human` within 1 pp in 99.9% of sessions (the metadata measure is
of *inserted*, not final, text); replayed selections match `num_selected` in 100%; metadata `num_query` counts answered requests only.

> The Korean manuscript `CoAuthor_Research_Draft_KO.md` and the section below predate the log replay and microsimulation; `paper/main.tex` is current.

---

# CoAuthor: AI의 도움과 소유감은 어떻게 연결되는가?

Mina Lee 등의 CoAuthor 공개 메타데이터·설문을 재분석하는 **실행 가능한 연구 코드셋**입니다. Git 저장소의 최상위 폴더로 사용할 수 있습니다. 실제 GitHub 원격 저장소를 생성하거나 업로드한 것은 아닙니다.

**2026-10-09 기준:** 61개 참여자 ID, 1,407개 AI 요청 세션의 정량 분석과 23개 세션·16명의 사후 코멘트에 대한 AI 보조 예비 코딩을 포함합니다. 초록·서론·본론·결과·결론, 정량·정성 결과표, 근거 문헌, 슈도알고리즘, Option 2의 다섯 항목은 [한국어 원고](CoAuthor_Research_Draft_KO.md)에 있습니다.

## 바로 실행하기

Python **3.12**를 권장합니다. 아래는 macOS/Linux 터미널의 예입니다. 압축을 푼 `coauthor_study` 폴더 안에서 실행하세요.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python download_data.py
python run_pipeline.py --input data/raw/coauthor_metadata.xlsx --out results
python verify_results.py --out results
```

Windows PowerShell에서는 첫 두 줄 대신 다음을 사용하고, 나머지는 동일하게 실행합니다.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

이미 데이터가 있다면 다운로드 단계를 건너뛰고 `--input`에 자신의 XLSX 경로를 넣으세요. `run_pipeline.py`에는 **500회 참여자 bootstrap**과 고정 seed `20261009`가 기본값으로 설정되어 있습니다. 실행 시간은 컴퓨터에 따라 달라집니다.

## 다운로드가 안 되면

[원본 Google Sheet](https://docs.google.com/spreadsheets/d/1O3EXJm52TQHfFSbzVGZmNIzzdu5ow6IjnOBrGTUY02o/edit)를 열어 **파일 → 다운로드 → Microsoft Excel(.xlsx)**을 선택합니다. `data/raw/coauthor_metadata.xlsx`로 저장하면 위 실행 명령을 그대로 사용할 수 있습니다.

[직접 XLSX 다운로드](https://docs.google.com/spreadsheets/d/1O3EXJm52TQHfFSbzVGZmNIzzdu5ow6IjnOBrGTUY02o/export?format=xlsx)

필요한 시트는 `Metadata (creative)`, `Metadata (argumentative)`, `Survey (creative)`, `Survery (argumentative)` 네 개입니다. 마지막 철자는 원본 그대로입니다. CSV 한 장이나 interaction-log JSON만으로 이 분석을 그대로 실행할 수는 없습니다. 이 패키지는 원시 이벤트 로그를 분석한 결과를 포함하지 않습니다.

다운로더는 로그인 HTML을 XLSX로 저장하지 않도록 파일 형식을 검사하며 기존 파일을 덮어쓰지 않습니다. 실제 네트워크 다운로드의 성공 여부는 원본 서비스의 공개 상태와 사용자의 환경에 의존합니다.

## 어느 파일을 보면 되는가

| 파일 | 역할 |
|---|---|
| `run_pipeline.py` | 정량 분석 → 검증된 예비 코드 연결 → 결과표 생성 |
| `analyze.py` | 전처리·순서형 GEE·민감도·고정효과·bootstrap·대비 표집·그림 |
| `join_qualitative.py` | 사례·평가·텍스트 해시 확인 후 고정된 정성 코딩 연결 |
| `make_tables.py` | 실제 출력 CSV를 Markdown 표로 변환 |
| `download_data.py` | 원본 XLSX 다운로드 |
| `verify_results.py` | 기준 결과와 모든 모형 계수·bootstrap 재현 비교 |
| `qualitative_codes.tsv` | AI 보조 예비 코드, 한국어 요약, 해석 한계 |
| `qualitative_manifest.csv` | 코딩을 다른 사례에 잘못 붙이지 않기 위한 원본 대응 정보 |
| `reference_results/` | 이 원고가 근거로 삼은 기준 실행의 집계 결과 |
| `tests/test_data_guards.py` | 변경된 사례·코멘트·평가 및 잘못된 다운로드 형식 차단 검사 |
| `CoAuthor_Research_Draft_KO.md` | 논문 형태의 한국어 분석보고서와 참고문헌 |

실행 뒤 `results/tables.md`를 먼저 읽으세요. 전체 계수는 `results/model_results.csv`, 표본 처리·소프트웨어 버전·수치 검증은 `results/audit.json`, 그림은 `results/associations.png`에 있습니다. 정성 결과를 포함한 실행에서는 `results/qualitative_audit.csv`가 생성됩니다. 단계별 오류는 `results/quantitative.log`, `qualitative.log`, `tables.log`에서 확인합니다.

## 원자료 버전과 정성 코드 보호

기준 XLSX SHA-256:

`bb850549c91ca5d7b34f20b59833f61f0f362b817b91fe333d08b270c25647c4`

Google Sheets 재내보내기만으로 XLSX 바이트가 달라질 수도 있습니다. 해시가 다르면 표본 흐름·문항·결과를 확인해야 합니다. 정성 코드는 파일 전체 해시만으로 연결하지 않습니다. **사례별 session ID, 장르, 평가값, 코멘트 해시가 모두 일치해야** 기존 코드를 연결합니다. 해시 일치는 인간의 해석 검토를 대신하지 않습니다.

원자료가 변경되어 예비 코드 연결이 중단되면 옛 코드를 새 자료에 강제로 붙이지 마세요. 다음처럼 정량 분석과 새 사례 추출만 실행할 수 있습니다.

```bash
python run_pipeline.py --input data/raw/new_export.xlsx --out results --skip-pilot-codes
```

이 경우 정성 코멘트 원문을 다시 읽고, 새 manifest와 코드를 연구자가 작성해야 합니다. `--skip-pilot-codes` 실행은 출력 폴더의 이전 `qualitative_audit.csv`를 제거해 낡은 해석이 새 결과표에 섞이지 않도록 합니다. 새 실행에는 별도 출력 폴더를 쓸 수도 있지만 **기본 `results/` 바깥에 만든 폴더는 직접 `.gitignore`에 추가**해야 합니다.

## Git에 넣기

원본 XLSX·원문 코멘트·전체 분석 중간자료는 ZIP에 포함하지 않았습니다. 실행하면 생성되는 `data/`와 `results/`는 `.gitignore`로 제외합니다. 대신 `reference_results/`의 기준 집계 결과, 익명 사례 식별자에 연결된 예비 요약, 코드와 원고를 포함했습니다. 원자료와 원논문의 이용·인용 조건은 해당 배포처를 따릅니다. 이 패키지가 원자료에 새로운 라이선스를 부여하지는 않습니다.

새 저장소를 준비할 때:

```bash
git init
git add .
git status --short
```

파일 목록을 확인한 뒤 원하는 커밋 메시지로 커밋하고 본인의 원격 저장소에 연결하세요. 원자료·생성 코멘트 파일을 `git add -f`로 추가하지 마세요. 기존 저장소라면 `git init` 없이 원하는 폴더에 파일을 넣어 사용합니다.

## 검증과 구현 범위

```bash
python -m unittest discover -s tests -v
python verify_results.py --out results
```

Python 3.12.14, NumPy 2.3.5, pandas 2.2.3, SciPy 1.17.0, matplotlib 3.10.8, openpyxl 3.1.5에서 실행했습니다. `requirements.txt`는 이 실행 버전을 고정합니다. 별도의 깨끗한 컴퓨터에서 패키지를 새로 설치하는 검증까지 수행한 것은 아닙니다.

순서형 working-independence GEE는 NumPy/SciPy로 누적 이항 score를 풀어 구현했습니다. **statsmodels를 실행한 결과가 아닙니다.** 참여자 군집 sandwich, G/(G−1) 보정, t(G−1) 신뢰구간을 적용했습니다. 분석적 gradient, 절편-only 누적확률, FWL 고정효과 계수의 수치 검증을 포함합니다. 정식 비례오즈 검정과 별도 통계 소프트웨어를 이용한 독립 재현은 남아 있습니다. 일부 BFGS 적합은 precision-loss 메시지를 반환하므로 audit에 메시지·score·조건수를 함께 기록합니다. 작은 score만으로 모든 수치 위험이 해소되는 것은 아닙니다.

## 결과를 해석할 때

- 긍정적인 개인 내 이해–소유감 주가설은 지지되지 않았습니다. 일부 민감도의 음의 관련성을 새 주가설로 바꾸지 않습니다.
- 이해받는 경험과 **자기보고 아이디어 도움**의 관련성은 외부 평가 창의성 향상이나 인과 효과를 뜻하지 않습니다.
- 관찰 ID 61개와 원논문 63명, 실제 응답 1–7과 원논문 소유감 5점 서술의 불일치를 공개했습니다.
- 정성 코드는 AI 보조 예비 분석이며 인간 연구자의 검토를 받지 않았습니다. 코드를 다시 실행해도 해석의 신뢰성이 자동 확보되지 않습니다.
- 시간 압박·진정성·성격·우울·치료 성과를 직접 측정하지 않았습니다.
- 사전등록은 없었습니다. 초기 주가설 이후 보완한 가중치·세션 순서 민감도 분석을 모두 사전 지정 분석처럼 기술하지 않습니다.

Option 2에는 원고 부록 A의 다섯 항목을 사용할 수 있습니다. 제출 전에 본인이 코드·결과·한계를 이해하고 원문 정성 코딩을 검토하세요. 이 작업에는 코드·분석·원고 작성에 상당한 AI 보조가 포함되었습니다.
