# 운영 체크리스트

## 시작 전
- [ ] 거래소 API 권한 확인(조회용/주문용 분리)
- [ ] API 키는 키 관리에만 사용, 코드 하드코딩 금지
- [ ] `configs/default.json`의 risk_limits 값 점검
- [ ] 멀티 운용 시 `configs/multi_accounts.sample.json`(또는 실운영 파일) 프로파일별 config_path/enabled 점검
- [ ] 일일 손실 한도/포지션 한도 재설정
- [ ] 설치형 배포 시 `install-system.bat` 또는 배포본 `install.bat` 1회 실행
- [ ] `py -m trading_system.main --config configs/default.json --llm-test` 실행(PASS/CHECK 확인)
- [ ] `py -m trading_system.main --config configs/default.json --live-readiness-report` 실행(리포트 저장 확인)
- [ ] `py -m trading_system.main --config configs/default.json --exchange-probe-report` 실행(거래소 파라미터 점검 리포트 확인)
- [ ] `py -m trading_system.main --config configs/default.json --live-rehearsal-report` 실행(소액 staged runbook/실패 대응표 저장 확인)

## 1회 사이클 가동 검증
- [ ] config 로드 성공
- [ ] data 수집 성공
- [ ] 레짐 라벨 출력
- [ ] 후보 수집/스코어링 동작
- [ ] risk gate에서 거부/허용 로그 확인
- [ ] DB에 signal/execution 저장
- [ ] execution에서 `fee_usdt / gross_realized_pnl / realized_pnl(net)` 기록 확인

## 운영 중
- [ ] 잔고 이상치 체크(일일 감소)
- [ ] 실행 실패 이유 분포 모니터링
- [ ] `reasons`에서 특정 원인 과다 발생 시 즉시 중단
- [ ] 학습 제안(`docs`) 반영 전 소규모 테스트
- [ ] 멀티 운용 시 `start-system.bat multi ... status`로 프로파일별 상태 확인
- [ ] 멀티 통합 대시보드(`start-system.bat multi-ui ...`)에서 프로파일별 실행 상태 확인
- [ ] 멀티 통합 대시보드에서 프로파일별 준비점검/리스크 해제 결과 확인
- [ ] 멀티 통합 대시보드에서 프로파일별 AI 테스트/거래소 점검 결과 확인
- [ ] `start-system.bat healthcheck` 결과에서 필수 체크 PASS 확인
- [ ] `start-system.bat backup`으로 일일 백업 zip 생성 확인
- [ ] 장시간 운영 시 `start-system.bat watchdog ...` 실행 및 `logs/watchdog.log` 확인
- [ ] 상시 운영이면 `register-watchdog-task.ps1`로 로그온 자동실행 등록

## 주간 점검
- [ ] 전략별 승률/수익률/최대낙폭 확인
- [ ] 레짐 오분류 구간 식별
- [ ] 슬리피지 및 수수료 추정 오차 보정
- [ ] 다음 주 실거래 모드 전환 전 사전 점검(권장)
