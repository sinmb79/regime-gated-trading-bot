from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import Body, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from .runtime import TradingRuntime


def create_dashboard_app(config_path: str = "configs/default.json") -> FastAPI:
    config_path = str(Path(config_path))
    runtime = TradingRuntime(config_path)

    app = FastAPI(title="AI Trading Bot Dashboard", version="0.3.1")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
        allow_credentials=True,
    )

    @app.get("/", response_class=HTMLResponse)
    def index() -> str:
        return """<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>AI 트레이딩 봇 대시보드</title>
  <style>
    :root {
      --bg: linear-gradient(140deg, #0b1a36, #12213f 48%, #1d2f56);
      --panel: rgba(12, 22, 45, 0.94);
      --line: #2f3e5c;
      --text: #e6ecff;
      --muted: #9fb0d0;
      --ok: #22c55e;
      --warn: #f59e0b;
      --bad: #f87171;
      --accent: #3b82f6;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: "Pretendard", "Apple SD Gothic Neo", Arial, sans-serif;
      color: var(--text);
      background: var(--bg);
    }
    .wrap {
      max-width: 1200px;
      margin: 0 auto;
      padding: 16px;
      display: grid;
      gap: 12px;
    }
    .panel {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 14px;
      box-shadow: 0 8px 24px rgba(0,0,0,0.25);
    }
    h1, h2 { margin: 4px 0 12px; }
    .grid {
      display: grid;
      gap: 10px;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    }
    .metric {
      border: 1px solid #314267;
      border-radius: 10px;
      padding: 10px;
      background: rgba(8, 14, 28, 0.7);
    }
    .metric b { display: block; color: #bac7ea; font-size: 12px; margin-bottom: 6px; }
    .btn {
      border: 0;
      border-radius: 10px;
      padding: 10px 14px;
      font-weight: 700;
      cursor: pointer;
      background: var(--accent);
      color: white;
    }
    .btn-sub { background: #334155; }
    .btn-danger { background: #dc2626; }
    .btn-good { background: #14b8a6; }
    textarea {
      width: 100%;
      border: 1px solid #2f4166;
      border-radius: 10px;
      background: #070f24;
      color: #e5edff;
      padding: 10px;
      min-height: 260px;
      font-family: Menlo, Monaco, Consolas, "Courier New", monospace;
      font-size: 12px;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      font-size: 13px;
    }
    th, td {
      border-bottom: 1px solid #2f4166;
      padding: 7px;
      text-align: left;
      vertical-align: top;
    }
    th { color: #c8d4ee; }
    .muted { color: var(--muted); font-size: 12px; }
    .ok { color: var(--ok); }
    .warn { color: var(--warn); }
    .bad { color: var(--bad); }
    .canvas-wrap {
      border: 1px solid #2f4166;
      border-radius: 10px;
      padding: 8px;
      background: #070f24;
      height: 220px;
    }
    canvas { width: 100%; height: 100%; }
    .step {
      display: inline-block;
      margin-right: 8px;
      padding: 3px 10px;
      border-radius: 12px;
      border: 1px solid #44557d;
      color: #d5e0ff;
      background: #0e1731;
    }
    .step.active { background: #0b2a4f; color: #8dd4ff; }
    .step.done { background: #0f3b2a; color: #8cf7c5; }
    .step.warn { background: #41270f; color: #ffd28a; }
    .toolbar { display: flex; gap: 8px; flex-wrap: wrap; align-items: center; }
    input {
      background: #070f24;
      border: 1px solid #2f4166;
      color: #e5edff;
      border-radius: 10px;
      padding: 9px;
      min-width: 80px;
    }
    .small { font-size: 12px; }
    .badge-wrap {
      display: flex;
      gap: 6px;
      flex-wrap: wrap;
    }
    .reject-alert {
      border-left: 4px solid var(--warn);
      background: rgba(245, 158, 11, 0.12);
      padding: 8px 10px;
      border-radius: 10px;
      margin-bottom: 8px;
      font-size: 12px;
    }
    .reject-alert.critical {
      border-left-color: var(--bad);
      background: rgba(248, 113, 113, 0.12);
    }
    .reject-alert.ok {
      border-left-color: var(--ok);
      background: rgba(34, 197, 94, 0.12);
    }
    .reject-alert.info {
      border-left-color: #60a5fa;
      background: rgba(96, 165, 250, 0.12);
    }
    .reason-critical { color: var(--bad); }
    .reason-warn { color: var(--warn); }
    .reason-ok { color: var(--ok); }
    .form-grid {
      display: grid;
      gap: 8px;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    }
    .field {
      border: 1px solid #2f4166;
      border-radius: 10px;
      padding: 8px;
      background: rgba(7, 15, 36, 0.9);
    }
    .field label {
      font-size: 11px;
      color: var(--muted);
      display: block;
      margin-bottom: 4px;
    }
    .inline-check {
      display: inline-flex;
      gap: 6px;
      align-items: center;
      margin-right: 10px;
      color: var(--text);
      font-size: 12px;
    }
    .sketch-panel {
      border: 1px solid #3a4f77;
      background: linear-gradient(145deg, rgba(7, 16, 36, 0.95), rgba(11, 24, 49, 0.95));
    }
    .sketch-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 10px;
      flex-wrap: wrap;
      margin-bottom: 10px;
    }
    .sketch-tabs {
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
    }
    .sketch-tab {
      border: 1px solid #456091;
      background: rgba(14, 29, 58, 0.85);
      color: #e3ecff;
      border-radius: 10px;
      padding: 8px 12px;
      cursor: pointer;
      font-weight: 700;
    }
    .sketch-tab.active {
      background: linear-gradient(135deg, #1d4ed8, #0ea5e9);
      border-color: #8fc4ff;
      color: #ffffff;
    }
    .sketch-tab-cta {
      background: linear-gradient(135deg, #2563eb, #0ea5e9);
      border-color: #5fa6ff;
    }
    .sketch-statusline {
      display: flex;
      gap: 12px;
      flex-wrap: wrap;
      font-size: 12px;
      color: #a9bce0;
    }
    .sketch-layout {
      display: grid;
      grid-template-columns: 2.1fr 1fr;
      gap: 12px;
    }
    .sketch-main {
      border: 1px solid #35507d;
      border-radius: 12px;
      padding: 10px;
      background: rgba(5, 12, 27, 0.75);
      display: grid;
      gap: 10px;
    }
    .sketch-row {
      display: grid;
      grid-template-columns: 120px 1fr;
      gap: 10px;
    }
    .sketch-label {
      border: 1px solid #3f5f8f;
      border-radius: 10px;
      padding: 10px;
      font-weight: 700;
      font-size: 13px;
      color: #d7e3ff;
      background: rgba(13, 28, 57, 0.8);
      min-height: 78px;
      display: flex;
      align-items: center;
      justify-content: center;
      text-align: center;
    }
    .sketch-card {
      border: 1px solid #35507d;
      border-radius: 10px;
      padding: 10px;
      background: rgba(7, 15, 34, 0.8);
      min-height: 78px;
    }
    .sketch-list {
      margin: 0;
      padding-left: 18px;
      display: grid;
      gap: 6px;
      font-size: 13px;
      color: #e8eeff;
    }
    .sketch-note {
      border-top: 1px dashed #48638e;
      padding-top: 8px;
      color: #bfd2f8;
      font-size: 12px;
      display: grid;
      gap: 6px;
    }
    .sketch-side {
      border: 1px solid #35507d;
      border-radius: 12px;
      padding: 10px;
      background: rgba(5, 12, 27, 0.78);
      display: grid;
      align-content: start;
      gap: 10px;
    }
    .sketch-side h3 {
      margin: 2px 0 6px;
      font-size: 15px;
    }
    .sketch-side-box {
      border: 1px solid #3c5785;
      border-radius: 10px;
      padding: 8px;
      background: rgba(10, 20, 43, 0.82);
      display: grid;
      gap: 7px;
    }
    .sketch-mini-table th, .sketch-mini-table td {
      font-size: 12px;
      padding: 6px;
    }
    .sketch-error-line {
      margin-top: 6px;
      font-size: 12px;
      color: #f8be6b;
    }
    .sketch-list.compact {
      font-size: 12px;
      gap: 4px;
    }
    .sketch-inline {
      display: flex;
      gap: 6px;
      align-items: center;
      flex-wrap: wrap;
    }
    .sketch-inline input {
      min-width: 130px;
      flex: 1;
    }
    .btn-mini {
      padding: 6px 10px;
      border-radius: 8px;
      border: 1px solid #3f5b89;
      background: #243a66;
      color: #e4ebff;
      font-size: 12px;
      cursor: pointer;
    }
    .muted-box {
      color: #9fb0d0;
      font-size: 12px;
      border: 1px dashed #45628f;
      border-radius: 8px;
      padding: 6px;
      background: rgba(8, 15, 32, 0.72);
    }
    .sketch-tab-view { display: none; }
    .sketch-tab-view.active { display: block; }
    .theme-grid {
      display: grid;
      gap: 8px;
      grid-template-columns: repeat(2, minmax(120px, 1fr));
    }
    .theme-grid label {
      font-size: 11px;
      color: var(--muted);
      display: block;
      margin-bottom: 3px;
    }
    .theme-grid input[type="color"] {
      min-width: auto;
      width: 100%;
      height: 34px;
      padding: 4px;
      border-radius: 8px;
    }
    .strategy-edit-table {
      width: 100%;
      border-collapse: collapse;
      margin-top: 8px;
      font-size: 12px;
    }
    .strategy-edit-table th,
    .strategy-edit-table td {
      border-bottom: 1px solid #35507d;
      padding: 6px;
      text-align: left;
    }
    .strategy-edit-table input[type="number"] {
      width: 90px;
      min-width: 90px;
      padding: 6px;
    }
    @media (max-width: 900px) {
      .sketch-layout { grid-template-columns: 1fr; }
      .sketch-row { grid-template-columns: 1fr; }
      .sketch-label { min-height: auto; justify-content: flex-start; }
    }
  </style>
</head>
<body>
  <div class="wrap">
    <div class="panel">
      <h1>AI 트레이딩 봇 운영 대시보드</h1>
      <div class="toolbar">
        <button class="btn" onclick="runOnce()">1회 실행</button>
        <button class="btn btn-good" onclick="startLoop()">자동 시작</button>
        <button class="btn btn-danger" onclick="stopLoop()">중지</button>
        <button class="btn btn-sub" onclick="runLiveReadiness()">실거래 준비 점검</button>
        <button class="btn btn-sub" onclick="saveLiveReadinessReport()">점검 리포트 저장</button>
        <button class="btn btn-sub" onclick="runExchangeProbe()">거래소 파라미터 점검</button>
        <button class="btn btn-sub" onclick="saveExchangeProbeReport()">거래소 점검 리포트 저장</button>
        <button class="btn btn-sub" onclick="testLlmConnection()">AI 연결 테스트</button>
        <input id="intervalInput" type="number" min="1" value="5" />초
        <input id="liveConfirmTokenInput" type="text" placeholder="LIVE 시작 토큰" style="min-width:150px;" />
        <button class="btn btn-sub" onclick="refreshAll()">새로고침</button>
      </div>
      <div class="muted" style="margin-top:8px;">마지막 메시지: <span id="lastMessage">-</span></div>
      <div id="flowArea" style="margin-top:8px;"></div>
      <div id="liveReadinessArea" style="margin-top:8px;"></div>
      <div id="exchangeProbeArea" style="margin-top:8px;"></div>
      <div class="grid" id="overview" style="margin-top:10px;"></div>
    </div>

    <div class="panel">
      <h2>검증 리포트 비교 대시보드</h2>
      <div class="toolbar" style="margin-bottom:8px;">
        <button class="btn btn-sub" onclick="triggerValidationAlertTest('warn')">검증 알람 테스트(경고)</button>
        <button class="btn btn-sub" onclick="triggerValidationAlertTest('critical')">검증 알람 테스트(치명)</button>
      </div>
      <div class="grid" id="validationOverview"></div>
      <div id="validationAlertArea" style="margin-top:8px;"></div>
      <table style="margin-top:8px;">
        <thead>
          <tr>
            <th>시각</th>
            <th>전체통과</th>
            <th>Backtest</th>
            <th>WalkForward</th>
            <th>PnL(USDT)</th>
            <th>승률</th>
            <th>MDD</th>
          </tr>
        </thead>
        <tbody id="validationHistoryBody">
          <tr><td colspan="7" class="muted">검증 이력 없음</td></tr>
        </tbody>
      </table>
    </div>

    <div class="panel sketch-panel">
      <div class="sketch-header">
        <div class="sketch-tabs">
          <button class="sketch-tab sketch-tab-cta active" data-tab="start" onclick="setSketchTab('start')">시작</button>
          <button class="sketch-tab" data-tab="running" onclick="setSketchTab('running')">진행중인</button>
          <button class="sketch-tab" data-tab="settings" onclick="setSketchTab('settings')">내설정</button>
          <button class="sketch-tab" data-tab="api" onclick="setSketchTab('api')">연결 API</button>
          <button class="sketch-tab" data-tab="logging" onclick="setSketchTab('logging')">로깅</button>
        </div>
        <div class="sketch-statusline">
          <span id="sketchRunStatus">실행: -</span>
          <span id="sketchApiStatus">API: -</span>
          <span id="sketchLoopStatus">자동: -</span>
        </div>
      </div>
      <div class="sketch-layout">
        <div class="sketch-main">
          <section id="tab-start" class="sketch-tab-view active">
            <div class="toolbar" style="margin-bottom:8px;">
              <button class="btn btn-good" onclick="runOnce()">바로 1회 실행</button>
              <button class="btn btn-sub" onclick="startLoop()">자동 시작</button>
              <button class="btn btn-danger" onclick="stopLoop()">중지</button>
            </div>
            <div class="sketch-row">
              <div class="sketch-label">시황 분석</div>
              <div class="sketch-card">
                <ul id="sketchMarketAnalysis" class="sketch-list">
                  <li>데이터 대기 중...</li>
                </ul>
              </div>
            </div>
            <div class="sketch-note">
              <b>* 근거1 (뉴스/심리):</b>
              <ul id="sketchMarketEvidence" class="sketch-list compact">
                <li>아직 수집된 근거가 없습니다.</li>
              </ul>
            </div>
            <div class="sketch-row">
              <div class="sketch-label">매매 전략</div>
              <div class="sketch-card">
                <ul id="sketchStrategyList" class="sketch-list">
                  <li>전략 추천 대기 중...</li>
                </ul>
              </div>
            </div>
            <div class="sketch-note">
              <b>* 근거2:</b>
              <ul id="sketchStrategyEvidence" class="sketch-list compact">
                <li>전략 근거 대기 중...</li>
              </ul>
            </div>
            <div class="sketch-row">
              <div class="sketch-label">매매 봇</div>
              <div class="sketch-card">
                <ul id="sketchBotList" class="sketch-list">
                  <li>Grid / Trend / Defensive / Funding Arb / Indicator</li>
                </ul>
              </div>
            </div>
          </section>

          <section id="tab-running" class="sketch-tab-view">
            <div class="sketch-row">
              <div class="sketch-label">실시간 모니터링</div>
              <div class="sketch-card">
                <table class="sketch-mini-table">
                  <thead>
                    <tr>
                      <th>일시</th><th>종목</th><th>전략</th><th>상태</th><th>PnL</th>
                    </tr>
                  </thead>
                  <tbody id="sketchMonitorBody">
                    <tr><td colspan="5" class="muted">체결 데이터 대기 중...</td></tr>
                  </tbody>
                </table>
                <div id="sketchErrorLine" class="sketch-error-line">오류 점검: 정상</div>
              </div>
            </div>
            <div class="sketch-note">
              <b>* 진행 상태:</b>
              <ul id="sketchRunningMeta" class="sketch-list compact">
                <li>주기/상태 데이터 대기 중...</li>
              </ul>
            </div>
          </section>

          <section id="tab-settings" class="sketch-tab-view">
            <div class="sketch-row">
              <div class="sketch-label">내 설정</div>
              <div class="sketch-card">
                <ul id="sketchSettingsSummary" class="sketch-list">
                  <li>설정 요약 대기 중...</li>
                </ul>
                <div id="sketchStrategyEditor" style="margin-top:8px;">
                  <div class="muted">전략 설정 로딩 중...</div>
                </div>
                <div id="sketchRiskEditor" style="margin-top:10px;">
                  <div class="muted">리스크 설정 로딩 중...</div>
                </div>
                <div class="toolbar" style="margin-top:8px;">
                  <button class="btn btn-good" onclick="saveSketchStrategyConfig()">전략 설정 저장</button>
                  <button class="btn btn-good" onclick="saveSketchRiskConfig()">리스크 설정 저장</button>
                  <button class="btn btn-sub" onclick="goToConfig()">설정 JSON 이동</button>
                  <button class="btn btn-sub" onclick="loadConfig()">설정 다시 로드</button>
                </div>
              </div>
            </div>
          </section>

          <section id="tab-api" class="sketch-tab-view">
            <div class="sketch-row">
              <div class="sketch-label">API 상태</div>
              <div class="sketch-card">
                <ul id="sketchApiDetails" class="sketch-list">
                  <li>API 연결 상태 대기 중...</li>
                </ul>
                <div class="toolbar" style="margin-top:8px;">
                  <button class="btn btn-sub" onclick="runExchangeProbe()">거래소 파라미터 점검</button>
                  <button class="btn btn-sub" onclick="testLlmConnection()">AI 연결 테스트</button>
                </div>
                <div id="llmTestResult" class="muted-box" style="margin-top:8px;">아직 테스트를 실행하지 않았습니다.</div>
              </div>
            </div>
          </section>

          <section id="tab-logging" class="sketch-tab-view">
            <div class="sketch-row">
              <div class="sketch-label">운영 로깅</div>
              <div class="sketch-card">
                <table class="sketch-mini-table">
                  <thead>
                    <tr>
                      <th>시간</th><th>종목</th><th>상태</th><th>사유</th>
                    </tr>
                  </thead>
                  <tbody id="sketchLogBody">
                    <tr><td colspan="4" class="muted">로그 데이터 대기 중...</td></tr>
                  </tbody>
                </table>
                <div class="toolbar" style="margin-top:8px;">
                  <button class="btn btn-sub" onclick="goToLogging()">상세 실행내역 이동</button>
                </div>
              </div>
            </div>
          </section>
        </div>

        <aside class="sketch-side">
          <h3>소스 연동</h3>
          <div class="sketch-side-box">
            <b>심리 분석/리서치 소스</b>
            <ul class="sketch-list compact">
              <li>TradingView</li>
              <li>Google Trends</li>
              <li>VIX 지수</li>
            </ul>
            <div class="muted-box">사용자 소스는 아래에서 커스텀으로 추가합니다.</div>
          </div>
          <div class="sketch-side-box">
            <b>사용자 커스텀 소스</b>
            <div class="sketch-inline">
              <input id="sketchSourceInput" type="text" placeholder="예: https://example.com/feed" />
              <button class="btn-mini" onclick="addSketchSource()">추가</button>
            </div>
            <ul id="sketchSourceCustom" class="sketch-list compact">
              <li>등록된 커스텀 소스가 없습니다.</li>
            </ul>
          </div>
          <div class="sketch-side-box">
            <b>사용자 전략 메모</b>
            <textarea id="sketchStrategyMemo" rows="5" style="min-height:120px;" placeholder="사용자 전략 아이디어/규칙을 메모하세요."></textarea>
            <div class="sketch-inline">
              <button class="btn-mini" onclick="saveSketchMemo()">메모 저장</button>
            </div>
          </div>
          <div class="sketch-side-box">
            <b>UI 색상</b>
            <div class="sketch-inline">
              <select id="themePreset">
                <option value="ocean">Ocean</option>
                <option value="mono">Mono</option>
                <option value="forest">Forest</option>
                <option value="sunset">Sunset</option>
              </select>
              <button class="btn-mini" onclick="applyThemePreset()">프리셋 적용</button>
            </div>
            <div class="theme-grid">
              <div>
                <label for="themeBg1">배경 1</label>
                <input id="themeBg1" type="color" value="#0b1a36" />
              </div>
              <div>
                <label for="themeBg2">배경 2</label>
                <input id="themeBg2" type="color" value="#12213f" />
              </div>
              <div>
                <label for="themeBg3">배경 3</label>
                <input id="themeBg3" type="color" value="#1d2f56" />
              </div>
              <div>
                <label for="themeAccent">강조색</label>
                <input id="themeAccent" type="color" value="#3b82f6" />
              </div>
              <div>
                <label for="themePanel">패널색</label>
                <input id="themePanel" type="color" value="#0c162d" />
              </div>
              <div>
                <label for="themeLine">라인색</label>
                <input id="themeLine" type="color" value="#2f3e5c" />
              </div>
            </div>
            <div class="sketch-inline">
              <button class="btn-mini" onclick="applyCustomTheme()">색상 적용</button>
              <button class="btn-mini" onclick="resetTheme()">기본 복원</button>
            </div>
          </div>
        </aside>
      </div>
    </div>

    <div class="panel">
      <h2>계정/포지션</h2>
      <div class="grid" id="accountArea"></div>
      <div id="positionArea" class="muted"></div>
    </div>

    <div class="panel">
      <h2>리스크 상태</h2>
      <div class="grid" id="riskGuardArea"></div>
      <div class="toolbar" style="margin-top:8px;">
        <button id="clearRiskBtn" class="btn btn-sub" onclick="clearRiskHalt()" style="display:none;">리스크 해제</button>
      </div>
    </div>

    <div class="panel">
      <h2>리스크 이벤트</h2>
      <table>
        <thead>
          <tr>
            <th>시간</th><th>이벤트</th><th>이전 사유</th><th>현재 사유</th><th>비고</th>
          </tr>
        </thead>
        <tbody id="riskEventBody"></tbody>
      </table>
    </div>

    <div class="panel">
      <h2>거부사유 운영 대시보드</h2>
      <div id="rejectReasonAlertArea"></div>
      <div class="grid" id="rejectReasonSummary" style="margin-bottom: 8px;"></div>
      <table>
        <thead>
          <tr>
            <th>거부사유</th><th>건수</th><th>비율</th><th>상태</th>
          </tr>
        </thead>
        <tbody id="rejectReasonBody"></tbody>
      </table>
    </div>

    <div class="panel">
      <h2>레짐 기반 전략 추천</h2>
      <div id="strategyPlanSummary" class="grid" style="margin-bottom: 8px;"></div>
      <table>
        <thead>
          <tr>
            <th>종목</th>
            <th>레짐</th>
            <th>전략</th>
            <th>방향</th>
            <th>점수</th>
            <th>신뢰도</th>
            <th>이유</th>
          </tr>
        </thead>
        <tbody id="strategyPlanBody"></tbody>
      </table>
    </div>

    <div class="panel">
      <h2>수익 곡선</h2>
      <div class="canvas-wrap"><canvas id="pnlChart"></canvas></div>
      <div id="pnlSummary" class="muted" style="margin-top:6px;"></div>
    </div>

    <div class="panel">
      <h2>실행 내역</h2>
      <div class="toolbar" style="margin-bottom:8px; gap:6px;">
        <span class="muted">상태</span>
        <select id="execStatusFilter" onchange="renderExecutions()">
          <option value="">전체</option>
          <option value="filled">filled</option>
          <option value="partially_filled">partially_filled</option>
          <option value="rejected">rejected</option>
          <option value="cancelled">cancelled</option>
        </select>
        <span class="muted">부분체결</span>
        <select id="execPartialFilter" onchange="renderExecutions()">
          <option value="">전체</option>
          <option value="true">있음</option>
          <option value="false">아님</option>
        </select>
        <span class="muted">거부사유</span>
        <select id="execRejectFilter" onchange="renderExecutions()">
          <option value="">전체</option>
          <option value="risk_rejected">risk_rejected</option>
          <option value="invalid_position_size">invalid_position_size</option>
          <option value="insufficient_cash">insufficient_cash</option>
          <option value="invalid_size">invalid_size</option>
          <option value="invalid_order">invalid_order</option>
          <option value="invalid_order_value">invalid_order_value</option>
          <option value="unsupported_side">unsupported_side</option>
          <option value="partial_fill_zero">partial_fill_zero</option>
          <option value="partial_fill">partial_fill</option>
          <option value="live_staging_guard">live_staging_guard</option>
          <option value="timeout">timeout</option>
          <option value="network_error">network_error</option>
          <option value="auth_error">auth_error</option>
          <option value="rate_limit">rate_limit</option>
          <option value="exchange_reject">exchange_reject</option>
          <option value="unknown_reject">unknown_reject</option>
        </select>
        <button class="btn btn-sub" onclick="renderExecutions()">조회</button>
      </div>
      <table>
        <thead>
          <tr>
            <th>시간</th><th>전략</th><th>종목</th><th>방향</th><th>상태</th><th>요청금액(USDT)</th><th>체결금액(USDT)</th><th>레버리지</th><th>예상가</th><th>체결가</th><th>슬리피지(bps)</th><th>시도</th><th>재시도사유</th><th>수수료(USDT)</th><th>GrossPnL</th><th>NetPnL</th>
          </tr>
        </thead>
        <tbody id="executionBody"></tbody>
      </table>
    </div>

    <div class="panel">
      <h2>AI 복기/튜닝</h2>
      <div class="toolbar">
        <span class="muted">회고 기간</span>
        <input id="windowDays" type="number" min="1" max="60" value="14" />일
        <button class="btn btn-sub" onclick="loadLearning()">분석 조회</button>
        <button class="btn btn-sub" onclick="applyLearning('selected')">선택 전략 적용</button>
        <button class="btn btn-good" onclick="applyLearning('all')">전체 제안 일괄 적용</button>
      </div>
      <div id="learningMsg" class="muted" style="margin:8px 0;"></div>
      <table>
        <thead>
          <tr>
            <th>적용</th><th>전략</th><th>제안</th><th>현재 가중치</th><th>제안 가중치</th><th>신뢰도</th><th>사유</th>
          </tr>
        </thead>
        <tbody id="learningBody"></tbody>
      </table>
    </div>

    <div class="panel">
      <h2>거부사유 알림/임계치</h2>
      <div class="form-grid">
        <div class="field">
          <label>알림 사용</label>
          <label class="inline-check">
            <input id="notifyEnabled" type="checkbox" />
            사용
          </label>
        </div>
        <div class="field">
          <label>알림 발송 레벨</label>
          <label class="inline-check"><input id="notifyLevelCritical" type="checkbox" /> critical</label>
          <label class="inline-check"><input id="notifyLevelWarn" type="checkbox" /> warn</label>
          <label class="inline-check"><input id="notifyLevelInfo" type="checkbox" /> info</label>
        </div>
        <div class="field">
          <label>임계치 모드</label>
          <select id="rejectAlertProfile">
            <option value="auto">auto</option>
            <option value="safe">safe</option>
            <option value="balanced">balanced</option>
            <option value="aggressive">aggressive</option>
          </select>
        </div>
        <div class="field">
          <label>거부율 경고 임계치</label>
          <input id="rejectRateWarnInput" type="number" step="0.01" min="0" max="1" />
        </div>
        <div class="field">
          <label>거부율 critical 임계치</label>
          <input id="rejectRateCriticalInput" type="number" step="0.01" min="0" max="1" />
        </div>
        <div class="field">
          <label>거부사유 경고 임계치</label>
          <input id="rejectReasonWarnInput" type="number" step="0.01" min="0" max="1" />
        </div>
        <div class="field">
          <label>거부사유 critical 임계치</label>
          <input id="rejectReasonCriticalInput" type="number" step="0.01" min="0" max="1" />
        </div>
        <div class="field">
          <label>최소 샘플 수</label>
          <input id="rejectReasonMinSamplesInput" type="number" min="1" />
        </div>
        <div class="field">
          <label>쿨다운(초)</label>
          <input id="notifyCooldownSeconds" type="number" min="0" />
        </div>
        <div class="field">
          <label>시간당 발송 상한(0=무제한)</label>
          <input id="notifyMaxPerHour" type="number" min="0" />
        </div>
        <div class="field">
          <label>일반 웹훅 URL</label>
          <input id="notifyWebhook" type="text" />
        </div>
        <div class="field">
          <label>Slack 웹훅 URL</label>
          <input id="notifySlackWebhook" type="text" />
        </div>
        <div class="field">
          <label>텔레그램 Bot Token</label>
          <input id="notifyTelegramToken" type="text" placeholder="[HIDDEN]" />
        </div>
        <div class="field">
          <label>텔레그램 Chat ID</label>
          <input id="notifyTelegramChatId" type="text" placeholder="[HIDDEN]" />
        </div>
        <div class="field">
          <label>메세지 상세 요약</label>
          <label class="inline-check">
            <input id="notifyIncludeSummary" type="checkbox" /> 포함
          </label>
        </div>
      </div>
      <div class="toolbar" style="margin-top:8px; gap:8px;">
        <button class="btn btn-good" onclick="saveNotificationConfig()">알림 설정만 저장</button>
        <button class="btn btn-sub" onclick="loadConfig()">설정값 다시 불러오기</button>
      </div>
    </div>

    <div class="panel">
      <h2>설정 편집</h2>
      <div class="toolbar" style="margin-bottom:8px;">
        <button class="btn btn-sub" onclick="loadConfig()">설정 불러오기</button>
        <button class="btn btn-good" onclick="saveConfig()">저장</button>
      </div>
      <textarea id="configJson" rows="20"></textarea>
      <p class="muted" style="margin-top:8px;">API 비밀값은 화면에서 [HIDDEN]로 표시되며, 저장 시 그대로 유지됩니다.</p>
    </div>
  </div>

  <script>
    const POLL_MS = 3000;
    let clearState = { lockUntil: 0, failCount: 0 };
    const SKETCH_SOURCE_KEY = 'boss_sketch_sources_v1';
    const SKETCH_MEMO_KEY = 'boss_sketch_memo_v1';
    const SKETCH_TAB_KEY = 'boss_sketch_tab_v1';
    const SKETCH_THEME_KEY = 'boss_sketch_theme_v1';
    const THEME_PRESETS = {
      ocean: { bg1: '#0b1a36', bg2: '#12213f', bg3: '#1d2f56', accent: '#3b82f6', panel: '#0c162d', line: '#2f3e5c' },
      mono: { bg1: '#151515', bg2: '#1f1f1f', bg3: '#2b2b2b', accent: '#b7c0cc', panel: '#1a1a1a', line: '#414141' },
      forest: { bg1: '#0d2017', bg2: '#133424', bg3: '#194932', accent: '#22c55e', panel: '#10271c', line: '#2f5b44' },
      sunset: { bg1: '#2a1620', bg2: '#3f1d2f', bg3: '#5b2d43', accent: '#f97316', panel: '#271724', line: '#63405a' },
    };

    function hexToRgba(hex, alpha) {
      const value = String(hex || '').trim();
      const h = value.replace('#', '');
      if (!/^[0-9a-fA-F]{6}$/.test(h)) return `rgba(12,22,45,${alpha})`;
      const r = parseInt(h.slice(0, 2), 16);
      const g = parseInt(h.slice(2, 4), 16);
      const b = parseInt(h.slice(4, 6), 16);
      return `rgba(${r},${g},${b},${alpha})`;
    }

    function readStoredTheme() {
      try {
        const raw = localStorage.getItem(SKETCH_THEME_KEY);
        const parsed = JSON.parse(raw || '{}');
        if (!parsed || typeof parsed !== 'object') return null;
        return parsed;
      } catch (_e) {
        return null;
      }
    }

    function getThemeFromInputs() {
      return {
        bg1: document.getElementById('themeBg1').value,
        bg2: document.getElementById('themeBg2').value,
        bg3: document.getElementById('themeBg3').value,
        accent: document.getElementById('themeAccent').value,
        panel: document.getElementById('themePanel').value,
        line: document.getElementById('themeLine').value,
      };
    }

    function setThemeInputs(theme) {
      if (!theme) return;
      const set = (id, v) => {
        const node = document.getElementById(id);
        if (node && typeof v === 'string') node.value = v;
      };
      set('themeBg1', theme.bg1);
      set('themeBg2', theme.bg2);
      set('themeBg3', theme.bg3);
      set('themeAccent', theme.accent);
      set('themePanel', theme.panel);
      set('themeLine', theme.line);
    }

    function applyTheme(theme, persist) {
      const selected = theme || THEME_PRESETS.ocean;
      const root = document.documentElement;
      root.style.setProperty('--bg', `linear-gradient(140deg, ${selected.bg1}, ${selected.bg2} 48%, ${selected.bg3})`);
      root.style.setProperty('--accent', selected.accent);
      root.style.setProperty('--panel', hexToRgba(selected.panel, 0.94));
      root.style.setProperty('--line', selected.line);
      if (persist !== false) {
        localStorage.setItem(SKETCH_THEME_KEY, JSON.stringify(selected));
      }
      setThemeInputs(selected);
    }

    function applyThemePreset() {
      const node = document.getElementById('themePreset');
      const key = node ? node.value : 'ocean';
      const preset = THEME_PRESETS[key] || THEME_PRESETS.ocean;
      applyTheme(preset, true);
      document.getElementById('lastMessage').textContent = `UI 색상 프리셋 적용: ${key}`;
    }

    function applyCustomTheme() {
      applyTheme(getThemeFromInputs(), true);
      document.getElementById('lastMessage').textContent = '커스텀 UI 색상을 적용했습니다.';
    }

    function resetTheme() {
      applyTheme(THEME_PRESETS.ocean, true);
      const preset = document.getElementById('themePreset');
      if (preset) preset.value = 'ocean';
      document.getElementById('lastMessage').textContent = 'UI 색상을 기본값으로 복원했습니다.';
    }

    function loadTheme() {
      const stored = readStoredTheme();
      applyTheme(stored || THEME_PRESETS.ocean, false);
    }

    function setSketchTab(tab) {
      const name = String(tab || 'start');
      const valid = ['start', 'running', 'settings', 'api', 'logging'];
      const selected = valid.includes(name) ? name : 'start';
      localStorage.setItem(SKETCH_TAB_KEY, selected);

      document.querySelectorAll('.sketch-tab').forEach((btn) => {
        btn.classList.toggle('active', btn.getAttribute('data-tab') === selected);
      });

      document.querySelectorAll('.sketch-tab-view').forEach((pane) => {
        pane.classList.remove('active');
      });
      const pane = document.getElementById(`tab-${selected}`);
      if (pane) pane.classList.add('active');
    }

    function initSketchTabs() {
      const saved = localStorage.getItem(SKETCH_TAB_KEY) || 'start';
      setSketchTab(saved);
    }

    function goToConfig() {
      const node = document.getElementById('configJson');
      if (node) node.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }

    function goToLogging() {
      const node = document.getElementById('executionBody');
      if (node) node.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }

    function readSketchSources() {
      try {
        const raw = localStorage.getItem(SKETCH_SOURCE_KEY);
        const parsed = JSON.parse(raw || '[]');
        if (!Array.isArray(parsed)) return [];
        return parsed.filter((x) => typeof x === 'string' && x.trim().length > 0).slice(0, 20);
      } catch (_e) {
        return [];
      }
    }

    function writeSketchSources(values) {
      localStorage.setItem(SKETCH_SOURCE_KEY, JSON.stringify(values || []));
    }

    function renderSketchSources() {
      const node = document.getElementById('sketchSourceCustom');
      if (!node) return;
      const values = readSketchSources();
      if (!values.length) {
        node.innerHTML = '<li>등록된 커스텀 소스가 없습니다.</li>';
        return;
      }
      node.innerHTML = values.map((item, idx) => `
        <li>
          <span>${item}</span>
          <button class="btn-mini" style="margin-left:6px;" onclick="removeSketchSource(${idx})">삭제</button>
        </li>
      `).join('');
    }

    function addSketchSource() {
      const input = document.getElementById('sketchSourceInput');
      if (!input) return;
      const value = String(input.value || '').trim();
      if (!value) return;
      const values = readSketchSources();
      if (values.includes(value)) {
        document.getElementById('lastMessage').textContent = '이미 등록된 커스텀 소스입니다.';
        return;
      }
      values.unshift(value);
      writeSketchSources(values.slice(0, 20));
      input.value = '';
      renderSketchSources();
      document.getElementById('lastMessage').textContent = '커스텀 소스를 추가했습니다.';
    }

    function removeSketchSource(index) {
      const values = readSketchSources();
      const i = Number(index);
      if (!Number.isInteger(i) || i < 0 || i >= values.length) return;
      values.splice(i, 1);
      writeSketchSources(values);
      renderSketchSources();
      document.getElementById('lastMessage').textContent = '커스텀 소스를 삭제했습니다.';
    }

    function loadSketchMemo() {
      const node = document.getElementById('sketchStrategyMemo');
      if (!node) return;
      node.value = localStorage.getItem(SKETCH_MEMO_KEY) || '';
    }

    function saveSketchMemo() {
      const node = document.getElementById('sketchStrategyMemo');
      if (!node) return;
      localStorage.setItem(SKETCH_MEMO_KEY, String(node.value || ''));
      document.getElementById('lastMessage').textContent = '전략 메모를 저장했습니다.';
    }

    function renderSketchStrategyEditor(cfg) {
      const wrap = document.getElementById('sketchStrategyEditor');
      if (!wrap) return;
      const config = cfg || {};
      const strategies = config.strategies || {};
      const names = Object.keys(strategies).sort();
      if (!names.length) {
        wrap.innerHTML = '<div class="muted">전략 설정이 없습니다.</div>';
        return;
      }

      const rows = names.map((name) => {
        const item = strategies[name] || {};
        const enabled = !(item && item.enabled === false);
        const weight = Number(item.weight ?? 1.0);
        const safeWeight = Number.isFinite(weight) ? weight : 1.0;
        return `
          <tr data-strategy="${name}">
            <td>${name}</td>
            <td><input type="checkbox" class="sketch-strategy-enabled" ${enabled ? 'checked' : ''} /></td>
            <td><input type="number" step="0.05" min="0" max="3" class="sketch-strategy-weight" value="${safeWeight.toFixed(2)}" /></td>
          </tr>
        `;
      }).join('');

      wrap.innerHTML = `
        <table class="strategy-edit-table">
          <thead>
            <tr>
              <th>전략</th><th>사용</th><th>가중치</th>
            </tr>
          </thead>
          <tbody>${rows}</tbody>
        </table>
      `;
    }

    function renderSketchRiskEditor(cfg) {
      const wrap = document.getElementById('sketchRiskEditor');
      if (!wrap) return;
      const config = cfg || {};
      const limits = config.risk_limits || {};
      const fields = [
        { key: 'daily_max_loss_pct', label: '일일 최대손실(비율)', step: '0.005', min: '0', max: '1', type: 'float' },
        { key: 'max_total_exposure', label: '총 노출 상한(비율)', step: '0.01', min: '0', max: '1', type: 'float' },
        { key: 'max_symbol_exposure', label: '종목 노출 상한(비율)', step: '0.01', min: '0', max: '1', type: 'float' },
        { key: 'max_open_positions', label: '최대 포지션 수', step: '1', min: '1', max: '30', type: 'int' },
        { key: 'max_daily_trades', label: '일일 최대 거래수', step: '1', min: '1', max: '500', type: 'int' },
        { key: 'max_leverage', label: '최대 레버리지', step: '0.5', min: '1', max: '20', type: 'float' },
        { key: 'min_signal_confidence', label: '최소 신호 신뢰도', step: '0.01', min: '0', max: '1', type: 'float' },
        { key: 'max_slippage_bps', label: '최대 슬리피지(bps)', step: '1', min: '1', max: '300', type: 'float' },
        { key: 'min_expectancy_pct', label: '최소 기대수익(비율)', step: '0.005', min: '0', max: '1', type: 'float' },
        { key: 'cooldown_minutes', label: '쿨다운(분)', step: '1', min: '0', max: '240', type: 'int' },
        { key: 'max_consecutive_losses', label: '최대 연속손실', step: '1', min: '1', max: '20', type: 'int' },
        { key: 'max_reject_ratio', label: '최대 거부율(비율)', step: '0.01', min: '0', max: '1', type: 'float' },
      ];

      const rows = fields.map((field) => {
        const raw = limits[field.key];
        const fallback = field.type === 'int' ? 1 : 0;
        const v = Number(raw ?? fallback);
        const safe = Number.isFinite(v) ? v : fallback;
        const value = field.type === 'int' ? String(Math.round(safe)) : safe.toFixed(3);
        return `
          <tr>
            <td>${field.label}</td>
            <td>
              <input
                type="number"
                class="sketch-risk-input"
                data-risk-key="${field.key}"
                data-risk-type="${field.type}"
                step="${field.step}"
                min="${field.min}"
                max="${field.max}"
                value="${value}"
              />
            </td>
          </tr>
        `;
      }).join('');

      wrap.innerHTML = `
        <table class="strategy-edit-table">
          <thead>
            <tr>
              <th>리스크 항목</th><th>값</th>
            </tr>
          </thead>
          <tbody>${rows}</tbody>
        </table>
      `;
    }

    async function saveSketchStrategyConfig() {
      try {
        const rows = [...document.querySelectorAll('#sketchStrategyEditor tr[data-strategy]')];
        if (!rows.length) {
          document.getElementById('lastMessage').textContent = '저장할 전략 설정이 없습니다.';
          return;
        }

        const payload = { strategies: {} };
        for (const row of rows) {
          const name = row.getAttribute('data-strategy');
          if (!name) continue;
          const enabledNode = row.querySelector('.sketch-strategy-enabled');
          const weightNode = row.querySelector('.sketch-strategy-weight');
          const enabled = !!(enabledNode && enabledNode.checked);
          const rawWeight = Number(weightNode ? weightNode.value : 1);
          const weight = Number.isFinite(rawWeight) ? Math.min(3, Math.max(0, rawWeight)) : 1.0;
          payload.strategies[name] = {
            enabled: enabled,
            weight: Number(weight.toFixed(2)),
          };
        }

        await apiPost('/api/config', payload);
        document.getElementById('lastMessage').textContent = '전략 ON/OFF 및 가중치를 저장했습니다.';
        await loadConfig();
        await refreshAll();
      } catch (e) {
        document.getElementById('lastMessage').textContent = '전략 설정 저장 실패: ' + e.message;
      }
    }

    async function saveSketchRiskConfig() {
      try {
        const inputs = [...document.querySelectorAll('#sketchRiskEditor .sketch-risk-input')];
        if (!inputs.length) {
          document.getElementById('lastMessage').textContent = '저장할 리스크 설정이 없습니다.';
          return;
        }

        const limits = {};
        for (const input of inputs) {
          const key = input.getAttribute('data-risk-key');
          const type = input.getAttribute('data-risk-type');
          if (!key) continue;
          const raw = Number(input.value);
          if (!Number.isFinite(raw)) continue;

          const min = Number(input.min);
          const max = Number(input.max);
          let value = raw;
          if (Number.isFinite(min)) value = Math.max(min, value);
          if (Number.isFinite(max)) value = Math.min(max, value);
          if (type === 'int') {
            value = Math.round(value);
          } else {
            value = Number(value.toFixed(6));
          }
          limits[key] = value;
        }

        await apiPost('/api/config', { risk_limits: limits });
        document.getElementById('lastMessage').textContent = '리스크 설정을 저장했습니다.';
        await loadConfig();
        await refreshAll();
      } catch (e) {
        document.getElementById('lastMessage').textContent = '리스크 설정 저장 실패: ' + e.message;
      }
    }

    function renderSketchConfigSummary(cfg) {
      const config = cfg || {};
      const strategies = config.strategies || {};
      const enabledStrategies = Object.entries(strategies).filter(([, v]) => !(v && v.enabled === false)).map(([k]) => k);
      const exchange = config.exchange || {};
      const llm = config.llm || {};
      const llmTest = window.__lastLlmTest || null;
      const exchangeProbe = window.__lastExchangeProbe || null;
      const mode = config.mode || '-';

      const summary = document.getElementById('sketchSettingsSummary');
      if (summary) {
        summary.innerHTML = `
          <li>모드: ${mode}</li>
          <li>활성 전략: ${enabledStrategies.slice(0, 6).join(', ') || '-'}</li>
          <li>거래소 타입: ${exchange.type || '-'}, testnet=${exchange.testnet ? 'ON' : 'OFF'}</li>
          <li>리스크 max leverage: ${(config.risk_limits || {}).max_leverage || '-'}</li>
        `;
      }

      const apiNode = document.getElementById('sketchApiDetails');
      if (apiNode) {
        const probeLine = exchangeProbe
          ? `<li>거래소 점검: ${exchangeProbe.overall_passed ? 'PASS' : 'CHECK'} / critical=${exchangeProbe.critical_failures || 0}</li>`
          : '<li>거래소 점검: 미실행</li>';
        const llmTestLine = llmTest
          ? `<li>LLM 테스트: ${llmTest.passed ? 'PASS' : 'FAIL'} / ${llmTest.status || '-'}</li>`
          : '<li>LLM 테스트: 미실행</li>';
        apiNode.innerHTML = `
          <li>거래소 API Key: ${exchange.api_key ? '입력됨' : '미입력'}</li>
          <li>거래소 Secret: ${exchange.api_secret ? '입력됨' : '미입력'}</li>
          ${probeLine}
          <li>LLM 사용: ${llm.enabled ? 'ON' : 'OFF'} / ${llm.provider || '-'}</li>
          <li>LLM Key: ${llm.api_key ? '입력됨' : '미입력'}</li>
          ${llmTestLine}
        `;
      }

      renderSketchStrategyEditor(config);
      renderSketchRiskEditor(config);
    }

    function renderSketchTop(status) {
      const runNode = document.getElementById('sketchRunStatus');
      const apiNode = document.getElementById('sketchApiStatus');
      const loopNode = document.getElementById('sketchLoopStatus');
      const preflight = status.live_preflight || {};
      if (runNode) runNode.textContent = `실행: ${status.running ? '동작중' : '정지'}`;
      if (apiNode) apiNode.textContent = `API: ${status.exchange || '-'} / ${status.testnet ? 'testnet' : 'mainnet'}`;
      if (loopNode) loopNode.textContent = `자동: ${status.interval_seconds || '-'}초 / cycle ${status.cycle_count || 0}`;

      const runningMeta = document.getElementById('sketchRunningMeta');
      const cycle = status.last_cycle || {};
      if (runningMeta) {
        runningMeta.innerHTML = `
          <li>선택 후보: ${cycle.selected || 0}건</li>
          <li>실행/거부: ${cycle.executed || 0} / ${cycle.rejected || 0}</li>
          <li>최근 에러: ${status.last_error || '없음'}</li>
          <li>Live preflight: ${preflight.passed ? 'PASS' : 'CHECK'}</li>
        `;
      }

      renderSketchConfigSummary(status.config || {});
    }

    function renderSketchMonitor(rows) {
      const body = document.getElementById('sketchMonitorBody');
      if (!body) return;

      const list = (rows || []).slice(0, 8);
      if (!list.length) {
        body.innerHTML = '<tr><td colspan="5" class="muted">체결 데이터 대기 중...</td></tr>';
      } else {
        body.innerHTML = list.map((r) => `
          <tr>
            <td>${(r.ts || '-').toString().slice(0, 19)}</td>
            <td>${r.symbol || '-'}</td>
            <td>${r.strategy || '-'}</td>
            <td>${r.order_status || '-'}</td>
            <td>${Number(r.realized_pnl || 0).toFixed(2)}</td>
          </tr>
        `).join('');
      }

      const rejected = list.filter((x) => String(x.order_status || '') === 'rejected');
      const text = rejected.length
        ? `오류 점검: 최근 ${list.length}건 중 거부 ${rejected.length}건 (${rejected[0].reject_reason || 'unknown'})`
        : '오류 점검: 최근 실행 정상';
      const errNode = document.getElementById('sketchErrorLine');
      if (errNode) errNode.textContent = text;

      const logBody = document.getElementById('sketchLogBody');
      if (logBody) {
        logBody.innerHTML = list.length ? list.map((r) => `
          <tr>
            <td>${(r.ts || '-').toString().slice(0, 19)}</td>
            <td>${r.symbol || '-'}</td>
            <td>${r.order_status || '-'}</td>
            <td>${r.reject_reason || '-'}</td>
          </tr>
        `).join('') : '<tr><td colspan="4" class="muted">로그 데이터 대기 중...</td></tr>';
      }
    }

    async function apiGet(path) {
      const response = await fetch(path);
      if (!response.ok) throw new Error(await response.text());
      return response.json();
    }

    async function apiPost(path, body) {
      const response = await fetch(path, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body || {}),
      });
      if (!response.ok) throw new Error(await response.text());
      return response.json();
    }

    function statusBadge(text, ok) {
      const cls = ok ? 'ok' : 'bad';
      return `<span class="${cls}">${text}</span>`;
    }

    function numberOrText(v) {
      if (typeof v === 'number' && Number.isFinite(v)) return v.toFixed(2);
      if (typeof v === 'string') return v;
      return '-';
    }

    function percentOrText(v, fallback='-') {
      return (typeof v === 'number' && Number.isFinite(v)) ? `${(v * 100).toFixed(2)}%` : fallback;
    }

    function renderFlow(cycle, halted) {
      const steps = [
        '시장분석',
        '시그널 생성',
        '리스크 게이트',
        '실행/반려',
        '복기 로그'
      ];
      const marks = [];
      const selected = cycle.selected || 0;
      marks.push(`<span class="step ${selected > 0 ? 'done' : 'warn'}">1) ${steps[0]}</span>`);
      marks.push(`<span class="step ${selected > 0 ? 'done' : 'warn'}">2) ${steps[1]}</span>`);
      marks.push(`<span class="step ${selected >= 0 ? 'done' : 'warn'}">3) ${steps[2]}</span>`);
      marks.push(`<span class="step ${selected > 0 ? 'done' : 'warn'}">4) ${steps[3]}</span>`);
      marks.push(`<span class="step ${halted ? 'warn' : 'active'}">5) ${steps[4]}</span>`);
      document.getElementById('flowArea').innerHTML = marks.join('');
    }

    function renderOverview(status) {
      const rejectAlert = status.reject_alert || {};
      const rejectAlertThresholds = rejectAlert.thresholds || {};
      const preflight = status.live_preflight || {};
      const liveGuard = status.live_guard || {};
      const liveStaging = status.live_staging || {};
      const resolvedWarn = rejectAlertThresholds.warn == null ? null : (rejectAlertThresholds.warn * 100);
      const resolvedCritical = rejectAlertThresholds.critical == null ? null : (rejectAlertThresholds.critical * 100);
      const stagingStage = Number(liveStaging.stage || 0);
      const stagingCap = Number(liveStaging.max_order_usdt || 0);
      const stagingTrades = Number(liveStaging.today_trades || 0);
      const stagingPnl = Number(liveStaging.today_pnl || 0);
      const stagingStatus = !liveStaging.enabled
        ? 'OFF'
        : (liveStaging.active ? `Stage ${stagingStage || 1}` : '대기');
      document.getElementById('overview').innerHTML = `
        <div class="metric"><b>실행 상태</b>${status.running ? statusBadge('동작중', true) : statusBadge('정지', false)}</div>
        <div class="metric"><b>모드</b>${status.mode}</div>
        <div class="metric"><b>사이클</b>${status.cycle_count}</div>
        <div class="metric"><b>주기</b>${status.interval_seconds}초</div>
        <div class="metric"><b>거래소</b>${status.exchange}</div>
        <div class="metric"><b>실거래 허용</b>${status.allow_live ? 'ON' : 'OFF'}</div>
        <div class="metric"><b>테스트넷</b>${status.testnet ? 'ON' : 'OFF'}</div>
        <div class="metric"><b>거부 알림</b>${rejectAlert.enabled ? 'ON' : 'OFF'} / ${rejectAlert.profile || 'auto'}</div>
        <div class="metric"><b>거부 알림 임계치</b>${resolvedWarn == null ? "-" : resolvedWarn.toFixed(1) + "%"} / ${resolvedCritical == null ? "-" : resolvedCritical.toFixed(1) + "%"}</div>
        <div class="metric"><b>최근 알림시각</b>${rejectAlert.last_alert_ts ? new Date(rejectAlert.last_alert_ts).toLocaleString() : '없음'}</div>
        <div class="metric"><b>Live Preflight</b>${preflight.passed ? '<span class="ok">PASS</span>' : '<span class="warn">CHECK</span>'}</div>
        <div class="metric"><b>Live Staging</b>${stagingStatus}</div>
        <div class="metric"><b>주문 캡(USDT)</b>${stagingCap > 0 ? stagingCap.toFixed(2) : '-'}</div>
        <div class="metric"><b>당일 실거래</b>${stagingTrades}회 / PnL ${stagingPnl.toFixed(2)}</div>
        <div class="metric"><b>Staging 차단</b>${liveStaging.blocked ? '<span class="bad">BLOCK</span>' : '<span class="ok">OK</span>'}</div>
      `;
      const tokenInput = document.getElementById('liveConfirmTokenInput');
      if (tokenInput && liveGuard.confirm_token_hint) {
        tokenInput.placeholder = `LIVE 시작 토큰 (${liveGuard.confirm_token_hint})`;
      }
      renderSketchTop(status);
    }

    function renderAccount(status) {
      const b = status.balance || {};
      const open = status.positions || {};
      document.getElementById('accountArea').innerHTML = `
        <div class="metric"><b>USDT</b>${numberOrText(b.USDT)}</div>
        <div class="metric"><b>Equity</b>${numberOrText(b.equity_usdt)}</div>
        <div class="metric"><b>총 포지션 Notional</b>${numberOrText(b.notional_exposure)}</div>
        <div class="metric"><b>포지션 수</b>${open ? Object.keys(open).length : 0}</div>
      `;

      const entries = Object.entries(open);
      document.getElementById('positionArea').textContent = entries.length
        ? entries.map(([symbol, notional]) => `${symbol}: ${Number(notional).toFixed(2)}`).join('  ')
        : '현재 열린 포지션이 없습니다.';
    }

    function renderRisk(status) {
      const risk = status.risk_guard || {};
      const limits = risk.limits || {};
      const account = risk.account_state || {};
      const cycle = status.last_cycle || {};
      const executed = Number(cycle.executed || 0);
      const rejected = Number(cycle.rejected || 0);
      const total = executed + rejected;
      const rejectRate = total > 0 ? rejected / total : 0;
      const equity = Number(account.equity_usdt || 0);
      const todayPnl = Number(account.today_pnl || 0);
      const lossRate = todayPnl < 0 && equity > 0 ? Math.abs(todayPnl) / equity : 0;
      const halted = Boolean(risk.halted || ((risk.auto_halt || {}).enabled && (risk.auto_halt || {}).stopped));
      const autoHalt = risk.auto_halt || {};
      const reason = risk.reason || autoHalt.reason || '-';
      const clearProtection = risk.clear_protection || {};

      const maxAttempts = Math.max(1, Number(clearProtection.max_failed_attempts || 3));
      const failCount = Math.max(0, Number(clearProtection.failed_attempts || 0));
      const lockMs = Math.max(0, Number(clearProtection.locked_remaining_ms || 0));
      const tokenHint = clearProtection.confirm_token_hint || 'UNHALT';
      const lockText = lockMs > 0 ? `잠금중 ${Math.max(1, Math.ceil(lockMs / 1000))}초` : '정상';

      window.__riskClearPolicy = {
        maxFailedAttempts: maxAttempts,
        confirmTokenHint: tokenHint,
        lockedRemainingMs: lockMs,
        failedAttempts: failCount,
      };

      const clearBtn = document.getElementById('clearRiskBtn');
      if (clearBtn) {
        clearBtn.style.display = halted ? 'inline-block' : 'none';
        clearBtn.disabled = lockMs > 0;
        clearBtn.textContent = lockMs > 0 ? `리스크 해제 (${lockText})` : '리스크 해제';
      }

      renderFlow(cycle, halted);

      document.getElementById('riskGuardArea').innerHTML = `
        <div class="metric"><b>리스크 상태</b>${halted ? statusBadge('정지', false) : statusBadge('정상', true)}</div>
        <div class="metric"><b>금일 손실 비율</b>${percentOrText(lossRate)}</div>
        <div class="metric"><b>연속 손실</b>${Number(account.consecutive_loss_count || 0)} / ${limits.max_consecutive_losses || 0}</div>
        <div class="metric"><b>거절 비율</b>${percentOrText(rejectRate, '0.00%')} / ${percentOrText(limits.max_reject_ratio || 0)}</div>
        <div class="metric"><b>일일 손실 상한</b>${percentOrText(limits.daily_max_loss_pct || 0)}</div>
        <div class="metric"><b>사유</b><span class="muted">${reason}</span></div>
        <div class="metric"><b>해제 보안</b>${failCount}/${maxAttempts} 실패, ${lockText}</div>
        <div class="metric"><b>확인 토큰 힌트</b><code>${tokenHint}</code></div>
      `;
    }

    function renderStrategyPlan(status) {
      const cycle = status.last_cycle || {};
      const plan = cycle.strategy_plan || {};
      const snapshots = plan.snapshot_plans || [];
      const selectedPlan = plan.selected_plan || [];
      const selectedCounts = plan.selected_strategy_counts || {};
      const signalCounts = plan.strategy_signal_counts || {};
      const distribution = plan.regime_distribution || {};

      const rowsHtml = [];
      const regimes = Object.entries(distribution).sort((a, b) => b[1] - a[1]);
      for (const [r, count] of regimes) {
        rowsHtml.push(`<div class="metric"><b>레짐 ${r}</b>종목 ${count}개</div>`);
      }
      const selectedLabel = Object.entries(selectedCounts).map(([k, v]) => `${k}: ${v}개`).join(' / ') || '없음';
      const signalLabel = Object.entries(signalCounts).map(([k, v]) => `${k}: ${v}개`).join(' / ') || '없음';
      rowsHtml.push(`<div class="metric"><b>선택 전략</b>${selectedLabel}</div>`);
      rowsHtml.push(`<div class="metric"><b>후보 생성</b>${signalLabel}</div>`);
      document.getElementById('strategyPlanSummary').innerHTML = rowsHtml.join('');

      document.getElementById('strategyPlanBody').innerHTML = selectedPlan.map((row) => `
        <tr>
          <td>${row.symbol || '-'}</td>
          <td>${row.regime || '-'}</td>
          <td>${row.strategy || '-'}</td>
          <td>${row.direction || '-'}</td>
          <td>${Number(row.score || 0).toFixed(2)}</td>
          <td>${percentOrText(Number(row.confidence || 0))}</td>
          <td>${row.comment || '-'}</td>
        </tr>
      `).join('') || '<tr><td colspan="7" class="muted">현재 주기에서 선택 후보가 없습니다.</td></tr>';

      const marketAnalysis = document.getElementById('sketchMarketAnalysis');
      if (marketAnalysis) {
        const marketItems = snapshots.slice(0, 8).map((item) =>
          `<li>${item.symbol || '-'} / ${item.regime || '-'} (${percentOrText(Number(item.regime_confidence || 0))})</li>`
        );
        marketAnalysis.innerHTML = marketItems.join('') || '<li>시황 분석 데이터가 없습니다.</li>';
      }

      const marketEvidence = document.getElementById('sketchMarketEvidence');
      if (marketEvidence) {
        const evidence = snapshots.slice(0, 6).map((item) => `<li>${item.symbol || '-'}: ${item.regime_reason || '-'}</li>`);
        marketEvidence.innerHTML = evidence.join('') || '<li>근거 데이터가 없습니다.</li>';
      }

      const strategyList = document.getElementById('sketchStrategyList');
      if (strategyList) {
        const lines = selectedPlan.slice(0, 8).map((row) => `<li>${row.symbol || '-'}: ${row.strategy || '-'} / ${row.direction || '-'}</li>`);
        strategyList.innerHTML = lines.join('') || '<li>전략 후보가 없습니다.</li>';
      }

      const strategyEvidence = document.getElementById('sketchStrategyEvidence');
      if (strategyEvidence) {
        const lines = selectedPlan.slice(0, 8).map((row) => `<li>${row.symbol || '-'}: ${row.comment || '-'} (score ${Number(row.score || 0).toFixed(2)})</li>`);
        strategyEvidence.innerHTML = lines.join('') || '<li>전략 근거가 없습니다.</li>';
      }

      const botList = document.getElementById('sketchBotList');
      if (botList) {
        const activeBots = Object.entries(selectedCounts).map(([name, count]) => `${name}(${count})`);
        botList.innerHTML = (activeBots.length
          ? activeBots.map((x) => `<li>${x}</li>`).join('')
          : '<li>활성 매매 봇 데이터가 없습니다.</li>');
      }
    }

    async function renderRiskEvents() {
      const body = document.getElementById('riskEventBody');
      try {
        const rows = await apiGet('/api/risk/events?limit=50');
        if (!rows.length) {
          body.innerHTML = '<tr><td colspan="5" class="muted">이벤트가 없습니다.</td></tr>';
          return;
        }
        const list = rows.filter((x) => String(x.action || '').includes('risk_halt_clear')).slice(0, 10);
        body.innerHTML = list.map((row) => `
          <tr>
            <td>${row.ts || '-'}</td>
            <td>${row.action || '-'}</td>
            <td>${row.previous_reason || '-'}</td>
            <td>${row.current_reason || '-'}</td>
            <td>${row.note || '-'}</td>
          </tr>
        `).join('');
      } catch (_e) {
        body.innerHTML = '<tr><td colspan="5" class="muted">이벤트 조회 실패</td></tr>';
      }
    }

    function renderPnlChart(rows) {
      const canvas = document.getElementById('pnlChart');
      const ctx = canvas && canvas.getContext('2d');
      if (!ctx) return;

      const filledRows = rows.filter((r) => r.order_status === 'filled' || r.order_status === 'partially_filled').slice().reverse();
      const points = [];
      let cum = 0;
      for (const row of filledRows) {
        const pnl = Number(row.realized_pnl || 0);
        if (!Number.isFinite(pnl)) continue;
        cum += pnl;
        points.push(cum);
      }

      const summary = document.getElementById('pnlSummary');
      if (points.length === 0) {
        summary.textContent = '실행 데이터가 없습니다.';
      } else {
        summary.textContent = `총 거래: ${filledRows.length}건 | 누적 PnL: ${cum.toFixed(2)} USDT`;
      }

      const width = canvas.clientWidth;
      const height = canvas.clientHeight;
      const dpr = window.devicePixelRatio || 1;
      canvas.width = width * dpr;
      canvas.height = height * dpr;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.clearRect(0, 0, width, height);
      ctx.fillStyle = '#070f24';
      ctx.fillRect(0, 0, width, height);
      if (points.length <= 1) return;

      const maxV = Math.max(...points, 0);
      const minV = Math.min(...points, 0);
      const span = Math.max(maxV - minV, 1);
      const left = 24;
      const right = 10;
      const top = 12;
      const bottom = 20;
      const chartW = width - left - right;
      const chartH = height - top - bottom;

      ctx.strokeStyle = '#425277';
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(left, top);
      ctx.lineTo(left, height - bottom);
      ctx.lineTo(width - right, height - bottom);
      ctx.stroke();

      ctx.beginPath();
      points.forEach((v, idx) => {
        const x = left + (idx / (points.length - 1)) * chartW;
        const y = top + chartH - ((v - minV) / span) * chartH;
        if (idx === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      });
      ctx.strokeStyle = '#22d3ee';
      ctx.lineWidth = 2;
      ctx.stroke();

      ctx.fillStyle = '#dbeafe';
      ctx.font = '11px Arial';
      ctx.fillText(`min ${minV.toFixed(2)}`, 4, height - 8);
      ctx.fillText(`max ${maxV.toFixed(2)}`, width - 70, 16);
    }

    function levelClass(level) {
      if (level === 'critical') return 'reason-critical';
      if (level === 'warn') return 'reason-warn';
      return 'reason-ok';
    }

    async function renderRejectReasonStats() {
      const alertArea = document.getElementById('rejectReasonAlertArea');
      const summaryArea = document.getElementById('rejectReasonSummary');
      const body = document.getElementById('rejectReasonBody');
      try {
        const payload = await apiGet('/api/executions/reject-stats?limit=200');
        const total = payload.total_executions || 0;
        const rejected = payload.rejected_executions || 0;
        const rejectRate = payload.reject_rate || 0;
        const th = payload.thresholds || {};
        const profile = th.profile || '-';

        summaryArea.innerHTML = `
          <div class="metric"><b>알람 모드</b>${profile}</div>
          <div class="metric"><b>샘플 수</b>${total}</div>
          <div class="metric"><b>거부 총건수</b>${rejected}</div>
          <div class="metric"><b>거부율</b>${percentOrText(rejectRate, '0.00%')}</div>
          <div class="metric"><b>임계치(거부율)</b>${percentOrText(th.reject_rate_warn || 0)} / ${percentOrText(th.reject_rate_critical || 0)}</div>
          <div class="metric"><b>거부사유 임계치</b>${percentOrText(th.reject_reason_rate_warn || 0)} / ${percentOrText(th.reject_reason_rate_critical || 0)}</div>
        `;

        const alerts = (payload.alerts || []).slice(0, 8);
        if (!alerts.length) {
          alertArea.innerHTML = '<div class="reject-alert ok">현재 기준치 이상 위험 징후가 없습니다.</div>';
          const errNode = document.getElementById('sketchErrorLine');
          if (errNode) errNode.textContent = '오류 점검: 경보 없음';
        } else {
          alertArea.innerHTML = alerts.map((item) => {
            const cls = item.level || 'info';
            const clsName = cls === 'critical' ? 'critical' : cls === 'warn' ? 'warn' : 'ok';
            return `<div class="reject-alert ${clsName}">${item.message || '-'}</div>`;
          }).join('');
          const errNode = document.getElementById('sketchErrorLine');
          if (errNode) errNode.textContent = `오류 점검: ${alerts[0].message || '경보 발생'}`;
        }

        const rows = payload.reasons || [];
        if (!rows.length) {
          body.innerHTML = '<tr><td colspan="4" class="muted">거부 데이터가 아직 충분하지 않습니다.</td></tr>';
          return;
        }

        body.innerHTML = rows.map((row) => `
          <tr>
            <td>${row.reason || '-'}</td>
            <td>${row.count || 0}</td>
            <td>${percentOrText(row.ratio || 0)}</td>
            <td class="${levelClass(row.status)}">${row.status || 'ok'}</td>
          </tr>
        `).join('');
      } catch (_e) {
        summaryArea.innerHTML = '<div class="metric"><b>거부사유 통계</b>조회 실패</div>';
        alertArea.innerHTML = '<div class="reject-alert critical">거부사유 통계 조회 중 오류가 발생했습니다.</div>';
        body.innerHTML = '<tr><td colspan="4" class="muted">거부사유 통계를 불러오지 못했습니다.</td></tr>';
        const errNode = document.getElementById('sketchErrorLine');
        if (errNode) errNode.textContent = '오류 점검: 거부사유 통계 조회 실패';
      }
    }

    function buildExecutionQueryParams(limit) {
      const params = new URLSearchParams();
      params.set('limit', String(limit || 100));

      const status = document.getElementById('execStatusFilter').value;
      const rejectReason = document.getElementById('execRejectFilter').value;
      const isPartial = document.getElementById('execPartialFilter').value;

      if (status) params.set('status', status);
      if (rejectReason) params.set('reject_reason', rejectReason);
      if (isPartial === 'true') params.set('is_partial', 'true');
      if (isPartial === 'false') params.set('is_partial', 'false');

      return params.toString();
    }

    async function renderExecutions() {
      const query = buildExecutionQueryParams(100);
      const rows = await apiGet('/api/executions?' + query);
      document.getElementById('executionBody').innerHTML = rows.map((r) => `
        <tr>
          <td>${r.ts}</td>
          <td>${r.strategy || '-'}</td>
          <td>${r.symbol}</td>
          <td>${r.side}</td>
          <td>${r.order_status}</td>
          <td>${Number(r.requested_size_usdt || 0).toFixed(2)}</td>
          <td>${Number(r.size_usdt || 0).toFixed(2)}</td>
          <td>${r.leverage || 0}</td>
          <td>${Number(r.expected_fill_price || 0).toFixed(2)}</td>
          <td>${Number(r.actual_fill_price || 0).toFixed(2)}</td>
          <td>${Number(r.slippage_bps || 0).toFixed(2)}</td>
          <td>${r.attempt_count || 0}</td>
          <td>${r.reject_reason || '-'}</td>
          <td>${Number(r.fee_usdt || 0).toFixed(4)}</td>
          <td>${Number(r.gross_realized_pnl || 0).toFixed(2)}</td>
          <td>${Number(r.realized_pnl || 0).toFixed(2)}</td>
        </tr>
      `).join('');
      renderPnlChart(rows);
      renderSketchMonitor(rows);
    }

    function renderValidationAlerts(status) {
      const area = document.getElementById('validationAlertArea');
      const payload = (status || {}).validation_alert || {};
      const alerts = (payload.alerts || []).filter((x) => ['warn', 'critical'].includes(String(x.level || '').toLowerCase()));
      if (!alerts.length) {
        area.innerHTML = '<div class="reject-alert ok">검증 알람 상태: 정상</div>';
        return;
      }
      area.innerHTML = alerts.slice(0, 3).map((a) => `
        <div class="reject-alert ${String(a.level || '').toLowerCase()}">
          <b>[${String(a.level || 'warn').toUpperCase()}]</b> ${a.message || '-'}
        </div>
      `).join('');
    }

    async function triggerValidationAlertTest(level) {
      try {
        const lv = String(level || 'warn').toLowerCase();
        const result = await apiPost('/api/validation/alert/test', { level: lv });
        if (result.status === 'sent') {
          document.getElementById('lastMessage').textContent = `검증 알람 테스트(${lv}) 발송 시도 완료`;
        } else {
          document.getElementById('lastMessage').textContent = `검증 알람 테스트(${lv}) 실패/스킵: ${result.reason || result.status}`;
        }
        await refreshAll();
      } catch (e) {
        document.getElementById('lastMessage').textContent = '검증 알람 테스트 실패: ' + e.message;
      }
    }

    function yesNo(v) {
      return v ? 'PASS' : 'FAIL';
    }

    async function renderValidationHistory() {
      try {
        const payload = await apiGet('/api/validation/history?limit=30');
        const rows = payload.recent_runs || [];
        const total = Number(payload.total_runs || 0);
        const passRate = Number(payload.pass_rate || 0);
        const avgPnl = Number(payload.avg_pnl_total_usdt || 0);
        const avgWin = Number(payload.avg_win_rate || 0);
        const avgDd = Number(payload.avg_max_drawdown_pct || 0);
        const latest = payload.latest || {};
        document.getElementById('validationOverview').innerHTML = `
          <div class="metric"><b>최근 검증 횟수</b>${total}</div>
          <div class="metric"><b>통과율</b>${percentOrText(passRate)}</div>
          <div class="metric"><b>평균 PnL</b>${numberOrText(avgPnl, 2)}</div>
          <div class="metric"><b>평균 승률</b>${percentOrText(avgWin)}</div>
          <div class="metric"><b>평균 MDD</b>${percentOrText(avgDd)}</div>
          <div class="metric"><b>최근 상태</b>${yesNo(!!latest.overall_passed)}</div>
        `;

        const tbody = document.getElementById('validationHistoryBody');
        if (!rows.length) {
          tbody.innerHTML = '<tr><td colspan="7" class="muted">검증 이력이 없습니다.</td></tr>';
          return;
        }
        tbody.innerHTML = rows.map((r) => `
          <tr>
            <td>${(r.timestamp || '-').slice(0, 19)}</td>
            <td class="${r.overall_passed ? 'ok' : 'bad'}">${yesNo(!!r.overall_passed)}</td>
            <td>${r.backtest_passed == null ? '-' : yesNo(!!r.backtest_passed)}</td>
            <td>${r.walk_forward_passed == null ? '-' : yesNo(!!r.walk_forward_passed)}</td>
            <td>${numberOrText(r.pnl_total_usdt || 0, 2)}</td>
            <td>${percentOrText(r.win_rate || 0)}</td>
            <td>${percentOrText(r.max_drawdown_pct || 0)}</td>
          </tr>
        `).join('');
      } catch (_e) {
        document.getElementById('validationOverview').innerHTML = '<div class="metric"><b>검증 비교</b>조회 실패</div>';
        document.getElementById('validationHistoryBody').innerHTML = '<tr><td colspan="7" class="muted">검증 비교 데이터를 불러오지 못했습니다.</td></tr>';
      }
    }

    async function loadLearning() {
      const days = parseInt(document.getElementById('windowDays').value || '14', 10);
      const payload = await apiGet(`/api/learning?window_days=${days}`);
      const rows = payload.tuning || [];
      const auto = payload.auto_learning || {};
      document.getElementById('learningBody').innerHTML = rows.map((x) => `
        <tr>
          <td><input type="checkbox" class="tune-check" value="${x.strategy}" /></td>
          <td>${x.strategy}</td>
          <td>${x.action}</td>
          <td>${Number(x.current_weight || 0).toFixed(2)}</td>
          <td>${Number(x.suggested_weight || 0).toFixed(2)}</td>
          <td>${((x.confidence || 0) * 100).toFixed(1)}%</td>
          <td>${x.reason || '-'}</td>
        </tr>
      `).join('');
      const changeCount = rows.filter((r) => r.action !== 'hold').length;
      let learningMsg = `변경 제안: ${changeCount}개`;
      if (!rows.length) learningMsg = '적용 가능한 제안이 없습니다.';
      if (auto.enabled) {
        const autoStatus = ((auto.last_result || {}).status) || 'idle';
        const remain = Number(auto.remaining_cycles_to_next_apply || 0);
        learningMsg += ` | 자동학습: ${autoStatus} (다음까지 ${remain} cycle)`;
      } else {
        learningMsg += ' | 자동학습: 비활성';
      }
      document.getElementById('learningMsg').textContent = learningMsg;
    }

    async function applyLearning(mode) {
      const days = parseInt(document.getElementById('windowDays').value || '14', 10);
      const selected = [...document.querySelectorAll('.tune-check:checked')].map((x) => x.value);
      const body = { window_days: days };
      if (mode === 'selected') {
        if (!selected.length) {
          document.getElementById('learningMsg').textContent = '선택할 전략이 없습니다.';
          return;
        }
        body.strategy_filter = selected;
      }

      const result = await apiPost('/api/learning/apply', body);
      document.getElementById('learningMsg').textContent = `튜닝 적용: ${result.applied_count}개`;
      await loadLearning();
      await loadConfig();
    }

    function readFloatValue(id, fallback) {
      const value = document.getElementById(id).value;
      const num = parseFloat(value);
      if (Number.isNaN(num)) return fallback;
      return num;
    }

    function readIntValue(id, fallback) {
      const value = document.getElementById(id).value;
      const num = parseInt(value, 10);
      if (Number.isNaN(num)) return fallback;
      return num;
    }

    function ensureValidationAlertControls() {
      if (document.getElementById('validationAlertEnabled')) return;
      const anchor = document.getElementById('notifyIncludeSummary');
      if (!anchor) return;

      const fieldNode = anchor.closest ? anchor.closest('.field') : null;
      const host = (fieldNode && fieldNode.parentElement) ? fieldNode.parentElement : anchor.parentElement;
      if (!host) return;

      const wrap = document.createElement('div');
      wrap.className = 'field';
      wrap.id = 'validationAlertControlWrap';
      wrap.innerHTML = `
        <label><b>검증 이력 알람 임계치</b></label>
        <div class="inline-check">
          <input id="validationAlertEnabled" type="checkbox" checked /> 활성화
        </div>
        <div class="form-grid" style="margin-top:8px;">
          <div><label for="validationAlertMinSamples">최소 샘플 수</label><input id="validationAlertMinSamples" type="number" min="1" value="5" /></div>
          <div><label for="validationPassWarn">통과율 경고 이하(0~1)</label><input id="validationPassWarn" type="number" step="0.01" min="0" max="1" value="0.6" /></div>
          <div><label for="validationPassCritical">통과율 critical 이하(0~1)</label><input id="validationPassCritical" type="number" step="0.01" min="0" max="1" value="0.4" /></div>
          <div><label for="validationDdWarn">MDD 경고 이상(0~1)</label><input id="validationDdWarn" type="number" step="0.01" min="0" max="1" value="0.25" /></div>
          <div><label for="validationDdCritical">MDD critical 이상(0~1)</label><input id="validationDdCritical" type="number" step="0.01" min="0" max="1" value="0.35" /></div>
        </div>
      `;
      host.appendChild(wrap);
    }

    function renderNotificationSettings(cfg) {
      ensureValidationAlertControls();
      const cfgNotifications = cfg.notifications || {};
      const cfgLimits = cfg.risk_limits || {};
      const cfgValidationGate = cfg.validation_gate || {};
      const levels = Array.isArray(cfgNotifications.send_on_levels) ? cfgNotifications.send_on_levels : [];
      const levelSet = levels.map((x) => String(x).toLowerCase());

      document.getElementById('notifyEnabled').checked = !!cfgNotifications.enabled;
      document.getElementById('notifyLevelCritical').checked = levelSet.includes('critical');
      document.getElementById('notifyLevelWarn').checked = levelSet.includes('warn');
      document.getElementById('notifyLevelInfo').checked = levelSet.includes('info');
      document.getElementById('rejectAlertProfile').value = cfgLimits.reject_alert_profile || 'auto';

      document.getElementById('rejectRateWarnInput').value = cfgLimits.reject_rate_warn ?? '';
      document.getElementById('rejectRateCriticalInput').value = cfgLimits.reject_rate_critical ?? '';
      document.getElementById('rejectReasonWarnInput').value = cfgLimits.reject_reason_rate_warn ?? '';
      document.getElementById('rejectReasonCriticalInput').value = cfgLimits.reject_reason_rate_critical ?? '';
      document.getElementById('rejectReasonMinSamplesInput').value = cfgLimits.reject_reason_min_samples ?? '';
      document.getElementById('notifyCooldownSeconds').value = cfgNotifications.cooldown_seconds ?? '';
      document.getElementById('notifyMaxPerHour').value = cfgNotifications.max_per_hour ?? '';
      document.getElementById('notifyWebhook').value = cfgNotifications.webhook_url || '';
      document.getElementById('notifySlackWebhook').value = cfgNotifications.slack_webhook_url || '';
      document.getElementById('notifyTelegramToken').value = cfgNotifications.telegram_bot_token || '';
      document.getElementById('notifyTelegramChatId').value = cfgNotifications.telegram_chat_id || '';
      document.getElementById('notifyIncludeSummary').checked = cfgNotifications.include_reject_summary !== false;

      const validationEnabledNode = document.getElementById('validationAlertEnabled');
      if (validationEnabledNode) validationEnabledNode.checked = cfgValidationGate.alert_enabled !== false;
      const validationMinSamplesNode = document.getElementById('validationAlertMinSamples');
      if (validationMinSamplesNode) validationMinSamplesNode.value = cfgValidationGate.alert_min_samples ?? 5;
      const validationPassWarnNode = document.getElementById('validationPassWarn');
      if (validationPassWarnNode) validationPassWarnNode.value = cfgValidationGate.alert_pass_rate_warn ?? 0.6;
      const validationPassCriticalNode = document.getElementById('validationPassCritical');
      if (validationPassCriticalNode) validationPassCriticalNode.value = cfgValidationGate.alert_pass_rate_critical ?? 0.4;
      const validationDdWarnNode = document.getElementById('validationDdWarn');
      if (validationDdWarnNode) validationDdWarnNode.value = cfgValidationGate.alert_max_drawdown_warn ?? 0.25;
      const validationDdCriticalNode = document.getElementById('validationDdCritical');
      if (validationDdCriticalNode) validationDdCriticalNode.value = cfgValidationGate.alert_max_drawdown_critical ?? 0.35;
    }

    function buildNotificationPayload() {
      const levels = [];
      if (document.getElementById('notifyLevelCritical').checked) levels.push('critical');
      if (document.getElementById('notifyLevelWarn').checked) levels.push('warn');
      if (document.getElementById('notifyLevelInfo').checked) levels.push('info');

      const riskLimits = {
        reject_alert_profile: document.getElementById('rejectAlertProfile').value || 'auto',
      };
      const rateWarn = readFloatValue('rejectRateWarnInput', Number.NaN);
      const rateCritical = readFloatValue('rejectRateCriticalInput', Number.NaN);
      const reasonWarn = readFloatValue('rejectReasonWarnInput', Number.NaN);
      const reasonCritical = readFloatValue('rejectReasonCriticalInput', Number.NaN);
      const minSamples = readIntValue('rejectReasonMinSamplesInput', Number.NaN);

      if (!Number.isNaN(rateWarn)) riskLimits.reject_rate_warn = rateWarn;
      if (!Number.isNaN(rateCritical)) riskLimits.reject_rate_critical = rateCritical;
      if (!Number.isNaN(reasonWarn)) riskLimits.reject_reason_rate_warn = reasonWarn;
      if (!Number.isNaN(reasonCritical)) riskLimits.reject_reason_rate_critical = reasonCritical;
      if (!Number.isNaN(minSamples) && minSamples > 0) riskLimits.reject_reason_min_samples = minSamples;

      if (levels.length === 0) {
        levels.push('critical', 'warn');
      }

      const validationEnabledNode = document.getElementById('validationAlertEnabled');
      const validationMinSamplesNode = document.getElementById('validationAlertMinSamples');
      const validationPassWarnNode = document.getElementById('validationPassWarn');
      const validationPassCriticalNode = document.getElementById('validationPassCritical');
      const validationDdWarnNode = document.getElementById('validationDdWarn');
      const validationDdCriticalNode = document.getElementById('validationDdCritical');

      const validationGate = {
        alert_enabled: validationEnabledNode ? !!validationEnabledNode.checked : true,
        alert_min_samples: validationMinSamplesNode ? (parseInt(validationMinSamplesNode.value || '5', 10) || 5) : 5,
        alert_pass_rate_warn: validationPassWarnNode ? (parseFloat(validationPassWarnNode.value || '0.6') || 0.6) : 0.6,
        alert_pass_rate_critical: validationPassCriticalNode ? (parseFloat(validationPassCriticalNode.value || '0.4') || 0.4) : 0.4,
        alert_max_drawdown_warn: validationDdWarnNode ? (parseFloat(validationDdWarnNode.value || '0.25') || 0.25) : 0.25,
        alert_max_drawdown_critical: validationDdCriticalNode ? (parseFloat(validationDdCriticalNode.value || '0.35') || 0.35) : 0.35,
      };

      return {
        notifications: {
          enabled: document.getElementById('notifyEnabled').checked,
          send_on_levels: levels,
          cooldown_seconds: readIntValue('notifyCooldownSeconds', 900),
          max_per_hour: readIntValue('notifyMaxPerHour', 0),
          webhook_url: document.getElementById('notifyWebhook').value.trim(),
          slack_webhook_url: document.getElementById('notifySlackWebhook').value.trim(),
          telegram_bot_token: document.getElementById('notifyTelegramToken').value.trim(),
          telegram_chat_id: document.getElementById('notifyTelegramChatId').value.trim(),
          include_reject_summary: document.getElementById('notifyIncludeSummary').checked,
        },
        risk_limits: riskLimits,
        validation_gate: validationGate,
      };
    }

    async function saveNotificationConfig() {
      try {
        const payload = buildNotificationPayload();
        await apiPost('/api/config', payload);
        document.getElementById('lastMessage').textContent = '알림 설정이 저장되었습니다.';
        await loadConfig();
      } catch (e) {
        document.getElementById('lastMessage').textContent = '알림 설정 저장 실패: ' + e.message;
      }
    }
    async function runOnce() {
      try {
        const result = await apiPost('/api/run-once', {});
        const detail = result.auto_halt?.reason ? ` (${result.auto_halt.reason})` : '';
        document.getElementById('lastMessage').textContent = `1회 실행 완료: executed=${result.executed || 0}, rejected=${result.rejected || 0}${detail}`;
        await refreshAll();
      } catch (e) {
        document.getElementById('lastMessage').textContent = '1회 실행 실패: ' + e.message;
      }
    }

    async function startLoop() {
      const interval = parseInt(document.getElementById('intervalInput').value || '5', 10);
      const liveConfirmToken = String((document.getElementById('liveConfirmTokenInput') || {}).value || '').trim();
      try {
        const result = await apiPost('/api/start', {
          interval_seconds: interval,
          live_confirm_token: liveConfirmToken,
        });
        if (result.status === 'reject_preflight') {
          const errors = ((result.preflight || {}).errors || []).join(' / ') || 'unknown';
          document.getElementById('lastMessage').textContent = `자동 실행 차단(preflight): ${errors}`;
          await refreshAll();
          return;
        }
        if (result.status === 'reject_validation_gate') {
          const errors = ((result.validation_gate || {}).errors || []).join(' / ') || 'validation gate failed';
          document.getElementById('lastMessage').textContent = `자동 실행 차단(validation): ${errors}`;
          await refreshAll();
          return;
        }
        if (result.status === 'reject_live_ack') {
          document.getElementById('lastMessage').textContent = '자동 실행 차단: LIVE 시작 토큰 불일치';
          await refreshAll();
          return;
        }
        document.getElementById('lastMessage').textContent = `자동 실행: ${result.status}`;
        await refreshAll();
      } catch (e) {
        document.getElementById('lastMessage').textContent = '시작 실패: ' + e.message;
      }
    }

    async function runLiveReadiness() {
      try {
        const payload = await apiGet('/api/live/readiness');
        const checks = payload.checks || [];
        const failed = checks.filter((c) => c.required && !c.passed);
        document.getElementById('lastMessage').textContent = payload.overall_passed
          ? '실거래 준비 점검 통과'
          : `실거래 준비 점검 실패(${failed.length}개)`;

        const boxClass = payload.overall_passed ? 'reject-alert ok' : 'reject-alert critical';
        const lines = checks.slice(0, 8).map((c) => {
          const mark = c.passed ? 'PASS' : 'FAIL';
          return `<li>[${mark}] ${c.code}: ${c.detail || '-'}</li>`;
        }).join('');
        document.getElementById('liveReadinessArea').innerHTML = `
          <div class="${boxClass}">
            <b>실거래 준비 점검 결과: ${payload.overall_passed ? 'PASS' : 'FAIL'}</b>
            <ul class="sketch-list compact" style="margin-top:6px;">${lines || '<li>점검 항목 없음</li>'}</ul>
          </div>
        `;
      } catch (e) {
        document.getElementById('lastMessage').textContent = '실거래 준비 점검 실패: ' + e.message;
      }
    }

    async function saveLiveReadinessReport() {
      try {
        const customPath = window.prompt('저장 경로(비우면 자동 경로):', '');
        const body = {};
        if (customPath && customPath.trim()) body.output_path = customPath.trim();
        const payload = await apiPost('/api/live/readiness/report', body);
        const reportPath = (payload || {}).report_path || '-';
        document.getElementById('lastMessage').textContent = `실거래 점검 리포트 저장 완료: ${reportPath}`;
        await runLiveReadiness();
      } catch (e) {
        document.getElementById('lastMessage').textContent = '실거래 점검 리포트 저장 실패: ' + e.message;
      }
    }

    function renderExchangeProbe(payload) {
      const box = document.getElementById('exchangeProbeArea');
      if (!box) return;
      if (!payload || typeof payload !== 'object') {
        box.innerHTML = '';
        return;
      }
      const checks = Array.isArray(payload.checks) ? payload.checks : [];
      const warnings = Array.isArray(payload.warnings) ? payload.warnings : [];
      const failedRequired = checks.filter((x) => !!x.required && !x.passed);
      const css = payload.overall_passed ? 'reject-alert ok' : 'reject-alert critical';
      const lines = checks.slice(0, 7).map((c) => {
        const mark = c.passed ? 'PASS' : 'FAIL';
        return `<li>[${mark}] ${c.code}: ${c.detail || '-'}</li>`;
      }).join('');
      const warnLines = warnings.slice(0, 3).map((w) => `<li>${w}</li>`).join('');
      box.innerHTML = `
        <div class="${css}">
          <b>거래소 파라미터 점검: ${payload.overall_passed ? 'PASS' : 'CHECK'}</b>
          <span class="small" style="margin-left:8px;">필수 실패 ${failedRequired.length} / critical ${payload.critical_failures || 0}</span>
          <ul class="sketch-list compact" style="margin-top:6px;">${lines || '<li>점검 항목 없음</li>'}</ul>
          ${warnLines ? `<div class="small" style="margin-top:6px;">주요 경고</div><ul class="sketch-list compact">${warnLines}</ul>` : ''}
        </div>
      `;
    }

    async function runExchangeProbe() {
      try {
        const payload = await apiGet('/api/exchange/probe');
        window.__lastExchangeProbe = payload;
        renderExchangeProbe(payload);
        document.getElementById('lastMessage').textContent = payload.overall_passed
          ? `거래소 파라미터 점검 PASS (critical=${payload.critical_failures || 0})`
          : `거래소 파라미터 점검 CHECK (critical=${payload.critical_failures || 0})`;
        renderSketchConfigSummary((window.__loadedConfig || {}));
      } catch (e) {
        document.getElementById('lastMessage').textContent = '거래소 파라미터 점검 실패: ' + e.message;
      }
    }

    async function saveExchangeProbeReport() {
      try {
        const customPath = window.prompt('저장 경로(비우면 자동 경로):', '');
        const body = {};
        if (customPath && customPath.trim()) body.output_path = customPath.trim();
        const payload = await apiPost('/api/exchange/probe/report', body);
        const reportPath = (payload || {}).report_path || '-';
        const report = (payload || {}).report || {};
        window.__lastExchangeProbe = report;
        renderExchangeProbe(report);
        document.getElementById('lastMessage').textContent = `거래소 점검 리포트 저장 완료: ${reportPath}`;
        renderSketchConfigSummary((window.__loadedConfig || {}));
      } catch (e) {
        document.getElementById('lastMessage').textContent = '거래소 점검 리포트 저장 실패: ' + e.message;
      }
    }

    function renderLlmTestResult(payload) {
      const box = document.getElementById('llmTestResult');
      if (!box) return;
      if (!payload || typeof payload !== 'object') {
        box.textContent = 'AI 연결 테스트 결과를 표시할 수 없습니다.';
        return;
      }
      const status = String(payload.status || '-');
      const provider = String(payload.provider || '-');
      const mode = String(payload.request_mode || '-');
      const model = String(payload.model || '-');
      const scored = Number(payload.scored_count || 0);
      const passText = payload.passed ? '<span class="ok">PASS</span>' : '<span class="warn">CHECK</span>';
      box.innerHTML = `
        <b>AI 연결 테스트:</b> ${passText}<br/>
        provider=${provider}, mode=${mode}, model=${model}, status=${status}, scored=${scored}
      `;
    }

    async function testLlmConnection() {
      try {
        const payload = await apiPost('/api/llm/test', {});
        window.__lastLlmTest = payload;
        renderLlmTestResult(payload);
        document.getElementById('lastMessage').textContent = payload.passed
          ? `AI 연결 테스트 PASS (${payload.status || '-'})`
          : `AI 연결 테스트 CHECK (${payload.status || '-'})`;
        renderSketchConfigSummary((window.__loadedConfig || {}));
      } catch (e) {
        document.getElementById('lastMessage').textContent = 'AI 연결 테스트 실패: ' + e.message;
      }
    }

    async function stopLoop() {
      try {
        const result = await apiPost('/api/stop', {});
        document.getElementById('lastMessage').textContent = `자동 실행: ${result.status}`;
        await refreshAll();
      } catch (e) {
        document.getElementById('lastMessage').textContent = '중지 실패: ' + e.message;
      }
    }

    async function clearRiskHalt() {
      const now = Date.now();
      if (clearState.lockUntil > now) {
        const remain = Math.max(1, Math.ceil((clearState.lockUntil - now) / 1000));
        document.getElementById('lastMessage').textContent = `리스크 해제 잠금중 ${remain}초 남았습니다.`;
        return;
      }

      const policy = window.__riskClearPolicy || { confirmTokenHint: 'UNHALT' };
      const token = window.prompt(`리스크 해제 확인 토큰을 입력하세요 (${policy.confirmTokenHint})`);
      if (token === null) return;

      try {
        const result = await apiPost('/api/risk/clear', { confirm_token: token });
        const clearProtection = result.clear_protection || {};
        clearState.failCount = Number(clearProtection.failed_attempts || 0);
        clearState.lockUntil = Date.now() + Number(clearProtection.locked_remaining_ms || 0);

        if (result.status === 'cleared') {
          clearState.failCount = 0;
          clearState.lockUntil = 0;
          const detail = result.previous_reason ? ` (${result.previous_reason})` : '';
          const evt = result.event_id ? ` | event #${result.event_id}` : '';
          document.getElementById('lastMessage').textContent = `리스크 해제가 완료되었습니다.${detail}${evt}`;
          await refreshAll();
          return;
        }

        if (clearProtection.locked || clearProtection.locked_remaining_ms > 0 || result.locked) {
          const remain = Math.max(1, Math.ceil(Number(clearProtection.locked_remaining_ms || 0) / 1000));
          document.getElementById('lastMessage').textContent = `리스크 해제 실패 누적로 잠금됩니다. ${remain}초 뒤 재시도 가능합니다.`;
        } else {
          document.getElementById('lastMessage').textContent = `리스크 해제 실패 (${result.reason || '토큰 불일치'}). 시도 ${clearState.failCount}/${policy.maxFailedAttempts}`;
        }
        await refreshAll();
      } catch (e) {
        document.getElementById('lastMessage').textContent = '리스크 해제 실패: ' + e.message;
      }
    }

    async function loadConfig() {
      const cfg = await apiGet('/api/config');
      window.__loadedConfig = cfg;
      document.getElementById('configJson').value = JSON.stringify(cfg, null, 2);
      renderNotificationSettings(cfg);
      renderSketchConfigSummary(cfg);
      document.getElementById('lastMessage').textContent = '설정을 불러왔습니다.';
    }

    async function saveConfig() {
      let payload;
      try {
        payload = JSON.parse(document.getElementById('configJson').value);
      } catch (_e) {
        document.getElementById('lastMessage').textContent = '설정 JSON 형식이 올바르지 않습니다.';
        return;
      }
      const uiPayload = buildNotificationPayload();
      payload.notifications = { ...(payload.notifications || {}), ...uiPayload.notifications };
      payload.risk_limits = { ...(payload.risk_limits || {}), ...uiPayload.risk_limits };
      payload.validation_gate = { ...(payload.validation_gate || {}), ...uiPayload.validation_gate };
      await apiPost('/api/config', payload);
      document.getElementById('lastMessage').textContent = '설정이 저장되었습니다.';
      await refreshAll();
    }

    async function refreshAll() {
      try {
        const status = await apiGet('/api/status');
        renderOverview(status);
        renderValidationAlerts(status);
        renderAccount(status);
        renderRisk(status);
        renderStrategyPlan(status);
        await renderValidationHistory();
        await renderRejectReasonStats();
        await renderExecutions();
        await renderRiskEvents();
      } catch (e) {
        document.getElementById('lastMessage').textContent = '상태 조회 실패: ' + e.message;
      }
    }

    window.addEventListener('load', () => {
      loadTheme();
      ensureValidationAlertControls();
      initSketchTabs();
      refreshAll();
      loadConfig();
      loadLearning();
      renderSketchSources();
      loadSketchMemo();
      setInterval(refreshAll, POLL_MS);
      setInterval(loadLearning, 15000);
      setInterval(() => {
        renderExecutions().catch(() => {});
      }, 5000);
      setInterval(renderRiskEvents, 10000);
    });
  </script>
</body>
</html>
"""

    @app.get("/api/status")
    def get_status() -> dict[str, Any]:
        return runtime.get_status()

    @app.get("/api/config")
    def get_config() -> dict[str, Any]:
        return runtime.get_config()

    @app.post("/api/config")
    def patch_config(payload: dict[str, Any] = Body(default_factory=dict)) -> dict[str, Any]:
        try:
            return runtime.patch_config(payload)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc))

    @app.post("/api/run-once")
    def run_once() -> dict[str, Any]:
        try:
            return runtime.run_once()
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc))

    @app.post("/api/start")
    def start(body: dict[str, Any] = Body(default_factory=dict)) -> dict[str, Any]:
        interval = body.get("interval_seconds") if isinstance(body, dict) else None
        live_confirm_token = body.get("live_confirm_token") if isinstance(body, dict) else None
        if interval is not None:
            try:
                interval = int(interval)
            except (TypeError, ValueError) as exc:
                raise HTTPException(status_code=400, detail="interval_seconds must be integer") from exc
        return runtime.start(interval_seconds=interval, live_confirm_token=live_confirm_token)

    @app.get("/api/live/preflight")
    def live_preflight() -> dict[str, Any]:
        status = runtime.get_status()
        return status.get("live_preflight", {})

    @app.get("/api/live/readiness")
    def live_readiness() -> dict[str, Any]:
        try:
            return runtime.run_live_readiness()
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc))

    @app.post("/api/live/readiness/report")
    def save_live_readiness_report(payload: dict[str, Any] = Body(default_factory=dict)) -> dict[str, Any]:
        try:
            output_path = None
            if isinstance(payload, dict):
                output_path = payload.get("output_path")
            return runtime.save_live_readiness_report(output_path=output_path)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc))

    @app.get("/api/exchange/probe")
    def exchange_probe(symbols: str = "") -> dict[str, Any]:
        try:
            symbol_list = [x.strip() for x in str(symbols or "").split(",") if x.strip()]
            return runtime.run_exchange_probe(symbols=symbol_list or None)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc))

    @app.post("/api/exchange/probe/report")
    def exchange_probe_report(payload: dict[str, Any] = Body(default_factory=dict)) -> dict[str, Any]:
        try:
            output_path = None
            symbols = None
            if isinstance(payload, dict):
                output_path = payload.get("output_path")
                raw_symbols = payload.get("symbols")
                if isinstance(raw_symbols, list):
                    symbols = [str(x).strip() for x in raw_symbols if str(x).strip()]
            return runtime.save_exchange_probe_report(output_path=output_path, symbols=symbols)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc))

    @app.post("/api/llm/test")
    def test_llm_connection(payload: dict[str, Any] = Body(default_factory=dict)) -> dict[str, Any]:
        try:
            sample_symbol = "BTCUSDT"
            if isinstance(payload, dict):
                sample_symbol = str(payload.get("sample_symbol") or sample_symbol)
            return runtime.test_llm_connection(sample_symbol=sample_symbol)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc))

    @app.post("/api/stop")
    def stop() -> dict[str, Any]:
        return runtime.stop()

    @app.post("/api/risk/clear")
    def clear_risk(payload: dict[str, Any] = Body(default_factory=dict)) -> dict[str, Any]:
        confirm_token = None
        if isinstance(payload, dict):
            confirm_token = payload.get("confirm_token")
        try:
            return runtime.clear_risk_halt(confirm_token=confirm_token)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc))

    @app.get("/api/risk/events")
    def get_risk_events(limit: int = 20) -> list[dict[str, Any]]:
        try:
            return runtime.get_risk_events(limit=limit)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc))

    @app.get("/api/executions")
    def get_executions(limit: int = 30, status: str | None = None, reject_reason: str | None = None, is_partial: bool | None = None) -> list[dict[str, Any]]:
        return runtime.get_executions(limit=limit, status=status or None, reject_reason=reject_reason or None, is_partial=is_partial)

    @app.get("/api/executions/reject-stats")
    def get_reject_reason_stats(limit: int = 200) -> dict[str, Any]:
        try:
            return runtime.get_reject_reason_metrics(limit=limit)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc))

    @app.get("/api/learning")
    def get_learning(window_days: int = 14) -> dict[str, Any]:
        return runtime.get_learning(window_days=window_days)

    @app.post("/api/learning/apply")
    def apply_learning(payload: dict[str, Any] = Body(default_factory=dict)) -> dict[str, Any]:
        try:
            window_days = payload.get("window_days", 14) if isinstance(payload, dict) else 14
            strategy_filter = payload.get("strategy_filter") if isinstance(payload, dict) else None
            return runtime.apply_learning(window_days=window_days, strategy_filter=strategy_filter)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc))

    @app.get("/api/learning/events")
    def get_learning_events(limit: int = 100, source: str | None = None) -> list[dict[str, Any]]:
        try:
            return runtime.get_auto_learning_events(limit=limit, source=source)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc))

    @app.get("/api/validation/history")
    def get_validation_history(limit: int = 30) -> dict[str, Any]:
        try:
            return runtime.get_validation_history(limit=limit)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc))

    @app.post("/api/validation/alert/test")
    def trigger_validation_alert_test(payload: dict[str, Any] = Body(default_factory=dict)) -> dict[str, Any]:
        try:
            level = payload.get("level", "warn") if isinstance(payload, dict) else "warn"
            return runtime.trigger_validation_alert_test(level=level)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc))

    @app.on_event("shutdown")
    def shutdown() -> None:
        runtime.close()

    return app











