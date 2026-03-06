# 보스용 AI 자율학습 매매시스템 (초기 버전)

이 저장소는 Windows 환경에서 동작할 수 있는 **안전 우선형 자동매매 시범 시스템**입니다.

목표:
- 시장 분석 → 전략 추천 → 후보 종목 선별 → EV/리스크 게이트 → 주문 실행 → 복기 학습
- AI는 의사결정 보조와 리포트 생성에만 사용
- 모든 실거래 판단은 리스크 엔진의 규칙으로 최종 제어

현재 버전은 기본적으로 paper 모드 기반이며, `live` 모드(실거래)는 설정 검증 후 단계적으로 확장됩니다.

## 실행 방법

> 모든 실행은 아래 폴더를 기준으로 합니다.
> `D:\신명범(25.07.01.~)\개인파일\매매봇`

이 프로젝트는 `scripts` 폴더의 런처가 먼저 프로젝트 전용 가상환경(`.venv`)을 만들고, 의존성 설치를 보강한 뒤 실행합니다.

### 1) CLI 단발/반복 실행

```powershell
Set-Location "D:\신명범(25.07.01.~)\개인파일\매매봇"
py -m trading_system.main --config configs/default.json --mode dry
```

### 1-1) 원클릭 실행(가장 쉬운 방식)

```powershell
.\start-system.bat
```

```powershell
.\start-system.bat web
```

- `start-system.bat`: 데스크톱 대시보드 실행(기본)
- `start-system.bat web`: 웹 대시보드 실행
- `start-system.bat desktop [config_path]`: 데스크톱 + 커스텀 설정
- `start-system.bat web [config_path] [host] [port]`: 웹 + 커스텀 설정
- `start-system.bat multi [multi_config] [command] [interval] [live_token]`: 멀티 운용
- `start-system.bat multi-ui [multi_config] [host] [port]`: 멀티 통합 대시보드
- `start-system.bat nogate [desktop|web|multi|multi-ui] ...`: 검증 게이트 임시 우회 실행
- `start-system.bat rehearsal [config] [output_path|auto]`: 실거래 staged runbook/실패 대응표 생성
- `start-nogate-preset.bat [safe|balanced|aggressive] [desktop|web]`: 검증 우회 + 프리셋 실행

```powershell
.\start-system.bat /h
```
로 사용법을 확인할 수 있습니다.

### 1-1-b) 멀티계정/멀티전략 동시 운용

샘플 멀티 프로파일:
- `configs/multi_accounts.sample.json`

상태 조회:

```powershell
.\start-system.bat multi configs/multi_accounts.sample.json status
```

전체 프로파일 1회 실행:

```powershell
.\start-system.bat multi configs/multi_accounts.sample.json run-once
```

동시 자동 루프 시작:

```powershell
.\start-system.bat multi configs/multi_accounts.sample.json loop 5
```

또는 전용 런처:

```powershell
.\start-multi-system.bat configs/multi_accounts.sample.json loop 5
```

멀티 통합 대시보드:

```powershell
.\start-system.bat multi-ui configs/multi_accounts.sample.json 127.0.0.1 8100
```

또는 전용 런처:

```powershell
.\start-multi-dashboard.bat configs/multi_accounts.sample.json 127.0.0.1 8100
```

멀티 통합 대시보드에서 지원:
- 프로파일별 시작/중지/1회 실행
- 프로파일별 실거래 준비점검/리포트 저장
- 프로파일별 리스크 해제(확인 토큰 입력)
- 프로파일별 AI 연결 테스트(샘플 심볼 지정)
- 프로파일별 거래소 파라미터 점검/리포트 저장(심볼 리스트 지정)
- 프로파일별 거부사유 지표 조회
- 프로파일별 알림 임계치 적용/검증 알림 테스트
- 프로파일별 자율학습 설정 적용/학습 상태/검증이력 조회
- 프로파일별 전략 bot_profile 조회/적용(전략별 봇 파라미터 실시간 수정)
  - 초보자 모드: 숫자 입력 폼으로 설정 (JSON 편집 기본 숨김)
- 탭 전환 UI(시작/진행중/내계정/거래소 API/트레이딩 로그) 및 로그 탭 전용 체결/거부 내역 표
  - `내계정` 탭: 프로필별 계정/리스크/실행가드 요약
  - `내계정` 탭: 선택 프로필 기준 일자별 실현손익(P&L) 차트
  - `거래소 API` 탭: 프로필별 거래소 상태 요약 + Readiness/Exchange Probe 바로 실행
  - `거래소 API` 탭: API 키/시크릿/패스프레이즈 설정 상태 및 env 참조 표시
- 실거래 안정화: 재시도 지수 백오프 + 심볼/전역 자동 격리(`execution_guard`)

설명:
- 멀티 운용은 프로파일별 `config_path`를 읽어 각각 독립 런타임으로 실행합니다.
- 전략 차별화는 각 프로파일의 설정 파일(`strategies`, `risk_limits`, `mode`)을 별도로 두는 방식입니다.
- `boss_secondary`처럼 `enabled=false`로 비활성 프로파일을 관리할 수 있습니다.

전략별 봇 파라미터 자동 매핑:
- `pipeline`은 전략 신호 생성 후 실행 직전에 `bot_type` 기반 프로파일을 자동 적용합니다.
- 기본 매핑: `grid -> grid`, `trend/ema/volume -> trend`, `defensive -> defensive`, `funding_arb -> funding_arb`, `bollinger_reversion -> indicator`
- 각 전략에서 커스텀 가능 키:
  - `bot_type`
  - `bot_profile`
  - `bot_profile_by_regime` (`trend_up`, `trend_down`, `range`, `panic`)

`nogate` 프리셋(보수/중립/공격):
- `configs/presets/nogate_safe.json`
- `configs/presets/nogate_balanced.json`
- `configs/presets/nogate_aggressive.json`

실행 예시:
```powershell
.\start-nogate-preset.bat safe
.\start-nogate-preset.bat balanced web 127.0.0.1 8000
.\start-system.bat nogate web configs\presets\nogate_aggressive.json 127.0.0.1 8000
```

Kalman 기반 신호 반영:
- Mock 시세 생성 시 2상태(가격/속도) Kalman 필터를 적용해 `kalman_trend_score`, `kalman_innovation_z`, `kalman_uncertainty`를 계산합니다.
- 레짐 분류는 모멘텀+Kalman 추세를 결합하고, Kalman 충격(`innovation_z`)이 큰 경우 panic/range 쪽으로 보수적으로 전환합니다.
- `trend/grid/defensive/funding_arb/bollinger_reversion/ema_crossover/volume_breakout` 전략에 Kalman 보조 게이트/가중치가 반영됩니다.

전략 피처 로그 확장:
- 실행 로그(`/api/executions`)에 `regime_label`, `entry_rationale`, `market_state`, `slippage_cause`가 포함됩니다.
- 슬리피지 원인을 `within_expected_spread`, `high_volatility`, `kalman_shock`, `partial_fill_liquidity` 등으로 분류합니다.

학습 리더보드 + 승인형/자동형 분리:
- 학습 응답(`/api/learning`)에 전략/레짐/종목 리더보드가 포함됩니다.
- `auto_learning.apply_mode`:
  - `manual_approval`: 자동 제안은 pending 큐에 저장 후 승인 시 적용
  - `auto_apply`: 주기/한도 기준으로 자동 적용
- 제안 큐 조회: `GET /api/learning/proposals`
- 제안 승인/거절: `POST /api/learning/proposals/review`

### 1-2) 설치형 원클릭 배포 (딸깍 배포)

로컬 설치:

```powershell
.\install-system.bat
```

설치 경로 기본값:
- `%LOCALAPPDATA%\BossTradingSystem`

설치 후:
- 바탕화면 바로가기 2개 생성
  - `보스 AI 트레이딩 데스크톱`
  - `보스 AI 트레이딩 웹`
- 첫 실행 시 `.venv` 생성 + `requirements.txt` 의존성 자동복구

배포 패키지(zip) 생성:

```powershell
.\scripts\build-deploy-package.ps1
```

생성 결과:
- `dist\boss-trading-system-deploy\` (배포 폴더)
- `dist\boss-trading-system-deploy.zip` (전달용 압축)

대상 PC에서는 zip 압축 해제 후 `install.bat` 1회 실행하면 됩니다.

### 1-3) 운영 명령 (헬스체크/백업)

아래 명령은 PowerShell 없이 `.bat + python` 경로로 동작합니다.

헬스체크:

```powershell
.\start-system.bat healthcheck configs/default.json 127.0.0.1 8000
```

웹 대시보드 API까지 점검한 JSON 결과를 출력합니다.

백업:

```powershell
.\start-system.bat backup
```

출력 경로 지정:

```powershell
.\start-system.bat backup backups
```

기본 출력:
- `backups\trading_system_backup_YYYYMMDD_HHMMSS.zip`

리허설(runbook) 생성:

```powershell
.\start-system.bat rehearsal configs/default.json auto
```

기본 출력:
- `data\validation\live_rehearsal\live_rehearsal_YYYYMMDD_HHMMSS.json`

Watchdog(자동 재기동):

```powershell
.\start-system.bat watchdog configs/default.json 127.0.0.1 8000 15
```

- 대시보드 `/api/status`가 응답하지 않으면 웹 대시보드를 자동 재기동합니다.
- 로그: `logs\watchdog.log`

로그온 자동 실행 등록(선택):

```powershell
.\scripts\register-watchdog-task.ps1
```

PowerShell 차단 환경이라면 작업 스케줄러에서
`start-system.bat watchdog configs/default.json 127.0.0.1 8000 15`
명령을 로그온 트리거로 직접 등록하면 동일하게 운용할 수 있습니다.

등록 해제:

```powershell
.\scripts\unregister-watchdog-task.ps1
```


### 2) 웹 대시보드(초보자용 UI)

```powershell
.\scripts\start-dashboard.bat
```

PowerShell이 차단된 환경에서도 `.bat`만으로 실행됩니다.

### 3) 데스크톱 대시보드(Tkinter, 웹 브라우저 불필요)

```powershell
.\scripts\start-desktop-dashboard.bat
```

PowerShell이 차단된 환경에서도 `.bat`만으로 실행됩니다.

처음 실행 시에는 `requirements.txt`가 가상환경에 설치됩니다.

`TRADING_SYSTEM_PYTHON`를 미리 지정하면 사용하려는 Python 경로를 고정할 수 있습니다.

```powershell
$env:TRADING_SYSTEM_PYTHON = "C:\Python311\python.exe"
.\scripts\start-desktop-dashboard.bat
```

또는

```powershell
.\scripts\start-dashboard.bat
```

### 4) 실행 실패 시 체크

- Python이 경로에서 보이지 않으면: `TRADING_SYSTEM_PYTHON`을 절대 경로로 지정
- PowerShell 차단 환경: `scripts/*.bat`는 PowerShell을 호출하지 않고 Python을 직접 실행합니다.
- 첫 화면이 바로 안 뜨면: 설정 파일/권한 에러 메시지를 그대로 공유

### 5) 백테스트/워크포워드 검증

백테스트:

```powershell
py -m trading_system.main --config configs/default.json --backtest-cycles 300 --validation-report data\validation\backtest_report.json
```

워크포워드:

```powershell
py -m trading_system.main --config configs/default.json --walk-forward-windows 4 --walk-forward-train-cycles 80 --walk-forward-test-cycles 40 --validation-report data\validation\walk_forward_report.json
```

검증 게이트 기본값:
- 최소 체결 수: `--validation-min-trades 20`
- 최소 승률: `--validation-min-win-rate 0.45`
- 최소 손익: `--validation-min-pnl-usdt 0`
- 최대 드로우다운: `--validation-max-drawdown-pct 0.25`

검증 모드에서는 기본적으로 LLM 점수 반영을 끄고(rule-only) 실행합니다.
`--validation-use-llm`를 주면 설정된 LLM을 검증 모드에도 반영합니다.

### 6) 실거래 하드닝 (Live Guard)

실거래 모드(`--mode live`)에서는 시작 전에 preflight를 수행합니다.

- API 키/시크릿 존재 여부
- `exchange.allow_live=true` 여부
- 리스크 하드 리밋 초과 여부
- 알림 강제(`live_guard.enforce_notifications=true`)일 때 알림 활성 여부

또한 기본값으로 `live_guard.require_ack=true`이므로 시작 토큰이 필요합니다.

CLI 예시:

```powershell
py -m trading_system.main --config configs/default.json --mode live --live-confirm-token LIVE_OK --iterations 1
```

실거래 준비 점검만 실행:

```powershell
py -m trading_system.main --config configs/default.json --live-readiness
```

실거래 준비 점검 리포트 저장:

```powershell
py -m trading_system.main --config configs/default.json --live-readiness-report
```

거래소 파라미터 점검:

```powershell
py -m trading_system.main --config configs/default.json --exchange-probe
```

거래소 파라미터 점검 리포트 저장:

```powershell
py -m trading_system.main --config configs/default.json --exchange-probe-report
```

실체결 기반 PnL/수수료 정밀화(최근 업데이트):
- 실행내역에 `fee_usdt`, `gross_realized_pnl`, `realized_pnl(net)`이 함께 기록됩니다.
- 거래소가 수수료를 반환하면 해당 값을 우선 사용하고, live 모드에서 누락 시 설정 수수료율로 보정합니다.
- 웹/데스크톱 실행내역 표에서 수수료/Gross/Net을 확인할 수 있습니다.

웹 UI에서는 상단 `LIVE 시작 토큰` 입력창에 토큰을 넣고 `자동 시작`을 누르면 됩니다.
웹/데스크톱 UI의 `실거래 준비 점검`, `거래소 파라미터 점검` 버튼으로도 동일한 점검을 실행할 수 있습니다.

실거래 단계적 제한(`live_staging`)도 기본 활성화되어 있습니다.
- stage1: 소액 주문 캡
- stage2: 중간 주문 캡
- stage3: 확대 주문 캡
- 일일 손실이 `block_on_daily_loss_usdt` 아래로 내려가면 실거래 주문을 자동 차단

권장 거래소 타입(1차 고도화):
- Binance USDT-M 선물: `exchange.type = "binanceusdm"` (또는 `binance-futures`)
- Bybit 선물: `exchange.type = "bybit"` (별칭 일부 지원)

### 7) 자동 학습 루프 (매매복기 기반)

`configs/default.json`의 `auto_learning`을 켜면, 런타임이 주기적으로 복기 데이터를 기반으로
전략 가중치를 자동 조정합니다.

기본 안전 정책:
- `enabled=false` (기본 비활성)
- `paper_only=true` (dry/paper에서만 자동 반영)
- `apply_interval_cycles=20` (20사이클마다 검토)
- `max_weight_step_pct=0.2` (한 번에 가중치 20% 이내 조정)
- `max_strategy_changes_per_apply=3` (1회 최대 3개 전략 변경)

주의:
- 자동 학습은 **전략 설정만** 변경하며, 포지션/주문을 임의 종료하지 않습니다.
- `mode=live`에서는 `paper_only=true`일 때 자동 반영되지 않습니다.

### 8) 검증 게이트 (Validation Gate)

`validation_gate`는 검증 리포트가 통과된 경우에만
- `live` 시작
- 자동학습 자동 반영
을 허용합니다.

기본값:
- `enforce_for_live=true`
- `enforce_for_auto_learning=true`
- `report_path=data/validation/latest_validation_report.json`
- `history_path=data/validation/validation_history.jsonl`
- `allow_bypass=false`
- `bypass=false`
- `max_report_age_days=14`
- `alert_enabled=true`
- `alert_pass_rate_warn=0.60`, `alert_pass_rate_critical=0.40`
- `alert_max_drawdown_warn=0.25`, `alert_max_drawdown_critical=0.35`

보안/정책 이슈로 검증 실행이 막힐 때(임시 우회):
- 런처: `start-system.bat nogate web` 또는 `start-system.bat nogate desktop`
- 환경변수: `TRADING_SYSTEM_SKIP_VALIDATION_GATE=1`
- CLI: `py -m trading_system.main --skip-validation-gate ...`
- 설정 파일: `validation_gate.allow_bypass=true` + `validation_gate.bypass=true`

검증 실행 시 리포트는 지정 경로(`--validation-report`)와 함께
`validation_gate.report_path`에도 자동 저장됩니다.
또한 요약 스냅샷이 `validation_gate.history_path`에 누적됩니다.

검증 알람:
- 통과율 하락/최근 MDD 급등 시 `warn/critical` 경보를 생성합니다.
- 알림 전송은 기존 `notifications` 채널(Webhook/Slack/Telegram)을 그대로 사용합니다.
- 임계치는 웹/데스크톱 대시보드의 알림 설정 UI에서 바로 수정할 수 있습니다.
- 웹/데스크톱의 `검증 알람 테스트(경고/치명)` 버튼으로 채널 연결을 즉시 점검할 수 있습니다.

예시:
```powershell
py -m trading_system.main --config configs/default.json --backtest-cycles 300 --walk-forward-windows 3
```

대시보드:
- 데스크톱 UI: `검증 리포트 비교` 섹션에서 최근 N회 통과율/평균PnL/평균MDD와 상세 이력을 확인
- 웹 UI: `검증 리포트 비교 대시보드` 패널에서 동일 지표 확인

## 폴더 구성

- `src/trading_system/`: 핵심 실행 코드
  - `main.py`: CLI/웹 앱 진입점
  - `pipeline.py`: 매매 오케스트레이션
  - `runtime.py`: 반복 실행 상태 관리(대시보드 백그라운드 루프)
  - `ui.py`: FastAPI 기반 대시보드
  - `desktop_dashboard.py`: Tkinter 데스크톱 대시보드
- `configs/`: 설정 샘플
- `scripts/`: 실행 스크립트
  - `start-dashboard.bat`, `start-desktop-dashboard.bat`, `start-multi-dashboard.bat`, `start-multi-system.bat`
  - `run-trading-system.bat` (venv 자동 생성/의존성 확인, PowerShell 미사용)
- `docs/`: 시스템 문서
- `data/`: SQLite 기반 복기 DB

## LLM 실거래 보조점수 연동

`configs/default.json`의 `llm` 영역에서 `enabled`와 `provider`, `request_mode`를 켠 뒤 실행하면
선택 전 후보 정렬에 LLM 점수를 보조 반영합니다.

### 지원 모드
- `provider: mock` + `enabled: false` : 규칙 기반 정렬만 사용
- `provider: mock` + `enabled: true` : 로컬 규칙 점수(안전) 사용
- `request_mode: openai` : OpenAI 호환 엔드포인트 사용
- `request_mode: ollama` : Ollama `/api/chat` 형식 사용

### 권장 실행 플로우
1) UI에서 `llm.enabled=true`, `llm.api_key` 또는 `llm.api_key_env` 등록
2) 1회 실행 후 `/api/status` 또는 대시보드에서 `llm` 요약을 확인
3) 안정화 후 자동 루프 실행

### LLM 연결 테스트

CLI:
```powershell
py -m trading_system.main --config configs/default.json --llm-test
```

웹/데스크톱:
- 상단 `AI 연결 테스트` 버튼으로 즉시 점검 가능
- 결과는 `PASS/CHECK`로 표시되며 provider/status/scored 정보를 함께 보여줍니다.

환경변수 사용 시
- `OPENAI_API_KEY`(기본) 또는 `llm.api_key_env` 이름에 맞는 변수 등록



