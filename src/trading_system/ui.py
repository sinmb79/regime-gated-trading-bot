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
      --surface: #070f24;
      --surface-soft: rgba(8, 14, 28, 0.7);
      --field-surface: rgba(7, 15, 36, 0.9);
      --soft-border: #2f4166;
      --mini-btn-bg: #243a66;
      --mini-btn-border: #3f5b89;
      --muted-box-bg: rgba(8, 15, 32, 0.72);
      --muted-box-line: #45628f;
      --font-ui: "Pretendard", "Apple SD Gothic Neo", Arial, sans-serif;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: var(--font-ui);
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
      border: 1px solid var(--soft-border);
      border-radius: 10px;
      padding: 10px;
      background: var(--surface-soft);
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
      border: 1px solid var(--soft-border);
      border-radius: 10px;
      background: var(--surface);
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
      border-bottom: 1px solid var(--soft-border);
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
      border: 1px solid var(--soft-border);
      border-radius: 10px;
      padding: 8px;
      background: var(--surface);
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
      background: var(--surface);
      border: 1px solid var(--soft-border);
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
      border: 1px solid var(--soft-border);
      border-radius: 10px;
      padding: 8px;
      background: var(--field-surface);
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
      border: 1px solid var(--mini-btn-border);
      background: var(--mini-btn-bg);
      color: #e4ebff;
      font-size: 12px;
      cursor: pointer;
    }
    .muted-box {
      color: #9fb0d0;
      font-size: 12px;
      border: 1px dashed var(--muted-box-line);
      border-radius: 8px;
      padding: 6px;
      background: var(--muted-box-bg);
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
    body.theme-style-premium {
      background:
        radial-gradient(circle at top, rgba(212, 166, 74, 0.18), transparent 34%),
        radial-gradient(circle at 20% 20%, rgba(59, 130, 246, 0.16), transparent 28%),
        var(--bg);
    }
    body.theme-style-premium .panel {
      box-shadow: 0 14px 36px rgba(0,0,0,0.34);
    }
    body.theme-style-simple {
      background: linear-gradient(180deg, #111827, #0f172a 52%, #0b1220);
    }
    body.theme-style-simple .panel,
    body.theme-style-simple .metric,
    body.theme-style-simple .field,
    body.theme-style-simple .sketch-card,
    body.theme-style-simple .sketch-side-box,
    body.theme-style-simple .sketch-label {
      border-radius: 8px;
      box-shadow: none;
    }
    body.theme-style-light {
      background: linear-gradient(180deg, #f5f8fd, #e7eef8 48%, #dce7f4);
      color: #0f172a;
    }
    body.theme-style-light .panel,
    body.theme-style-light .metric,
    body.theme-style-light .field,
    body.theme-style-light .sketch-main,
    body.theme-style-light .sketch-card,
    body.theme-style-light .sketch-side,
    body.theme-style-light .sketch-side-box,
    body.theme-style-light .sketch-label,
    body.theme-style-light .canvas-wrap {
      background: rgba(255,255,255,0.92);
      color: #0f172a;
      border-color: #cfd8e5;
      box-shadow: 0 12px 28px rgba(15,23,42,0.08);
    }
    body.theme-style-light textarea,
    body.theme-style-light input,
    body.theme-style-light .muted-box,
    body.theme-style-light .step,
    body.theme-style-light .btn-mini {
      background: #f8fbff;
      color: #0f172a;
      border-color: #cfd8e5;
    }
    body.theme-style-light .sketch-tab {
      background: #eef4fb;
      color: #1f2d3d;
      border-color: #c7d5e8;
    }
    body.theme-style-light th,
    body.theme-style-light .metric b,
    body.theme-style-light .step,
    body.theme-style-light .field label {
      color: #334155;
    }
    body.theme-style-terminal {
      background:
        radial-gradient(circle at top, rgba(34, 197, 94, 0.12), transparent 28%),
        linear-gradient(180deg, #03110f, #071917 56%, #0a2620);
    }
    body.theme-style-terminal .panel,
    body.theme-style-terminal .metric,
    body.theme-style-terminal .field,
    body.theme-style-terminal .sketch-main,
    body.theme-style-terminal .sketch-card,
    body.theme-style-terminal .sketch-side,
    body.theme-style-terminal .sketch-side-box,
    body.theme-style-terminal .sketch-label,
    body.theme-style-terminal .canvas-wrap {
      box-shadow: 0 0 0 1px rgba(34, 197, 94, 0.08), 0 18px 34px rgba(0,0,0,0.42);
    }
    body.theme-style-terminal .sketch-tab.active {
      background: linear-gradient(135deg, #0f766e, #22c55e);
      border-color: #6ee7b7;
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
      <h1 data-i18n="title.main">AI 트레이딩 봇 운영 대시보드</h1>
      <div class="toolbar">
        <button class="btn" onclick="runOnce()" data-i18n="toolbar.runOnce">1회 실행</button>
        <button class="btn btn-good" onclick="startLoop()" data-i18n="toolbar.autoStart">자동 시작</button>
        <button class="btn btn-danger" onclick="stopLoop()" data-i18n="toolbar.stop">중지</button>
        <button class="btn btn-sub" onclick="runLiveReadiness()" data-i18n="toolbar.readiness">실거래 준비 점검</button>
        <button class="btn btn-sub" onclick="saveLiveReadinessReport()" data-i18n="toolbar.readinessReport">점검 리포트 저장</button>
        <button class="btn btn-sub" onclick="runLiveRehearsal()" data-i18n="toolbar.rehearsal">실거래 리허설 계획</button>
        <button class="btn btn-sub" onclick="saveLiveRehearsalReport()" data-i18n="toolbar.rehearsalReport">리허설 리포트 저장</button>
        <button class="btn btn-sub" onclick="runExchangeProbe()" data-i18n="toolbar.exchangeProbe">거래소 파라미터 점검</button>
        <button class="btn btn-sub" onclick="saveExchangeProbeReport()" data-i18n="toolbar.exchangeReport">거래소 점검 리포트 저장</button>
        <button class="btn btn-sub" onclick="testLlmConnection()" data-i18n="toolbar.aiTest">AI 연결 테스트</button>
        <input id="intervalInput" type="number" min="1" value="5" /><span data-i18n="unit.seconds">초</span>
        <input id="liveConfirmTokenInput" type="text" placeholder="LIVE 시작 토큰" data-i18n-placeholder="placeholder.liveToken" style="min-width:150px;" />
        <button class="btn btn-sub" onclick="refreshAll()" data-i18n="toolbar.refresh">새로고침</button>
      </div>
      <div class="muted" style="margin-top:8px;"><span id="lastMessageLabel" data-i18n="label.lastMessage">마지막 메시지</span>: <span id="lastMessage">-</span></div>
      <div id="flowArea" style="margin-top:8px;"></div>
      <div id="liveReadinessArea" style="margin-top:8px;"></div>
      <div id="liveRehearsalArea" style="margin-top:8px;"></div>
      <div id="exchangeProbeArea" style="margin-top:8px;"></div>
      <div class="grid" id="overview" style="margin-top:10px;"></div>
    </div>

    <div class="panel">
      <h2 data-i18n="title.validation">검증 리포트 비교 대시보드</h2>
      <div class="toolbar" style="margin-bottom:8px;">
        <button class="btn btn-sub" onclick="triggerValidationAlertTest('warn')" data-i18n="validation.testWarn">검증 알람 테스트(경고)</button>
        <button class="btn btn-sub" onclick="triggerValidationAlertTest('critical')" data-i18n="validation.testCritical">검증 알람 테스트(치명)</button>
      </div>
      <div class="grid" id="validationOverview"></div>
      <div id="validationAlertArea" style="margin-top:8px;"></div>
      <table style="margin-top:8px;">
        <thead>
          <tr>
            <th data-i18n="table.time">시각</th>
            <th data-i18n="table.overallPassed">전체통과</th>
            <th data-i18n="table.backtest">Backtest</th>
            <th data-i18n="table.walkForward">WalkForward</th>
            <th data-i18n="table.pnlUsdt">PnL(USDT)</th>
            <th data-i18n="table.winRate">승률</th>
            <th data-i18n="table.mdd">MDD</th>
          </tr>
        </thead>
        <tbody id="validationHistoryBody">
          <tr><td colspan="7" class="muted" data-i18n="validation.noHistory">검증 이력 없음</td></tr>
        </tbody>
      </table>
    </div>

    <div class="panel sketch-panel">
      <div class="sketch-header">
        <div class="sketch-tabs">
          <button class="sketch-tab sketch-tab-cta active" data-tab="start" onclick="setSketchTab('start')" data-i18n="tab.start">시작</button>
          <button class="sketch-tab" data-tab="running" onclick="setSketchTab('running')" data-i18n="tab.running">진행중인</button>
          <button class="sketch-tab" data-tab="settings" onclick="setSketchTab('settings')" data-i18n="tab.settings">내설정</button>
          <button class="sketch-tab" data-tab="api" onclick="setSketchTab('api')" data-i18n="tab.api">연결 API</button>
          <button class="sketch-tab" data-tab="logging" onclick="setSketchTab('logging')" data-i18n="tab.logging">로깅</button>
        </div>
        <div class="sketch-statusline">
          <span id="sketchRunStatus" data-i18n="sketch.status.runIdle">실행: -</span>
          <span id="sketchApiStatus" data-i18n="sketch.status.apiIdle">API: -</span>
          <span id="sketchLoopStatus" data-i18n="sketch.status.loopIdle">자동: -</span>
        </div>
      </div>
      <div class="sketch-layout">
        <div class="sketch-main">
          <section id="tab-start" class="sketch-tab-view active">
            <div class="toolbar" style="margin-bottom:8px;">
              <button class="btn btn-good" onclick="runOnce()" data-i18n="sketch.action.runOnceNow">바로 1회 실행</button>
              <button class="btn btn-sub" onclick="startLoop()" data-i18n="toolbar.autoStart">자동 시작</button>
              <button class="btn btn-danger" onclick="stopLoop()" data-i18n="toolbar.stop">중지</button>
            </div>
            <div class="sketch-row">
              <div class="sketch-label" data-i18n="sketch.marketAnalysis">시황 분석</div>
              <div class="sketch-card">
                <ul id="sketchMarketAnalysis" class="sketch-list">
                  <li data-i18n="sketch.waitingData">데이터 대기 중...</li>
                </ul>
              </div>
            </div>
            <div class="sketch-note">
              <b data-i18n="sketch.evidenceNews">* 근거1 (뉴스/심리):</b>
              <ul id="sketchMarketEvidence" class="sketch-list compact">
                <li data-i18n="sketch.noEvidenceYet">아직 수집된 근거가 없습니다.</li>
              </ul>
            </div>
            <div class="sketch-row">
              <div class="sketch-label" data-i18n="sketch.strategy">매매 전략</div>
              <div class="sketch-card">
                <ul id="sketchStrategyList" class="sketch-list">
                  <li data-i18n="sketch.waitingStrategy">전략 추천 대기 중...</li>
                </ul>
              </div>
            </div>
            <div class="sketch-note">
              <b data-i18n="sketch.evidenceStrategy">* 근거2:</b>
              <ul id="sketchStrategyEvidence" class="sketch-list compact">
                <li data-i18n="sketch.waitingStrategyEvidence">전략 근거 대기 중...</li>
              </ul>
            </div>
            <div class="sketch-row">
              <div class="sketch-label" data-i18n="sketch.bot">매매 봇</div>
              <div class="sketch-card">
                <ul id="sketchBotList" class="sketch-list">
                  <li>Grid / Trend / Defensive / Funding Arb / Indicator</li>
                </ul>
              </div>
            </div>
          </section>

          <section id="tab-running" class="sketch-tab-view">
            <div class="sketch-row">
              <div class="sketch-label" data-i18n="sketch.monitoring">실시간 모니터링</div>
              <div class="sketch-card">
                <table class="sketch-mini-table">
                  <thead>
                    <tr>
                      <th data-i18n="table.datetime">일시</th><th data-i18n="table.symbol">종목</th><th data-i18n="table.strategy">전략</th><th data-i18n="table.status">상태</th><th data-i18n="table.pnl">PnL</th>
                    </tr>
                  </thead>
                  <tbody id="sketchMonitorBody">
                    <tr><td colspan="5" class="muted" data-i18n="sketch.waitingExecutionData">체결 데이터 대기 중...</td></tr>
                  </tbody>
                </table>
                <div id="sketchErrorLine" class="sketch-error-line" data-i18n="sketch.errorNormal">오류 점검: 정상</div>
              </div>
            </div>
            <div class="sketch-note">
              <b data-i18n="sketch.progressState">* 진행 상태:</b>
              <ul id="sketchRunningMeta" class="sketch-list compact">
                <li data-i18n="sketch.waitingCycleState">주기/상태 데이터 대기 중...</li>
              </ul>
            </div>
          </section>

          <section id="tab-settings" class="sketch-tab-view">
            <div class="sketch-row">
              <div class="sketch-label" data-i18n="sketch.mySettings">내 설정</div>
              <div class="sketch-card">
                <ul id="sketchSettingsSummary" class="sketch-list">
                  <li data-i18n="sketch.waitingConfigSummary">설정 요약 대기 중...</li>
                </ul>
                <div id="sketchStrategyEditor" style="margin-top:8px;">
                  <div class="muted" data-i18n="sketch.loadingStrategyConfig">전략 설정 로딩 중...</div>
                </div>
                <div id="sketchRiskEditor" style="margin-top:10px;">
                  <div class="muted" data-i18n="sketch.loadingRiskConfig">리스크 설정 로딩 중...</div>
                </div>
                <div class="toolbar" style="margin-top:8px;">
                  <button class="btn btn-good" onclick="saveSketchStrategyConfig()" data-i18n="button.saveStrategyConfig">전략 설정 저장</button>
                  <button class="btn btn-good" onclick="saveSketchRiskConfig()" data-i18n="button.saveRiskConfig">리스크 설정 저장</button>
                  <button class="btn btn-sub" onclick="goToConfig()" data-i18n="button.goToConfig">설정 JSON 이동</button>
                  <button class="btn btn-sub" onclick="loadConfig()" data-i18n="button.reloadConfig">설정 다시 로드</button>
                </div>
              </div>
            </div>
          </section>

          <section id="tab-api" class="sketch-tab-view">
            <div class="sketch-row">
              <div class="sketch-label" data-i18n="sketch.apiStatus">API 상태</div>
              <div class="sketch-card">
                <ul id="sketchApiDetails" class="sketch-list">
                  <li data-i18n="sketch.waitingApiStatus">API 연결 상태 대기 중...</li>
                </ul>
                <div class="toolbar" style="margin-top:8px;">
                  <button class="btn btn-sub" onclick="runExchangeProbe()" data-i18n="toolbar.exchangeProbe">거래소 파라미터 점검</button>
                  <button class="btn btn-sub" onclick="testLlmConnection()" data-i18n="toolbar.aiTest">AI 연결 테스트</button>
                </div>
                <div id="llmTestResult" class="muted-box" style="margin-top:8px;" data-i18n="sketch.noAiTestYet">아직 테스트를 실행하지 않았습니다.</div>
              </div>
            </div>
          </section>

          <section id="tab-logging" class="sketch-tab-view">
            <div class="sketch-row">
              <div class="sketch-label" data-i18n="sketch.opsLogging">운영 로깅</div>
              <div class="sketch-card">
                <table class="sketch-mini-table">
                  <thead>
                    <tr>
                      <th data-i18n="table.time">시간</th><th data-i18n="table.symbol">종목</th><th data-i18n="table.status">상태</th><th data-i18n="table.reason">사유</th>
                    </tr>
                  </thead>
                  <tbody id="sketchLogBody">
                    <tr><td colspan="4" class="muted" data-i18n="sketch.waitingLogData">로그 데이터 대기 중...</td></tr>
                  </tbody>
                </table>
                <div class="toolbar" style="margin-top:8px;">
                  <button class="btn btn-sub" onclick="goToLogging()" data-i18n="button.goToExecutions">상세 실행내역 이동</button>
                </div>
              </div>
            </div>
          </section>
        </div>

        <aside class="sketch-side">
          <h3 data-i18n="side.sourceIntegration">소스 연동</h3>
          <div class="sketch-side-box">
            <b data-i18n="side.researchSources">심리 분석/리서치 소스</b>
            <ul class="sketch-list compact">
              <li>TradingView</li>
              <li>Google Trends</li>
              <li>VIX 지수</li>
            </ul>
            <div class="muted-box" data-i18n="side.researchSourcesHelp">사용자 소스는 아래에서 커스텀으로 추가합니다.</div>
          </div>
          <div class="sketch-side-box">
            <b data-i18n="side.customSources">사용자 커스텀 소스</b>
            <div class="sketch-inline">
              <input id="sketchSourceInput" type="text" placeholder="예: https://example.com/feed" data-i18n-placeholder="placeholder.customSource" />
              <button class="btn-mini" onclick="addSketchSource()" data-i18n="button.add">추가</button>
            </div>
            <ul id="sketchSourceCustom" class="sketch-list compact">
              <li data-i18n="side.noCustomSources">등록된 커스텀 소스가 없습니다.</li>
            </ul>
          </div>
          <div class="sketch-side-box">
            <b data-i18n="side.strategyMemo">사용자 전략 메모</b>
            <textarea id="sketchStrategyMemo" rows="5" style="min-height:120px;" placeholder="사용자 전략 아이디어/규칙을 메모하세요." data-i18n-placeholder="placeholder.strategyMemo"></textarea>
            <div class="sketch-inline">
              <button class="btn-mini" onclick="saveSketchMemo()" data-i18n="button.saveMemo">메모 저장</button>
            </div>
          </div>
          <div class="sketch-side-box">
            <b data-i18n="side.uiStyle">UI 스타일</b>
            <div class="sketch-inline">
              <select id="themePreset">
                <option value="premium" data-i18n="theme.premium">더 고급스럽게</option>
                <option value="simple" data-i18n="theme.simple">더 단순하게</option>
                <option value="light" data-i18n="theme.light">라이트 테마</option>
                <option value="terminal" data-i18n="theme.terminal">거래소 터미널</option>
              </select>
              <button class="btn-mini" onclick="applyThemePreset()" data-i18n="button.preview">미리보기</button>
              <button class="btn-mini" onclick="saveThemeStyleConfig()" data-i18n="button.saveSetting">설정 저장</button>
            </div>
            <div class="theme-grid">
              <div>
                <label for="themeBg1" data-i18n="theme.bg1">배경 1</label>
                <input id="themeBg1" type="color" value="#0b1a36" />
              </div>
              <div>
                <label for="themeBg2" data-i18n="theme.bg2">배경 2</label>
                <input id="themeBg2" type="color" value="#12213f" />
              </div>
              <div>
                <label for="themeBg3" data-i18n="theme.bg3">배경 3</label>
                <input id="themeBg3" type="color" value="#1d2f56" />
              </div>
              <div>
                <label for="themeAccent" data-i18n="theme.accent">강조색</label>
                <input id="themeAccent" type="color" value="#3b82f6" />
              </div>
              <div>
                <label for="themePanel" data-i18n="theme.panel">패널색</label>
                <input id="themePanel" type="color" value="#0c162d" />
              </div>
              <div>
                <label for="themeLine" data-i18n="theme.line">라인색</label>
                <input id="themeLine" type="color" value="#2f3e5c" />
              </div>
            </div>
            <div class="sketch-inline">
              <button class="btn-mini" onclick="applyCustomTheme()" data-i18n="button.applyColors">색상 적용</button>
              <button class="btn-mini" onclick="resetTheme()" data-i18n="button.resetDefault">기본 복원</button>
            </div>
          </div>
          <div class="sketch-side-box">
            <b data-i18n="side.language">언어 설정</b>
            <div class="sketch-inline">
              <select id="languagePreset">
                <option value="ko">한국어</option>
                <option value="en">English</option>
                <option value="zh">中文</option>
                <option value="ja">日本語</option>
                <option value="fr">Français</option>
              </select>
              <button class="btn-mini" onclick="applyLanguagePreview()" data-i18n="button.preview">미리보기</button>
              <button class="btn-mini" onclick="saveLanguageConfig()" data-i18n="button.saveSetting">설정 저장</button>
            </div>
            <div class="muted-box" data-i18n="side.languageHelp">저장하면 이후 접속에도 선택 언어를 유지합니다.</div>
          </div>
        </aside>
      </div>
    </div>

    <div class="panel">
      <h2 data-i18n="title.account">계정/포지션</h2>
      <div class="grid" id="accountArea"></div>
      <div id="positionArea" class="muted"></div>
    </div>

    <div class="panel">
      <h2 data-i18n="title.risk">리스크 상태</h2>
      <div class="grid" id="riskGuardArea"></div>
      <div class="toolbar" style="margin-top:8px;">
        <button id="clearRiskBtn" class="btn btn-sub" onclick="clearRiskHalt()" style="display:none;" data-i18n="button.clearRisk">리스크 해제</button>
      </div>
    </div>

    <div class="panel">
      <h2 data-i18n="title.riskEvents">리스크 이벤트</h2>
      <table>
        <thead>
          <tr>
            <th data-i18n="table.time">시간</th><th data-i18n="table.event">이벤트</th><th data-i18n="table.previousReason">이전 사유</th><th data-i18n="table.currentReason">현재 사유</th><th data-i18n="table.note">비고</th>
          </tr>
        </thead>
        <tbody id="riskEventBody"></tbody>
      </table>
    </div>

    <div class="panel">
      <h2 data-i18n="title.rejectDashboard">거부사유 운영 대시보드</h2>
      <div id="rejectReasonAlertArea"></div>
      <div class="grid" id="rejectReasonSummary" style="margin-bottom: 8px;"></div>
      <table>
        <thead>
          <tr>
            <th data-i18n="table.rejectReason">거부사유</th><th data-i18n="table.count">건수</th><th data-i18n="table.ratio">비율</th><th data-i18n="table.status">상태</th>
          </tr>
        </thead>
        <tbody id="rejectReasonBody"></tbody>
      </table>
    </div>

    <div class="panel">
      <h2 data-i18n="title.regimeStrategy">레짐 기반 전략 추천</h2>
      <div id="strategyPlanSummary" class="grid" style="margin-bottom: 8px;"></div>
      <table>
        <thead>
          <tr>
            <th data-i18n="table.symbol">종목</th>
            <th data-i18n="table.regime">레짐</th>
            <th data-i18n="table.strategy">전략</th>
            <th data-i18n="table.direction">방향</th>
            <th data-i18n="table.score">점수</th>
            <th data-i18n="table.confidence">신뢰도</th>
            <th data-i18n="table.reason">이유</th>
          </tr>
        </thead>
        <tbody id="strategyPlanBody"></tbody>
      </table>
    </div>

    <div class="panel">
      <h2 data-i18n="title.pnlCurve">수익 곡선</h2>
      <div class="canvas-wrap"><canvas id="pnlChart"></canvas></div>
      <div id="pnlSummary" class="muted" style="margin-top:6px;"></div>
    </div>

    <div class="panel">
      <h2 data-i18n="title.executions">실행 내역</h2>
      <div class="toolbar" style="margin-bottom:8px; gap:6px;">
        <span class="muted" data-i18n="filter.status">상태</span>
        <select id="execStatusFilter" onchange="renderExecutions()">
          <option value="" data-i18n="filter.all">전체</option>
          <option value="filled">filled</option>
          <option value="partially_filled">partially_filled</option>
          <option value="rejected">rejected</option>
          <option value="cancelled">cancelled</option>
        </select>
        <span class="muted" data-i18n="filter.partialFill">부분체결</span>
        <select id="execPartialFilter" onchange="renderExecutions()">
          <option value="" data-i18n="filter.all">전체</option>
          <option value="true" data-i18n="filter.hasValue">있음</option>
          <option value="false" data-i18n="filter.notValue">아님</option>
        </select>
        <span class="muted" data-i18n="filter.rejectReason">거부사유</span>
        <select id="execRejectFilter" onchange="renderExecutions()">
          <option value="" data-i18n="filter.all">전체</option>
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
        <button class="btn btn-sub" onclick="renderExecutions()" data-i18n="button.query">조회</button>
      </div>
      <table>
        <thead>
          <tr>
            <th data-i18n="table.time">시간</th><th data-i18n="table.strategy">전략</th><th data-i18n="table.symbol">종목</th><th data-i18n="table.direction">방향</th><th data-i18n="table.status">상태</th><th data-i18n="table.requestUsdt">요청금액(USDT)</th><th data-i18n="table.filledUsdt">체결금액(USDT)</th><th data-i18n="table.leverage">레버리지</th><th data-i18n="table.expectedPrice">예상가</th><th data-i18n="table.fillPrice">체결가</th><th data-i18n="table.slippageBps">슬리피지(bps)</th><th data-i18n="table.attempts">시도</th><th data-i18n="table.retryReason">재시도사유</th><th data-i18n="table.feeUsdt">수수료(USDT)</th><th data-i18n="table.grossPnl">GrossPnL</th><th data-i18n="table.netPnl">NetPnL</th><th data-i18n="table.regime">레짐</th><th data-i18n="table.entryReason">진입근거</th><th data-i18n="table.marketState">시장상태</th><th data-i18n="table.slippageCause">슬리피지 원인</th>
          </tr>
        </thead>
        <tbody id="executionBody"></tbody>
      </table>
    </div>

    <div class="panel">
      <h2 data-i18n="title.learning">AI 복기/튜닝</h2>
      <div class="toolbar">
        <span class="muted" data-i18n="learning.windowDays">회고 기간</span>
        <input id="windowDays" type="number" min="1" max="60" value="14" /><span data-i18n="unit.days">일</span>
        <button class="btn btn-sub" onclick="loadLearning()" data-i18n="button.loadAnalysis">분석 조회</button>
        <button class="btn btn-sub" onclick="applyLearning('selected')" data-i18n="button.applySelectedStrategy">선택 전략 적용</button>
        <button class="btn btn-good" onclick="applyLearning('all')" data-i18n="button.applyAllSuggestions">전체 제안 일괄 적용</button>
        <button class="btn btn-sub" onclick="reviewLearningProposals('approve')" data-i18n="button.approvePending">대기 제안 승인 적용</button>
        <button class="btn btn-sub" onclick="reviewLearningProposals('reject')" data-i18n="button.rejectPending">대기 제안 거절</button>
      </div>
      <div id="learningMsg" class="muted" style="margin:8px 0;"></div>
      <table>
        <thead>
          <tr>
            <th data-i18n="table.apply">적용</th><th data-i18n="table.strategy">전략</th><th data-i18n="table.suggestion">제안</th><th data-i18n="table.currentWeight">현재 가중치</th><th data-i18n="table.suggestedWeight">제안 가중치</th><th data-i18n="table.confidence">신뢰도</th><th data-i18n="table.reason">사유</th>
          </tr>
        </thead>
        <tbody id="learningBody"></tbody>
      </table>
      <div id="learningProposalMsg" class="muted" style="margin:10px 0 4px;"></div>
      <table>
        <thead>
          <tr>
            <th data-i18n="table.select">선택</th><th>ID</th><th data-i18n="table.strategy">전략</th><th data-i18n="table.suggestion">제안</th><th data-i18n="table.currentValue">현재</th><th data-i18n="table.suggestedValue">제안값</th><th data-i18n="table.confidence">신뢰도</th><th data-i18n="table.reason">사유</th><th data-i18n="table.status">상태</th><th data-i18n="table.time">시각</th>
          </tr>
        </thead>
        <tbody id="learningProposalBody"></tbody>
      </table>
      <div class="grid" id="learningLeaderboardSummary" style="margin-top:8px;"></div>
      <table>
        <thead>
          <tr>
            <th data-i18n="table.category">카테고리</th><th data-i18n="table.key">키</th><th data-i18n="table.tradeCount">거래수</th><th data-i18n="table.winRate">승률</th><th data-i18n="table.totalPnl">총PnL</th><th data-i18n="table.avgPnl">평균PnL</th>
          </tr>
        </thead>
        <tbody id="learningLeaderboardBody"></tbody>
      </table>
    </div>

    <div class="panel">
      <h2 data-i18n="title.notificationThreshold">거부사유 알림/임계치</h2>
      <div class="form-grid">
        <div class="field">
          <label data-i18n="notify.enabled">알림 사용</label>
          <label class="inline-check">
            <input id="notifyEnabled" type="checkbox" />
            <span data-i18n="common.use">사용</span>
          </label>
        </div>
        <div class="field">
          <label data-i18n="notify.levels">알림 발송 레벨</label>
          <label class="inline-check"><input id="notifyLevelCritical" type="checkbox" /> critical</label>
          <label class="inline-check"><input id="notifyLevelWarn" type="checkbox" /> warn</label>
          <label class="inline-check"><input id="notifyLevelInfo" type="checkbox" /> info</label>
        </div>
        <div class="field">
          <label data-i18n="notify.profile">임계치 모드</label>
          <select id="rejectAlertProfile">
            <option value="auto">auto</option>
            <option value="safe">safe</option>
            <option value="balanced">balanced</option>
            <option value="aggressive">aggressive</option>
          </select>
        </div>
        <div class="field">
          <label data-i18n="notify.rejectWarn">거부율 경고 임계치</label>
          <input id="rejectRateWarnInput" type="number" step="0.01" min="0" max="1" />
        </div>
        <div class="field">
          <label data-i18n="notify.rejectCritical">거부율 critical 임계치</label>
          <input id="rejectRateCriticalInput" type="number" step="0.01" min="0" max="1" />
        </div>
        <div class="field">
          <label data-i18n="notify.reasonWarn">거부사유 경고 임계치</label>
          <input id="rejectReasonWarnInput" type="number" step="0.01" min="0" max="1" />
        </div>
        <div class="field">
          <label data-i18n="notify.reasonCritical">거부사유 critical 임계치</label>
          <input id="rejectReasonCriticalInput" type="number" step="0.01" min="0" max="1" />
        </div>
        <div class="field">
          <label data-i18n="notify.minSamples">최소 샘플 수</label>
          <input id="rejectReasonMinSamplesInput" type="number" min="1" />
        </div>
        <div class="field">
          <label data-i18n="notify.cooldownSeconds">쿨다운(초)</label>
          <input id="notifyCooldownSeconds" type="number" min="0" />
        </div>
        <div class="field">
          <label data-i18n="notify.maxPerHour">시간당 발송 상한(0=무제한)</label>
          <input id="notifyMaxPerHour" type="number" min="0" />
        </div>
        <div class="field">
          <label data-i18n="notify.webhook">일반 웹훅 URL</label>
          <input id="notifyWebhook" type="text" />
        </div>
        <div class="field">
          <label data-i18n="notify.slackWebhook">Slack 웹훅 URL</label>
          <input id="notifySlackWebhook" type="text" />
        </div>
        <div class="field">
          <label data-i18n="notify.telegramToken">텔레그램 Bot Token</label>
          <input id="notifyTelegramToken" type="text" placeholder="[HIDDEN]" />
        </div>
        <div class="field">
          <label data-i18n="notify.telegramChatId">텔레그램 Chat ID</label>
          <input id="notifyTelegramChatId" type="text" placeholder="[HIDDEN]" />
        </div>
        <div class="field">
          <label data-i18n="notify.includeSummary">메세지 상세 요약</label>
          <label class="inline-check">
            <input id="notifyIncludeSummary" type="checkbox" /> <span data-i18n="common.include">포함</span>
          </label>
        </div>
      </div>
      <div class="toolbar" style="margin-top:8px; gap:8px;">
        <button class="btn btn-good" onclick="saveNotificationConfig()" data-i18n="button.saveNotificationsOnly">알림 설정만 저장</button>
        <button class="btn btn-sub" onclick="loadConfig()" data-i18n="button.reloadValues">설정값 다시 불러오기</button>
      </div>
    </div>

    <div class="panel">
      <h2 data-i18n="title.configEdit">설정 편집</h2>
      <div class="toolbar" style="margin-bottom:8px;">
        <button class="btn btn-sub" onclick="loadConfig()" data-i18n="button.loadConfig">설정 불러오기</button>
        <button class="btn btn-good" onclick="saveConfig()" data-i18n="button.save">저장</button>
      </div>
      <textarea id="configJson" rows="20"></textarea>
      <p class="muted" style="margin-top:8px;" data-i18n="config.hiddenSecretHelp">API 비밀값은 화면에서 [HIDDEN]로 표시되며, 저장 시 그대로 유지됩니다.</p>
    </div>
  </div>

  <script>
    const POLL_MS = 3000;
    let clearState = { lockUntil: 0, failCount: 0 };
    const SKETCH_SOURCE_KEY = 'boss_sketch_sources_v1';
    const SKETCH_MEMO_KEY = 'boss_sketch_memo_v1';
    const SKETCH_TAB_KEY = 'boss_sketch_tab_v1';
    const SKETCH_THEME_KEY = 'boss_sketch_theme_v1';
    const SKETCH_LANGUAGE_KEY = 'boss_sketch_language_v1';
    const LANGUAGE_OPTIONS = {
      ko: { key: 'ko', label: '한국어' },
      en: { key: 'en', label: 'English' },
      zh: { key: 'zh', label: '中文' },
      ja: { key: 'ja', label: '日本語' },
      fr: { key: 'fr', label: 'Français' },
    };
    const THEME_PRESETS = {
      premium: {
        key: 'premium',
        label: '더 고급스럽게',
        className: 'theme-style-premium',
        bg1: '#0b1424',
        bg2: '#13233f',
        bg3: '#20385e',
        accent: '#d4a64a',
        panel: '#0f1b2d',
        line: '#41597b',
        text: '#eef3ff',
        muted: '#a9b7cf',
        surface: '#0a1423',
        surfaceSoft: 'rgba(10, 20, 35, 0.78)',
        fieldSurface: 'rgba(10, 19, 34, 0.92)',
        softBorder: '#314965',
        miniBtnBg: '#2f4668',
        miniBtnBorder: '#4f6788',
        mutedBoxBg: 'rgba(12, 23, 40, 0.76)',
        mutedBoxLine: '#61799a',
        fontUi: '"Pretendard", "Apple SD Gothic Neo", Arial, sans-serif',
      },
      simple: {
        key: 'simple',
        label: '더 단순하게',
        className: 'theme-style-simple',
        bg1: '#111827',
        bg2: '#18202d',
        bg3: '#1f2937',
        accent: '#cbd5e1',
        panel: '#141b24',
        line: '#374151',
        text: '#f3f4f6',
        muted: '#9ca3af',
        surface: '#0f1720',
        surfaceSoft: 'rgba(15, 23, 32, 0.76)',
        fieldSurface: 'rgba(17, 24, 39, 0.94)',
        softBorder: '#334155',
        miniBtnBg: '#1f2937',
        miniBtnBorder: '#475569',
        mutedBoxBg: 'rgba(15, 23, 32, 0.72)',
        mutedBoxLine: '#475569',
        fontUi: '"Pretendard", "Apple SD Gothic Neo", Arial, sans-serif',
      },
      light: {
        key: 'light',
        label: '라이트 테마',
        className: 'theme-style-light',
        bg1: '#f5f8fd',
        bg2: '#e8eef8',
        bg3: '#dce7f4',
        accent: '#2563eb',
        panel: '#ffffff',
        line: '#cfd8e5',
        text: '#0f172a',
        muted: '#64748b',
        surface: '#f8fbff',
        surfaceSoft: 'rgba(255, 255, 255, 0.92)',
        fieldSurface: 'rgba(248, 251, 255, 0.95)',
        softBorder: '#cfd8e5',
        miniBtnBg: '#eef4fb',
        miniBtnBorder: '#c7d5e8',
        mutedBoxBg: 'rgba(247, 250, 255, 0.9)',
        mutedBoxLine: '#c7d5e8',
        fontUi: '"Pretendard", "Apple SD Gothic Neo", Arial, sans-serif',
      },
      terminal: {
        key: 'terminal',
        label: '거래소 터미널',
        className: 'theme-style-terminal',
        bg1: '#03110f',
        bg2: '#08201d',
        bg3: '#0d332b',
        accent: '#22c55e',
        panel: '#071815',
        line: '#1f6a57',
        text: '#d8ffee',
        muted: '#89c8b4',
        surface: '#031410',
        surfaceSoft: 'rgba(4, 20, 16, 0.78)',
        fieldSurface: 'rgba(5, 24, 20, 0.92)',
        softBorder: '#1f5f4c',
        miniBtnBg: '#0b2a23',
        miniBtnBorder: '#1f6a57',
        mutedBoxBg: 'rgba(5, 21, 17, 0.74)',
        mutedBoxLine: '#1f6a57',
        fontUi: '"Consolas", "Pretendard", "Apple SD Gothic Neo", monospace',
      },
    };
    const STYLE_CLASSES = Object.values(THEME_PRESETS).map((item) => item.className);
    const I18N = { ko: {}, en: {}, zh: {}, ja: {}, fr: {} };

    function formatMessage(template, vars) {
      return String(template || '').replace(/\{(\w+)\}/g, (_m, key) => {
        const value = vars && Object.prototype.hasOwnProperty.call(vars, key) ? vars[key] : `{${key}}`;
        return value == null ? '' : String(value);
      });
    }

    function normalizeLanguage(value) {
      const raw = String(value || 'ko').trim().toLowerCase().replace('_', '-');
      const base = raw.split('-')[0];
      return LANGUAGE_OPTIONS[base] ? base : 'ko';
    }

    function languageLabel(language) {
      const normalized = normalizeLanguage(language);
      return (LANGUAGE_OPTIONS[normalized] || LANGUAGE_OPTIONS.ko).label;
    }

    function t(key, vars, fallback) {
      const lang = normalizeLanguage(window.__currentLanguage || 'ko');
      const pack = I18N[lang] || I18N.ko;
      const base = I18N.ko || {};
      const template = pack[key] || base[key] || fallback || key;
      return formatMessage(template, vars);
    }

    function tr(koText, enText) {
      return normalizeLanguage(window.__currentLanguage || 'ko') === 'ko' ? koText : enText;
    }

    function readStoredLanguage() {
      try {
        return normalizeLanguage(localStorage.getItem(SKETCH_LANGUAGE_KEY) || 'ko');
      } catch (_e) {
        return 'ko';
      }
    }

    function setLanguagePresetSelect(language) {
      const node = document.getElementById('languagePreset');
      if (node) node.value = normalizeLanguage(language);
    }

    function getConfiguredLanguage() {
      const cfg = window.__loadedConfig || {};
      const ui = cfg.ui || {};
      return normalizeLanguage(ui.language || 'ko');
    }

    function localizeStaticText() {
      document.documentElement.lang = normalizeLanguage(window.__currentLanguage || 'ko');
      document.title = t('title.page', null, 'AI 트레이딩 봇 대시보드');
      document.querySelectorAll('[data-i18n]').forEach((node) => {
        node.textContent = t(node.getAttribute('data-i18n'));
      });
      document.querySelectorAll('[data-i18n-placeholder]').forEach((node) => {
        node.placeholder = t(node.getAttribute('data-i18n-placeholder'));
      });
    }

    function applyLanguage(language, persist) {
      const normalized = normalizeLanguage(language);
      window.__currentLanguage = normalized;
      setLanguagePresetSelect(normalized);
      localizeStaticText();
      if (persist !== false) {
        localStorage.setItem(SKETCH_LANGUAGE_KEY, normalized);
      }
    }

    function loadLanguage() {
      applyLanguage(readStoredLanguage(), false);
    }

    Object.assign(I18N.ko, {
      'title.page': 'AI 트레이딩 봇 대시보드',
      'title.main': 'AI 트레이딩 봇 운영 대시보드',
      'title.validation': '검증 리포트 비교 대시보드',
      'title.account': '계정/포지션',
      'title.risk': '리스크 상태',
      'title.riskEvents': '리스크 이벤트',
      'title.rejectDashboard': '거부사유 운영 대시보드',
      'title.regimeStrategy': '레짐 기반 전략 추천',
      'title.pnlCurve': '수익 곡선',
      'title.executions': '실행 내역',
      'title.learning': 'AI 복기/튜닝',
      'title.notificationThreshold': '거부사유 알림/임계치',
      'title.configEdit': '설정 편집',
      'toolbar.runOnce': '1회 실행',
      'toolbar.autoStart': '자동 시작',
      'toolbar.stop': '중지',
      'toolbar.readiness': '실거래 준비 점검',
      'toolbar.readinessReport': '점검 리포트 저장',
      'toolbar.rehearsal': '실거래 리허설 계획',
      'toolbar.rehearsalReport': '리허설 리포트 저장',
      'toolbar.exchangeProbe': '거래소 파라미터 점검',
      'toolbar.exchangeReport': '거래소 점검 리포트 저장',
      'toolbar.aiTest': 'AI 연결 테스트',
      'toolbar.refresh': '새로고침',
      'unit.seconds': '초',
      'unit.days': '일',
      'label.lastMessage': '마지막 메시지',
      'validation.testWarn': '검증 알람 테스트(경고)',
      'validation.testCritical': '검증 알람 테스트(치명)',
      'validation.noHistory': '검증 이력 없음',
      'tab.start': '시작',
      'tab.running': '진행중인',
      'tab.settings': '내설정',
      'tab.api': '연결 API',
      'tab.logging': '로깅',
      'sketch.status.runIdle': '실행: -',
      'sketch.status.apiIdle': 'API: -',
      'sketch.status.loopIdle': '자동: -',
      'sketch.action.runOnceNow': '바로 1회 실행',
      'sketch.marketAnalysis': '시황 분석',
      'sketch.waitingData': '데이터 대기 중...',
      'sketch.evidenceNews': '* 근거1 (뉴스/심리):',
      'sketch.noEvidenceYet': '아직 수집된 근거가 없습니다.',
      'sketch.strategy': '매매 전략',
      'sketch.waitingStrategy': '전략 추천 대기 중...',
      'sketch.evidenceStrategy': '* 근거2:',
      'sketch.waitingStrategyEvidence': '전략 근거 대기 중...',
      'sketch.bot': '매매 봇',
      'sketch.monitoring': '실시간 모니터링',
      'sketch.waitingExecutionData': '체결 데이터 대기 중...',
      'sketch.errorNormal': '오류 점검: 정상',
      'sketch.progressState': '* 진행 상태:',
      'sketch.waitingCycleState': '주기/상태 데이터 대기 중...',
      'sketch.mySettings': '내 설정',
      'sketch.waitingConfigSummary': '설정 요약 대기 중...',
      'sketch.loadingStrategyConfig': '전략 설정 로딩 중...',
      'sketch.loadingRiskConfig': '리스크 설정 로딩 중...',
      'sketch.apiStatus': 'API 상태',
      'sketch.waitingApiStatus': 'API 연결 상태 대기 중...',
      'sketch.noAiTestYet': '아직 테스트를 실행하지 않았습니다.',
      'sketch.opsLogging': '운영 로깅',
      'sketch.waitingLogData': '로그 데이터 대기 중...',
      'side.sourceIntegration': '소스 연동',
      'side.researchSources': '심리 분석/리서치 소스',
      'side.researchSourcesHelp': '사용자 소스는 아래에서 커스텀으로 추가합니다.',
      'side.customSources': '사용자 커스텀 소스',
      'side.noCustomSources': '등록된 커스텀 소스가 없습니다.',
      'side.strategyMemo': '사용자 전략 메모',
      'side.uiStyle': 'UI 스타일',
      'side.language': '언어 설정',
      'side.languageHelp': '저장하면 이후 접속에도 선택 언어를 유지합니다.',
      'theme.premium': '더 고급스럽게',
      'theme.simple': '더 단순하게',
      'theme.light': '라이트 테마',
      'theme.terminal': '거래소 터미널',
      'theme.bg1': '배경 1',
      'theme.bg2': '배경 2',
      'theme.bg3': '배경 3',
      'theme.accent': '강조색',
      'theme.panel': '패널색',
      'theme.line': '라인색',
      'table.time': '시간',
      'table.datetime': '일시',
      'table.overallPassed': '전체통과',
      'table.backtest': 'Backtest',
      'table.walkForward': 'WalkForward',
      'table.pnlUsdt': 'PnL(USDT)',
      'table.winRate': '승률',
      'table.mdd': 'MDD',
      'table.symbol': '종목',
      'table.strategy': '전략',
      'table.status': '상태',
      'table.pnl': 'PnL',
      'table.reason': '사유',
      'table.event': '이벤트',
      'table.previousReason': '이전 사유',
      'table.currentReason': '현재 사유',
      'table.note': '비고',
      'table.rejectReason': '거부사유',
      'table.count': '건수',
      'table.ratio': '비율',
      'table.regime': '레짐',
      'table.direction': '방향',
      'table.score': '점수',
      'table.confidence': '신뢰도',
      'table.requestUsdt': '요청금액(USDT)',
      'table.filledUsdt': '체결금액(USDT)',
      'table.leverage': '레버리지',
      'table.expectedPrice': '예상가',
      'table.fillPrice': '체결가',
      'table.slippageBps': '슬리피지(bps)',
      'table.attempts': '시도',
      'table.retryReason': '재시도사유',
      'table.feeUsdt': '수수료(USDT)',
      'table.grossPnl': 'GrossPnL',
      'table.netPnl': 'NetPnL',
      'table.entryReason': '진입근거',
      'table.marketState': '시장상태',
      'table.apply': '적용',
      'table.suggestion': '제안',
      'table.currentWeight': '현재 가중치',
      'table.suggestedWeight': '제안 가중치',
      'table.select': '선택',
      'table.currentValue': '현재',
      'table.suggestedValue': '제안값',
      'table.category': '카테고리',
      'table.key': '키',
      'table.tradeCount': '거래수',
      'table.totalPnl': '총PnL',
      'table.avgPnl': '평균PnL',
      'filter.status': '상태',
      'filter.all': '전체',
      'filter.partialFill': '부분체결',
      'filter.hasValue': '있음',
      'filter.notValue': '아님',
      'filter.rejectReason': '거부사유',
      'learning.windowDays': '회고 기간',
      'notify.enabled': '알림 사용',
      'notify.levels': '알림 발송 레벨',
      'notify.profile': '임계치 모드',
      'notify.rejectWarn': '거부율 경고 임계치',
      'notify.rejectCritical': '거부율 critical 임계치',
      'notify.reasonWarn': '거부사유 경고 임계치',
      'notify.reasonCritical': '거부사유 critical 임계치',
      'notify.minSamples': '최소 샘플 수',
      'notify.cooldownSeconds': '쿨다운(초)',
      'notify.maxPerHour': '시간당 발송 상한(0=무제한)',
      'notify.webhook': '일반 웹훅 URL',
      'notify.slackWebhook': 'Slack 웹훅 URL',
      'notify.telegramToken': '텔레그램 Bot Token',
      'notify.telegramChatId': '텔레그램 Chat ID',
      'notify.includeSummary': '메세지 상세 요약',
      'common.use': '사용',
      'common.include': '포함',
      'button.saveStrategyConfig': '전략 설정 저장',
      'button.saveRiskConfig': '리스크 설정 저장',
      'button.goToConfig': '설정 JSON 이동',
      'button.reloadConfig': '설정 다시 로드',
      'button.goToExecutions': '상세 실행내역 이동',
      'button.add': '추가',
      'button.saveMemo': '메모 저장',
      'button.preview': '미리보기',
      'button.saveSetting': '설정 저장',
      'button.applyColors': '색상 적용',
      'button.resetDefault': '기본 복원',
      'button.clearRisk': '리스크 해제',
      'button.query': '조회',
      'button.loadAnalysis': '분석 조회',
      'button.applySelectedStrategy': '선택 전략 적용',
      'button.applyAllSuggestions': '전체 제안 일괄 적용',
      'button.approvePending': '대기 제안 승인 적용',
      'button.rejectPending': '대기 제안 거절',
      'button.saveNotificationsOnly': '알림 설정만 저장',
      'button.reloadValues': '설정값 다시 불러오기',
      'button.loadConfig': '설정 불러오기',
      'button.save': '저장',
      'config.hiddenSecretHelp': 'API 비밀값은 화면에서 [HIDDEN]로 표시되며, 저장 시 그대로 유지됩니다.',
      'placeholder.liveToken': 'LIVE 시작 토큰',
      'placeholder.customSource': '예: https://example.com/feed',
      'placeholder.strategyMemo': '사용자 전략 아이디어/규칙을 메모하세요.',
      'message.themePreview': 'UI 스타일 미리보기: {label}',
      'message.customThemeApplied': '커스텀 UI 색상을 적용했습니다.',
      'message.themeReset': '설정에 저장된 UI 스타일로 복원했습니다.',
      'message.themeSaved': 'UI 스타일 설정 저장: {label}',
      'message.themeSaveFailed': 'UI 스타일 저장 실패: {error}',
      'message.languagePreview': '언어 미리보기: {label}',
      'message.languageSaved': '언어 설정 저장: {label}',
      'message.languageSaveFailed': '언어 저장 실패: {error}',
      'common.on': 'ON',
      'common.off': 'OFF',
      'common.none': '없음',
      'common.normal': '정상',
      'common.waiting': '대기',
      'common.ready': 'READY',
      'common.check': 'CHECK',
      'common.pass': 'PASS',
      'common.fail': 'FAIL',
      'common.ok': 'OK',
      'common.block': 'BLOCK',
    });

    Object.assign(I18N.en, {
      'title.page': 'AI Trading Bot Dashboard',
      'title.main': 'AI Trading Bot Operations Dashboard',
      'title.validation': 'Validation Report Comparison Dashboard',
      'title.account': 'Account / Positions',
      'title.risk': 'Risk Status',
      'title.riskEvents': 'Risk Events',
      'title.rejectDashboard': 'Reject Reason Dashboard',
      'title.regimeStrategy': 'Regime-Based Strategy Recommendations',
      'title.pnlCurve': 'PnL Curve',
      'title.executions': 'Executions',
      'title.learning': 'AI Review / Tuning',
      'title.notificationThreshold': 'Reject Alerts / Thresholds',
      'title.configEdit': 'Config Editor',
      'toolbar.runOnce': 'Run Once',
      'toolbar.autoStart': 'Start Auto',
      'toolbar.stop': 'Stop',
      'toolbar.readiness': 'Live Readiness Check',
      'toolbar.readinessReport': 'Save Readiness Report',
      'toolbar.rehearsal': 'Live Rehearsal Plan',
      'toolbar.rehearsalReport': 'Save Rehearsal Report',
      'toolbar.exchangeProbe': 'Exchange Parameter Check',
      'toolbar.exchangeReport': 'Save Exchange Report',
      'toolbar.aiTest': 'AI Connection Test',
      'toolbar.refresh': 'Refresh',
      'unit.seconds': 's',
      'unit.days': 'days',
      'label.lastMessage': 'Last message',
      'validation.testWarn': 'Validation Alert Test (Warn)',
      'validation.testCritical': 'Validation Alert Test (Critical)',
      'validation.noHistory': 'No validation history',
      'tab.start': 'Start',
      'tab.running': 'Running',
      'tab.settings': 'My Settings',
      'tab.api': 'Connected APIs',
      'tab.logging': 'Logging',
      'sketch.status.runIdle': 'Run: -',
      'sketch.status.apiIdle': 'API: -',
      'sketch.status.loopIdle': 'Auto: -',
      'sketch.action.runOnceNow': 'Run Once Now',
      'sketch.marketAnalysis': 'Market Analysis',
      'sketch.waitingData': 'Waiting for data...',
      'sketch.evidenceNews': '* Evidence 1 (News/Sentiment):',
      'sketch.noEvidenceYet': 'No collected evidence yet.',
      'sketch.strategy': 'Trading Strategy',
      'sketch.waitingStrategy': 'Waiting for strategy recommendations...',
      'sketch.evidenceStrategy': '* Evidence 2:',
      'sketch.waitingStrategyEvidence': 'Waiting for strategy evidence...',
      'sketch.bot': 'Trading Bots',
      'sketch.monitoring': 'Real-Time Monitoring',
      'sketch.waitingExecutionData': 'Waiting for execution data...',
      'sketch.errorNormal': 'Error check: normal',
      'sketch.progressState': '* Progress:',
      'sketch.waitingCycleState': 'Waiting for cycle/status data...',
      'sketch.mySettings': 'My Settings',
      'sketch.waitingConfigSummary': 'Waiting for config summary...',
      'sketch.loadingStrategyConfig': 'Loading strategy settings...',
      'sketch.loadingRiskConfig': 'Loading risk settings...',
      'sketch.apiStatus': 'API Status',
      'sketch.waitingApiStatus': 'Waiting for API status...',
      'sketch.noAiTestYet': 'No test has been run yet.',
      'sketch.opsLogging': 'Operations Logging',
      'sketch.waitingLogData': 'Waiting for log data...',
      'side.sourceIntegration': 'Source Integration',
      'side.researchSources': 'Sentiment / Research Sources',
      'side.researchSourcesHelp': 'Add custom user sources below.',
      'side.customSources': 'Custom User Sources',
      'side.noCustomSources': 'No custom sources registered.',
      'side.strategyMemo': 'Strategy Memo',
      'side.uiStyle': 'UI Style',
      'side.language': 'Language',
      'side.languageHelp': 'Saved language is kept for future sessions.',
      'theme.premium': 'Premium',
      'theme.simple': 'Simple',
      'theme.light': 'Light',
      'theme.terminal': 'Exchange Terminal',
      'theme.bg1': 'Background 1',
      'theme.bg2': 'Background 2',
      'theme.bg3': 'Background 3',
      'theme.accent': 'Accent',
      'theme.panel': 'Panel',
      'theme.line': 'Line',
      'table.time': 'Time',
      'table.datetime': 'Date/Time',
      'table.overallPassed': 'Overall Pass',
      'table.backtest': 'Backtest',
      'table.walkForward': 'WalkForward',
      'table.pnlUsdt': 'PnL (USDT)',
      'table.winRate': 'Win Rate',
      'table.mdd': 'MDD',
      'table.symbol': 'Symbol',
      'table.strategy': 'Strategy',
      'table.status': 'Status',
      'table.pnl': 'PnL',
      'table.reason': 'Reason',
      'table.event': 'Event',
      'table.previousReason': 'Previous Reason',
      'table.currentReason': 'Current Reason',
      'table.note': 'Note',
      'table.rejectReason': 'Reject Reason',
      'table.count': 'Count',
      'table.ratio': 'Ratio',
      'table.regime': 'Regime',
      'table.direction': 'Direction',
      'table.score': 'Score',
      'table.confidence': 'Confidence',
      'table.requestUsdt': 'Requested (USDT)',
      'table.filledUsdt': 'Filled (USDT)',
      'table.leverage': 'Leverage',
      'table.expectedPrice': 'Expected Price',
      'table.fillPrice': 'Fill Price',
      'table.slippageBps': 'Slippage (bps)',
      'table.attempts': 'Attempts',
      'table.retryReason': 'Retry Reason',
      'table.feeUsdt': 'Fee (USDT)',
      'table.grossPnl': 'Gross PnL',
      'table.netPnl': 'Net PnL',
      'table.entryReason': 'Entry Rationale',
      'table.marketState': 'Market State',
      'table.apply': 'Apply',
      'table.suggestion': 'Suggestion',
      'table.currentWeight': 'Current Weight',
      'table.suggestedWeight': 'Suggested Weight',
      'table.select': 'Select',
      'table.currentValue': 'Current',
      'table.suggestedValue': 'Suggested',
      'table.category': 'Category',
      'table.key': 'Key',
      'table.tradeCount': 'Trades',
      'table.totalPnl': 'Total PnL',
      'table.avgPnl': 'Avg PnL',
      'filter.status': 'Status',
      'filter.all': 'All',
      'filter.partialFill': 'Partial Fill',
      'filter.hasValue': 'Yes',
      'filter.notValue': 'No',
      'filter.rejectReason': 'Reject Reason',
      'learning.windowDays': 'Lookback',
      'notify.enabled': 'Alerts Enabled',
      'notify.levels': 'Alert Levels',
      'notify.profile': 'Threshold Profile',
      'notify.rejectWarn': 'Reject Rate Warn Threshold',
      'notify.rejectCritical': 'Reject Rate Critical Threshold',
      'notify.reasonWarn': 'Reason Warn Threshold',
      'notify.reasonCritical': 'Reason Critical Threshold',
      'notify.minSamples': 'Minimum Samples',
      'notify.cooldownSeconds': 'Cooldown (sec)',
      'notify.maxPerHour': 'Max per Hour (0=unlimited)',
      'notify.webhook': 'Generic Webhook URL',
      'notify.slackWebhook': 'Slack Webhook URL',
      'notify.telegramToken': 'Telegram Bot Token',
      'notify.telegramChatId': 'Telegram Chat ID',
      'notify.includeSummary': 'Detailed Message Summary',
      'common.use': 'Use',
      'common.include': 'Include',
      'button.saveStrategyConfig': 'Save Strategy Settings',
      'button.saveRiskConfig': 'Save Risk Settings',
      'button.goToConfig': 'Open Config JSON',
      'button.reloadConfig': 'Reload Config',
      'button.goToExecutions': 'Open Execution Details',
      'button.add': 'Add',
      'button.saveMemo': 'Save Memo',
      'button.preview': 'Preview',
      'button.saveSetting': 'Save',
      'button.applyColors': 'Apply Colors',
      'button.resetDefault': 'Reset',
      'button.clearRisk': 'Clear Risk Halt',
      'button.query': 'Query',
      'button.loadAnalysis': 'Load Analysis',
      'button.applySelectedStrategy': 'Apply Selected',
      'button.applyAllSuggestions': 'Apply All Suggestions',
      'button.approvePending': 'Approve Pending',
      'button.rejectPending': 'Reject Pending',
      'button.saveNotificationsOnly': 'Save Alerts Only',
      'button.reloadValues': 'Reload Values',
      'button.loadConfig': 'Load Config',
      'button.save': 'Save',
      'config.hiddenSecretHelp': 'API secrets are shown as [HIDDEN] and kept unchanged when saved.',
      'placeholder.liveToken': 'LIVE start token',
      'placeholder.customSource': 'e.g. https://example.com/feed',
      'placeholder.strategyMemo': 'Write your strategy ideas and rules.',
      'message.themePreview': 'UI style preview: {label}',
      'message.customThemeApplied': 'Custom UI colors applied.',
      'message.themeReset': 'Restored saved UI style.',
      'message.themeSaved': 'UI style saved: {label}',
      'message.themeSaveFailed': 'Failed to save UI style: {error}',
      'message.languagePreview': 'Language preview: {label}',
      'message.languageSaved': 'Language saved: {label}',
      'message.languageSaveFailed': 'Failed to save language: {error}',
      'common.on': 'ON',
      'common.off': 'OFF',
      'common.none': 'None',
      'common.normal': 'Normal',
      'common.waiting': 'Waiting',
      'common.ready': 'READY',
      'common.check': 'CHECK',
      'common.pass': 'PASS',
      'common.fail': 'FAIL',
      'common.ok': 'OK',
      'common.block': 'BLOCK',
    });

    Object.assign(I18N.zh, I18N.en, {
      'title.page': 'AI 交易机器人仪表板',
      'title.main': 'AI 交易机器人运营仪表板',
      'title.validation': '验证报告对比仪表板',
      'title.account': '账户/仓位',
      'title.risk': '风险状态',
      'title.riskEvents': '风险事件',
      'title.rejectDashboard': '拒单原因仪表板',
      'title.regimeStrategy': '市场状态策略推荐',
      'title.pnlCurve': '收益曲线',
      'title.executions': '执行记录',
      'title.learning': 'AI 复盘/调优',
      'title.notificationThreshold': '拒单告警/阈值',
      'title.configEdit': '配置编辑',
      'toolbar.runOnce': '执行一次',
      'toolbar.autoStart': '自动开始',
      'toolbar.stop': '停止',
      'toolbar.readiness': '实盘准备检查',
      'toolbar.readinessReport': '保存检查报告',
      'toolbar.rehearsal': '实盘演练计划',
      'toolbar.rehearsalReport': '保存演练报告',
      'toolbar.exchangeProbe': '交易所参数检查',
      'toolbar.exchangeReport': '保存交易所报告',
      'toolbar.aiTest': 'AI 连接测试',
      'toolbar.refresh': '刷新',
      'unit.seconds': '秒',
      'unit.days': '天',
      'label.lastMessage': '最后消息',
      'tab.start': '开始',
      'tab.running': '运行中',
      'tab.settings': '我的设置',
      'tab.api': 'API 连接',
      'tab.logging': '日志',
      'side.sourceIntegration': '数据源联动',
      'side.language': '语言',
      'side.languageHelp': '保存后会在后续访问中保持所选语言。',
      'theme.premium': '高级',
      'theme.simple': '简洁',
      'theme.light': '浅色',
      'theme.terminal': '交易终端',
      'button.preview': '预览',
      'button.saveSetting': '保存',
      'button.save': '保存',
      'button.add': '添加',
      'common.use': '使用',
      'common.include': '包含',
      'placeholder.liveToken': 'LIVE 启动令牌',
      'message.languagePreview': '语言预览: {label}',
      'message.languageSaved': '语言已保存: {label}',
      'message.languageSaveFailed': '保存语言失败: {error}',
    });

    Object.assign(I18N.ja, I18N.en, {
      'title.page': 'AI トレーディングボット ダッシュボード',
      'title.main': 'AI トレーディングボット運用ダッシュボード',
      'title.validation': '検証レポート比較ダッシュボード',
      'title.account': '口座/ポジション',
      'title.risk': 'リスク状態',
      'title.riskEvents': 'リスクイベント',
      'title.rejectDashboard': '拒否理由ダッシュボード',
      'title.regimeStrategy': 'レジーム別戦略推薦',
      'title.pnlCurve': '損益カーブ',
      'title.executions': '実行履歴',
      'title.learning': 'AI レビュー/調整',
      'title.notificationThreshold': '拒否アラート/閾値',
      'title.configEdit': '設定編集',
      'toolbar.runOnce': '1回実行',
      'toolbar.autoStart': '自動開始',
      'toolbar.stop': '停止',
      'toolbar.readiness': '実取引準備チェック',
      'toolbar.rehearsal': '実取引リハーサル計画',
      'toolbar.exchangeProbe': '取引所パラメータ点検',
      'toolbar.aiTest': 'AI 接続テスト',
      'toolbar.refresh': '更新',
      'unit.seconds': '秒',
      'unit.days': '日',
      'label.lastMessage': '最新メッセージ',
      'tab.start': '開始',
      'tab.running': '実行中',
      'tab.settings': '設定',
      'tab.api': 'API 接続',
      'tab.logging': 'ログ',
      'side.sourceIntegration': 'ソース連携',
      'side.language': '言語',
      'side.languageHelp': '保存すると次回以降も選択言語を維持します。',
      'theme.premium': 'プレミアム',
      'theme.simple': 'シンプル',
      'theme.light': 'ライト',
      'theme.terminal': '取引所ターミナル',
      'button.preview': 'プレビュー',
      'button.saveSetting': '保存',
      'button.save': '保存',
      'button.add': '追加',
      'common.use': '使用',
      'common.include': '含む',
      'placeholder.liveToken': 'LIVE 開始トークン',
      'message.languagePreview': '言語プレビュー: {label}',
      'message.languageSaved': '言語設定保存: {label}',
      'message.languageSaveFailed': '言語保存失敗: {error}',
    });

    Object.assign(I18N.fr, I18N.en, {
      'title.page': 'Tableau de bord du bot de trading IA',
      'title.main': 'Tableau de bord d’exploitation du bot de trading IA',
      'title.validation': 'Comparaison des rapports de validation',
      'title.account': 'Compte / Positions',
      'title.risk': 'Statut du risque',
      'title.riskEvents': 'Événements de risque',
      'title.rejectDashboard': 'Tableau des motifs de rejet',
      'title.regimeStrategy': 'Recommandations par régime',
      'title.pnlCurve': 'Courbe de PnL',
      'title.executions': 'Exécutions',
      'title.learning': 'Revue / Ajustement IA',
      'title.notificationThreshold': 'Alertes de rejet / Seuils',
      'title.configEdit': 'Édition de configuration',
      'toolbar.runOnce': 'Exécuter une fois',
      'toolbar.autoStart': 'Démarrer auto',
      'toolbar.stop': 'Arrêter',
      'toolbar.readiness': 'Vérification live',
      'toolbar.rehearsal': 'Plan de répétition live',
      'toolbar.exchangeProbe': 'Vérifier les paramètres exchange',
      'toolbar.aiTest': 'Test de connexion IA',
      'toolbar.refresh': 'Actualiser',
      'unit.seconds': 's',
      'unit.days': 'jours',
      'label.lastMessage': 'Dernier message',
      'tab.start': 'Démarrer',
      'tab.running': 'En cours',
      'tab.settings': 'Mes réglages',
      'tab.api': 'API connectées',
      'tab.logging': 'Journalisation',
      'side.sourceIntegration': 'Intégration des sources',
      'side.language': 'Langue',
      'side.languageHelp': 'La langue enregistrée est conservée pour les prochaines sessions.',
      'theme.premium': 'Premium',
      'theme.simple': 'Simple',
      'theme.light': 'Clair',
      'theme.terminal': 'Terminal exchange',
      'button.preview': 'Aperçu',
      'button.saveSetting': 'Enregistrer',
      'button.save': 'Enregistrer',
      'button.add': 'Ajouter',
      'common.use': 'Utiliser',
      'common.include': 'Inclure',
      'placeholder.liveToken': 'Jeton LIVE de démarrage',
      'message.languagePreview': 'Aperçu de langue : {label}',
      'message.languageSaved': 'Langue enregistrée : {label}',
      'message.languageSaveFailed': 'Échec de l’enregistrement de la langue : {error}',
    });

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

    function resolveTheme(theme) {
      if (typeof theme === 'string') {
        return THEME_PRESETS[theme] || THEME_PRESETS.premium;
      }
      if (!theme || typeof theme !== 'object') {
        return THEME_PRESETS.premium;
      }
      const key = typeof theme.key === 'string' ? theme.key : 'premium';
      const base = THEME_PRESETS[key] || THEME_PRESETS.premium;
      return { ...base, ...theme, key, className: base.className };
    }

    function setThemePresetSelect(key) {
      const node = document.getElementById('themePreset');
      if (node && typeof key === 'string' && THEME_PRESETS[key]) {
        node.value = key;
      }
    }

    function getConfiguredThemeKey() {
      const cfg = window.__loadedConfig || {};
      const ui = cfg.ui || {};
      const raw = String(ui.style_preset || 'premium').trim().toLowerCase();
      return THEME_PRESETS[raw] ? raw : 'premium';
    }

    function themePresetLabel(key) {
      const normalized = THEME_PRESETS[key] ? key : 'premium';
      return t(`theme.${normalized}`, null, (THEME_PRESETS[normalized] || THEME_PRESETS.premium).label);
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
      const selected = resolveTheme(theme);
      const root = document.documentElement;
      document.body.classList.remove(...STYLE_CLASSES);
      document.body.classList.add(selected.className);
      root.style.setProperty('--bg', `linear-gradient(140deg, ${selected.bg1}, ${selected.bg2} 48%, ${selected.bg3})`);
      root.style.setProperty('--accent', selected.accent);
      root.style.setProperty('--panel', hexToRgba(selected.panel, 0.94));
      root.style.setProperty('--line', selected.line);
      root.style.setProperty('--text', selected.text);
      root.style.setProperty('--muted', selected.muted);
      root.style.setProperty('--surface', selected.surface);
      root.style.setProperty('--surface-soft', selected.surfaceSoft);
      root.style.setProperty('--field-surface', selected.fieldSurface);
      root.style.setProperty('--soft-border', selected.softBorder);
      root.style.setProperty('--mini-btn-bg', selected.miniBtnBg);
      root.style.setProperty('--mini-btn-border', selected.miniBtnBorder);
      root.style.setProperty('--muted-box-bg', selected.mutedBoxBg);
      root.style.setProperty('--muted-box-line', selected.mutedBoxLine);
      root.style.setProperty('--font-ui', selected.fontUi);
      if (persist !== false) {
        localStorage.setItem(SKETCH_THEME_KEY, JSON.stringify(selected));
      }
      setThemeInputs(selected);
      setThemePresetSelect(selected.key);
    }

    function applyThemePreset() {
      const node = document.getElementById('themePreset');
      const key = node ? node.value : 'premium';
      const preset = THEME_PRESETS[key] || THEME_PRESETS.premium;
      applyTheme(preset, true);
      document.getElementById('lastMessage').textContent = t('message.themePreview', { label: themePresetLabel(preset.key) });
    }

    function applyCustomTheme() {
      const base = resolveTheme(document.getElementById('themePreset')?.value || getConfiguredThemeKey());
      applyTheme({ ...base, ...getThemeFromInputs() }, true);
      document.getElementById('lastMessage').textContent = t('message.customThemeApplied');
    }

    function resetTheme() {
      const key = getConfiguredThemeKey();
      applyTheme(THEME_PRESETS[key] || THEME_PRESETS.premium, true);
      document.getElementById('lastMessage').textContent = t('message.themeReset');
    }

    function loadTheme() {
      const stored = readStoredTheme();
      applyTheme(stored || THEME_PRESETS.premium, false);
    }

    async function saveThemeStyleConfig() {
      try {
        const node = document.getElementById('themePreset');
        const key = node ? node.value : 'premium';
        const preset = THEME_PRESETS[key] || THEME_PRESETS.premium;
        await apiPost('/api/config', { ui: { style_preset: preset.key } });
        applyTheme(preset, true);
        await loadConfig();
        document.getElementById('lastMessage').textContent = t('message.themeSaved', { label: themePresetLabel(preset.key) });
      } catch (e) {
        document.getElementById('lastMessage').textContent = t('message.themeSaveFailed', { error: e.message }, 'UI 스타일 저장 실패: ' + e.message);
      }
    }

    async function saveLanguageConfig() {
      try {
        const node = document.getElementById('languagePreset');
        const lang = normalizeLanguage(node ? node.value : 'ko');
        await apiPost('/api/config', { ui: { language: lang } });
        applyLanguage(lang, true);
        await loadConfig();
        document.getElementById('lastMessage').textContent = t('message.languageSaved', { label: languageLabel(lang) });
      } catch (e) {
        document.getElementById('lastMessage').textContent = t('message.languageSaveFailed', { error: e.message }, '언어 저장 실패: ' + e.message);
      }
    }

    function applyLanguagePreview() {
      const node = document.getElementById('languagePreset');
      const lang = normalizeLanguage(node ? node.value : 'ko');
      applyLanguage(lang, true);
      if (window.__loadedConfig) {
        renderSketchConfigSummary(window.__loadedConfig);
        renderNotificationSettings(window.__loadedConfig);
      }
      refreshAll();
      loadLearning();
      document.getElementById('lastMessage').textContent = t('message.languagePreview', { label: languageLabel(lang) });
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
        node.innerHTML = `<li>${tr('등록된 커스텀 소스가 없습니다.', 'No custom sources registered.')}</li>`;
        return;
      }
      node.innerHTML = values.map((item, idx) => `
        <li>
          <span>${item}</span>
          <button class="btn-mini" style="margin-left:6px;" onclick="removeSketchSource(${idx})">${tr('삭제', 'Delete')}</button>
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
        document.getElementById('lastMessage').textContent = tr('이미 등록된 커스텀 소스입니다.', 'This custom source is already registered.');
        return;
      }
      values.unshift(value);
      writeSketchSources(values.slice(0, 20));
      input.value = '';
      renderSketchSources();
      document.getElementById('lastMessage').textContent = tr('커스텀 소스를 추가했습니다.', 'Custom source added.');
    }

    function removeSketchSource(index) {
      const values = readSketchSources();
      const i = Number(index);
      if (!Number.isInteger(i) || i < 0 || i >= values.length) return;
      values.splice(i, 1);
      writeSketchSources(values);
      renderSketchSources();
      document.getElementById('lastMessage').textContent = tr('커스텀 소스를 삭제했습니다.', 'Custom source removed.');
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
      document.getElementById('lastMessage').textContent = tr('전략 메모를 저장했습니다.', 'Strategy memo saved.');
    }

    function renderSketchStrategyEditor(cfg) {
      const wrap = document.getElementById('sketchStrategyEditor');
      if (!wrap) return;
      const config = cfg || {};
      const strategies = config.strategies || {};
      const names = Object.keys(strategies).sort();
      if (!names.length) {
        wrap.innerHTML = `<div class="muted">${tr('전략 설정이 없습니다.', 'No strategy settings found.')}</div>`;
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
              <th>${tr('전략', 'Strategy')}</th><th>${tr('사용', 'Enabled')}</th><th>${tr('가중치', 'Weight')}</th>
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
        { key: 'daily_max_loss_pct', label: tr('일일 최대손실(비율)', 'Daily max loss (ratio)'), step: '0.005', min: '0', max: '1', type: 'float' },
        { key: 'max_total_exposure', label: tr('총 노출 상한(비율)', 'Total exposure cap (ratio)'), step: '0.01', min: '0', max: '1', type: 'float' },
        { key: 'max_symbol_exposure', label: tr('종목 노출 상한(비율)', 'Symbol exposure cap (ratio)'), step: '0.01', min: '0', max: '1', type: 'float' },
        { key: 'max_open_positions', label: tr('최대 포지션 수', 'Max open positions'), step: '1', min: '1', max: '30', type: 'int' },
        { key: 'max_daily_trades', label: tr('일일 최대 거래수', 'Max daily trades'), step: '1', min: '1', max: '500', type: 'int' },
        { key: 'max_leverage', label: tr('최대 레버리지', 'Max leverage'), step: '0.5', min: '1', max: '20', type: 'float' },
        { key: 'min_signal_confidence', label: tr('최소 신호 신뢰도', 'Minimum signal confidence'), step: '0.01', min: '0', max: '1', type: 'float' },
        { key: 'max_slippage_bps', label: tr('최대 슬리피지(bps)', 'Max slippage (bps)'), step: '1', min: '1', max: '300', type: 'float' },
        { key: 'min_expectancy_pct', label: tr('최소 기대수익(비율)', 'Minimum expectancy (ratio)'), step: '0.005', min: '0', max: '1', type: 'float' },
        { key: 'cooldown_minutes', label: tr('쿨다운(분)', 'Cooldown (min)'), step: '1', min: '0', max: '240', type: 'int' },
        { key: 'max_consecutive_losses', label: tr('최대 연속손실', 'Max consecutive losses'), step: '1', min: '1', max: '20', type: 'int' },
        { key: 'max_reject_ratio', label: tr('최대 거부율(비율)', 'Max reject rate (ratio)'), step: '0.01', min: '0', max: '1', type: 'float' },
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
              <th>${tr('리스크 항목', 'Risk Item')}</th><th>${tr('값', 'Value')}</th>
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
          document.getElementById('lastMessage').textContent = tr('저장할 전략 설정이 없습니다.', 'No strategy settings to save.');
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
        document.getElementById('lastMessage').textContent = tr('전략 ON/OFF 및 가중치를 저장했습니다.', 'Strategy enabled flags and weights saved.');
        await loadConfig();
        await refreshAll();
      } catch (e) {
        document.getElementById('lastMessage').textContent = tr('전략 설정 저장 실패: ', 'Failed to save strategy settings: ') + e.message;
      }
    }

    async function saveSketchRiskConfig() {
      try {
        const inputs = [...document.querySelectorAll('#sketchRiskEditor .sketch-risk-input')];
        if (!inputs.length) {
          document.getElementById('lastMessage').textContent = tr('저장할 리스크 설정이 없습니다.', 'No risk settings to save.');
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
        document.getElementById('lastMessage').textContent = tr('리스크 설정을 저장했습니다.', 'Risk settings saved.');
        await loadConfig();
        await refreshAll();
      } catch (e) {
        document.getElementById('lastMessage').textContent = tr('리스크 설정 저장 실패: ', 'Failed to save risk settings: ') + e.message;
      }
    }

    function renderSketchConfigSummary(cfg) {
      const config = cfg || {};
      const strategies = config.strategies || {};
      const enabledStrategies = Object.entries(strategies).filter(([, v]) => !(v && v.enabled === false)).map(([k]) => k);
      const exchange = config.exchange || {};
      const llm = config.llm || {};
      const ui = config.ui || {};
      const llmTest = window.__lastLlmTest || null;
      const exchangeProbe = window.__lastExchangeProbe || null;
      const mode = config.mode || '-';
      const styleKey = THEME_PRESETS[String(ui.style_preset || 'premium').trim().toLowerCase()] ? String(ui.style_preset || 'premium').trim().toLowerCase() : 'premium';
      const styleLabel = themePresetLabel(styleKey);
      const languageName = languageLabel(window.__currentLanguage || ui.language || 'ko');

      const summary = document.getElementById('sketchSettingsSummary');
      if (summary) {
        summary.innerHTML = `
          <li>${tr('모드', 'Mode')}: ${mode}</li>
          <li>${tr('활성 전략', 'Active strategies')}: ${enabledStrategies.slice(0, 6).join(', ') || '-'}</li>
          <li>${tr('거래소 타입', 'Exchange type')}: ${exchange.type || '-'}, testnet=${exchange.testnet ? t('common.on') : t('common.off')}</li>
          <li>${tr('리스크 max leverage', 'Risk max leverage')}: ${(config.risk_limits || {}).max_leverage || '-'}</li>
          <li>${tr('UI 스타일', 'UI style')}: ${styleLabel}</li>
          <li>${tr('UI 언어', 'UI language')}: ${languageName}</li>
        `;
      }

      const apiNode = document.getElementById('sketchApiDetails');
      if (apiNode) {
        const probeLine = exchangeProbe
          ? `<li>${tr('거래소 점검', 'Exchange probe')}: ${exchangeProbe.overall_passed ? t('common.pass') : t('common.check')} / critical=${exchangeProbe.critical_failures || 0}</li>`
          : `<li>${tr('거래소 점검', 'Exchange probe')}: ${tr('미실행', 'Not run')}</li>`;
        const llmTestLine = llmTest
          ? `<li>${tr('LLM 테스트', 'LLM test')}: ${llmTest.passed ? t('common.pass') : t('common.fail')} / ${llmTest.status || '-'}</li>`
          : `<li>${tr('LLM 테스트', 'LLM test')}: ${tr('미실행', 'Not run')}</li>`;
        apiNode.innerHTML = `
          <li>${tr('거래소 API Key', 'Exchange API Key')}: ${exchange.api_key ? tr('입력됨', 'Provided') : tr('미입력', 'Missing')}</li>
          <li>${tr('거래소 Secret', 'Exchange Secret')}: ${exchange.api_secret ? tr('입력됨', 'Provided') : tr('미입력', 'Missing')}</li>
          ${probeLine}
          <li>${tr('LLM 사용', 'LLM enabled')}: ${llm.enabled ? t('common.on') : t('common.off')} / ${llm.provider || '-'}</li>
          <li>${tr('LLM Key', 'LLM Key')}: ${llm.api_key ? tr('입력됨', 'Provided') : tr('미입력', 'Missing')}</li>
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
      if (runNode) runNode.textContent = `${tr('실행', 'Run')}: ${status.running ? tr('동작중', 'Running') : tr('정지', 'Stopped')}`;
      if (apiNode) apiNode.textContent = `API: ${status.exchange || '-'} / ${status.testnet ? 'testnet' : 'mainnet'}`;
      if (loopNode) loopNode.textContent = `${tr('자동', 'Auto')}: ${status.interval_seconds || '-'}${t('unit.seconds')} / cycle ${status.cycle_count || 0}`;

      const runningMeta = document.getElementById('sketchRunningMeta');
      const cycle = status.last_cycle || {};
      if (runningMeta) {
        runningMeta.innerHTML = `
          <li>${tr('선택 후보', 'Selected candidates')}: ${cycle.selected || 0}</li>
          <li>${tr('실행/거부', 'Executed / Rejected')}: ${cycle.executed || 0} / ${cycle.rejected || 0}</li>
          <li>${tr('최근 에러', 'Last error')}: ${status.last_error || tr('없음', 'None')}</li>
          <li>Live preflight: ${preflight.passed ? t('common.pass') : t('common.check')}</li>
        `;
      }

      renderSketchConfigSummary(status.config || {});
    }

    function renderSketchMonitor(rows) {
      const body = document.getElementById('sketchMonitorBody');
      if (!body) return;

      const list = (rows || []).slice(0, 8);
      if (!list.length) {
        body.innerHTML = `<tr><td colspan="5" class="muted">${tr('체결 데이터 대기 중...', 'Waiting for execution data...')}</td></tr>`;
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
        ? tr(`오류 점검: 최근 ${list.length}건 중 거부 ${rejected.length}건 (${rejected[0].reject_reason || 'unknown'})`, `Error check: ${rejected.length} rejects in recent ${list.length} runs (${rejected[0].reject_reason || 'unknown'})`)
        : tr('오류 점검: 최근 실행 정상', 'Error check: recent executions look normal');
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
        `).join('') : `<tr><td colspan="4" class="muted">${tr('로그 데이터 대기 중...', 'Waiting for log data...')}</td></tr>`;
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
        tr('시장분석', 'Market analysis'),
        tr('시그널 생성', 'Signal generation'),
        tr('리스크 게이트', 'Risk gate'),
        tr('실행/반려', 'Execution / reject'),
        tr('복기 로그', 'Review log'),
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
        ? t('common.off')
        : (liveStaging.active ? `Stage ${stagingStage || 1}` : t('common.waiting'));
      document.getElementById('overview').innerHTML = `
        <div class="metric"><b>${tr('실행 상태', 'Run status')}</b>${status.running ? statusBadge(tr('동작중', 'Running'), true) : statusBadge(tr('정지', 'Stopped'), false)}</div>
        <div class="metric"><b>${tr('모드', 'Mode')}</b>${status.mode}</div>
        <div class="metric"><b>${tr('사이클', 'Cycle')}</b>${status.cycle_count}</div>
        <div class="metric"><b>${tr('주기', 'Interval')}</b>${status.interval_seconds}${t('unit.seconds')}</div>
        <div class="metric"><b>${tr('거래소', 'Exchange')}</b>${status.exchange}</div>
        <div class="metric"><b>${tr('실거래 허용', 'Live allowed')}</b>${status.allow_live ? t('common.on') : t('common.off')}</div>
        <div class="metric"><b>${tr('테스트넷', 'Testnet')}</b>${status.testnet ? t('common.on') : t('common.off')}</div>
        <div class="metric"><b>${tr('거부 알림', 'Reject alert')}</b>${rejectAlert.enabled ? t('common.on') : t('common.off')} / ${rejectAlert.profile || 'auto'}</div>
        <div class="metric"><b>${tr('거부 알림 임계치', 'Reject alert thresholds')}</b>${resolvedWarn == null ? "-" : resolvedWarn.toFixed(1) + "%"} / ${resolvedCritical == null ? "-" : resolvedCritical.toFixed(1) + "%"}</div>
        <div class="metric"><b>${tr('최근 알림시각', 'Last alert time')}</b>${rejectAlert.last_alert_ts ? new Date(rejectAlert.last_alert_ts).toLocaleString() : t('common.none')}</div>
        <div class="metric"><b>Live Preflight</b>${preflight.passed ? `<span class="ok">${t('common.pass')}</span>` : `<span class="warn">${t('common.check')}</span>`}</div>
        <div class="metric"><b>Live Staging</b>${stagingStatus}</div>
        <div class="metric"><b>${tr('주문 캡(USDT)', 'Order cap (USDT)')}</b>${stagingCap > 0 ? stagingCap.toFixed(2) : '-'}</div>
        <div class="metric"><b>${tr('당일 실거래', 'Today live trades')}</b>${stagingTrades}${tr('회', '')} / PnL ${stagingPnl.toFixed(2)}</div>
        <div class="metric"><b>${tr('Staging 차단', 'Staging block')}</b>${liveStaging.blocked ? `<span class="bad">${t('common.block')}</span>` : `<span class="ok">${t('common.ok')}</span>`}</div>
      `;
      const tokenInput = document.getElementById('liveConfirmTokenInput');
      if (tokenInput && liveGuard.confirm_token_hint) {
        tokenInput.placeholder = `${t('placeholder.liveToken')} (${liveGuard.confirm_token_hint})`;
      }
      renderSketchTop(status);
    }

    function renderAccount(status) {
      const b = status.balance || {};
      const open = status.positions || {};
      document.getElementById('accountArea').innerHTML = `
        <div class="metric"><b>USDT</b>${numberOrText(b.USDT)}</div>
        <div class="metric"><b>Equity</b>${numberOrText(b.equity_usdt)}</div>
        <div class="metric"><b>${tr('총 포지션 Notional', 'Total position notional')}</b>${numberOrText(b.notional_exposure)}</div>
        <div class="metric"><b>${tr('포지션 수', 'Open positions')}</b>${open ? Object.keys(open).length : 0}</div>
      `;

      const entries = Object.entries(open);
      document.getElementById('positionArea').textContent = entries.length
        ? entries.map(([symbol, notional]) => `${symbol}: ${Number(notional).toFixed(2)}`).join('  ')
        : tr('현재 열린 포지션이 없습니다.', 'There are no open positions.');
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
      const lockText = lockMs > 0 ? tr(`잠금중 ${Math.max(1, Math.ceil(lockMs / 1000))}초`, `Locked ${Math.max(1, Math.ceil(lockMs / 1000))}s`) : t('common.normal');

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
        clearBtn.textContent = lockMs > 0 ? `${tr('리스크 해제', 'Clear Risk Halt')} (${lockText})` : tr('리스크 해제', 'Clear Risk Halt');
      }

      renderFlow(cycle, halted);

      document.getElementById('riskGuardArea').innerHTML = `
        <div class="metric"><b>${tr('리스크 상태', 'Risk status')}</b>${halted ? statusBadge(tr('정지', 'Stopped'), false) : statusBadge(tr('정상', 'Normal'), true)}</div>
        <div class="metric"><b>${tr('금일 손실 비율', 'Today loss ratio')}</b>${percentOrText(lossRate)}</div>
        <div class="metric"><b>${tr('연속 손실', 'Consecutive losses')}</b>${Number(account.consecutive_loss_count || 0)} / ${limits.max_consecutive_losses || 0}</div>
        <div class="metric"><b>${tr('거절 비율', 'Reject ratio')}</b>${percentOrText(rejectRate, '0.00%')} / ${percentOrText(limits.max_reject_ratio || 0)}</div>
        <div class="metric"><b>${tr('일일 손실 상한', 'Daily loss limit')}</b>${percentOrText(limits.daily_max_loss_pct || 0)}</div>
        <div class="metric"><b>${tr('사유', 'Reason')}</b><span class="muted">${reason}</span></div>
        <div class="metric"><b>${tr('해제 보안', 'Clear protection')}</b>${failCount}/${maxAttempts} ${tr('실패', 'failures')}, ${lockText}</div>
        <div class="metric"><b>${tr('확인 토큰 힌트', 'Confirm token hint')}</b><code>${tokenHint}</code></div>
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
        rowsHtml.push(`<div class="metric"><b>${tr('레짐', 'Regime')} ${r}</b>${tr('종목', 'Symbols')} ${count}</div>`);
      }
      const selectedLabel = Object.entries(selectedCounts).map(([k, v]) => `${k}: ${v}`).join(' / ') || tr('없음', 'None');
      const signalLabel = Object.entries(signalCounts).map(([k, v]) => `${k}: ${v}`).join(' / ') || tr('없음', 'None');
      rowsHtml.push(`<div class="metric"><b>${tr('선택 전략', 'Selected strategies')}</b>${selectedLabel}</div>`);
      rowsHtml.push(`<div class="metric"><b>${tr('후보 생성', 'Candidate generation')}</b>${signalLabel}</div>`);
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
      `).join('') || `<tr><td colspan="7" class="muted">${tr('현재 주기에서 선택 후보가 없습니다.', 'No candidates selected in the current cycle.')}</td></tr>`;

      const marketAnalysis = document.getElementById('sketchMarketAnalysis');
      if (marketAnalysis) {
        const marketItems = snapshots.slice(0, 8).map((item) =>
          `<li>${item.symbol || '-'} / ${item.regime || '-'} (${percentOrText(Number(item.regime_confidence || 0))})</li>`
        );
        marketAnalysis.innerHTML = marketItems.join('') || `<li>${tr('시황 분석 데이터가 없습니다.', 'No market analysis data.')}</li>`;
      }

      const marketEvidence = document.getElementById('sketchMarketEvidence');
      if (marketEvidence) {
        const evidence = snapshots.slice(0, 6).map((item) => `<li>${item.symbol || '-'}: ${item.regime_reason || '-'}</li>`);
        marketEvidence.innerHTML = evidence.join('') || `<li>${tr('근거 데이터가 없습니다.', 'No evidence data.')}</li>`;
      }

      const strategyList = document.getElementById('sketchStrategyList');
      if (strategyList) {
        const lines = selectedPlan.slice(0, 8).map((row) => `<li>${row.symbol || '-'}: ${row.strategy || '-'} / ${row.direction || '-'}</li>`);
        strategyList.innerHTML = lines.join('') || `<li>${tr('전략 후보가 없습니다.', 'No strategy candidates.')}</li>`;
      }

      const strategyEvidence = document.getElementById('sketchStrategyEvidence');
      if (strategyEvidence) {
        const lines = selectedPlan.slice(0, 8).map((row) => `<li>${row.symbol || '-'}: ${row.comment || '-'} (score ${Number(row.score || 0).toFixed(2)})</li>`);
        strategyEvidence.innerHTML = lines.join('') || `<li>${tr('전략 근거가 없습니다.', 'No strategy evidence.')}</li>`;
      }

      const botList = document.getElementById('sketchBotList');
      if (botList) {
        const activeBots = Object.entries(selectedCounts).map(([name, count]) => `${name}(${count})`);
        botList.innerHTML = (activeBots.length
          ? activeBots.map((x) => `<li>${x}</li>`).join('')
          : `<li>${tr('활성 매매 봇 데이터가 없습니다.', 'No active trading bot data.')}</li>`);
      }
    }

    async function renderRiskEvents() {
      const body = document.getElementById('riskEventBody');
      try {
        const rows = await apiGet('/api/risk/events?limit=50');
        if (!rows.length) {
          body.innerHTML = `<tr><td colspan="5" class="muted">${tr('이벤트가 없습니다.', 'No events found.')}</td></tr>`;
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
        body.innerHTML = `<tr><td colspan="5" class="muted">${tr('이벤트 조회 실패', 'Failed to load events')}</td></tr>`;
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
        summary.textContent = tr('실행 데이터가 없습니다.', 'No execution data.');
      } else {
        summary.textContent = tr(`총 거래: ${filledRows.length}건 | 누적 PnL: ${cum.toFixed(2)} USDT`, `Total trades: ${filledRows.length} | Cumulative PnL: ${cum.toFixed(2)} USDT`);
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
          <div class="metric"><b>${tr('알람 모드', 'Alert mode')}</b>${profile}</div>
          <div class="metric"><b>${tr('샘플 수', 'Samples')}</b>${total}</div>
          <div class="metric"><b>${tr('거부 총건수', 'Total rejects')}</b>${rejected}</div>
          <div class="metric"><b>${tr('거부율', 'Reject rate')}</b>${percentOrText(rejectRate, '0.00%')}</div>
          <div class="metric"><b>${tr('임계치(거부율)', 'Thresholds (reject rate)')}</b>${percentOrText(th.reject_rate_warn || 0)} / ${percentOrText(th.reject_rate_critical || 0)}</div>
          <div class="metric"><b>${tr('거부사유 임계치', 'Reason thresholds')}</b>${percentOrText(th.reject_reason_rate_warn || 0)} / ${percentOrText(th.reject_reason_rate_critical || 0)}</div>
        `;

        const alerts = (payload.alerts || []).slice(0, 8);
        if (!alerts.length) {
          alertArea.innerHTML = `<div class="reject-alert ok">${tr('현재 기준치 이상 위험 징후가 없습니다.', 'No risk signals above the current thresholds.')}</div>`;
          const errNode = document.getElementById('sketchErrorLine');
          if (errNode) errNode.textContent = tr('오류 점검: 경보 없음', 'Error check: no alert');
        } else {
          alertArea.innerHTML = alerts.map((item) => {
            const cls = item.level || 'info';
            const clsName = cls === 'critical' ? 'critical' : cls === 'warn' ? 'warn' : 'ok';
            return `<div class="reject-alert ${clsName}">${item.message || '-'}</div>`;
          }).join('');
          const errNode = document.getElementById('sketchErrorLine');
          if (errNode) errNode.textContent = tr(`오류 점검: ${alerts[0].message || '경보 발생'}`, `Error check: ${alerts[0].message || 'Alert raised'}`);
        }

        const rows = payload.reasons || [];
        if (!rows.length) {
          body.innerHTML = `<tr><td colspan="4" class="muted">${tr('거부 데이터가 아직 충분하지 않습니다.', 'Reject data is not sufficient yet.')}</td></tr>`;
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
        summaryArea.innerHTML = `<div class="metric"><b>${tr('거부사유 통계', 'Reject stats')}</b> ${tr('조회 실패', 'load failed')}</div>`;
        alertArea.innerHTML = `<div class="reject-alert critical">${tr('거부사유 통계 조회 중 오류가 발생했습니다.', 'An error occurred while loading reject statistics.')}</div>`;
        body.innerHTML = `<tr><td colspan="4" class="muted">${tr('거부사유 통계를 불러오지 못했습니다.', 'Unable to load reject statistics.')}</td></tr>`;
        const errNode = document.getElementById('sketchErrorLine');
        if (errNode) errNode.textContent = tr('오류 점검: 거부사유 통계 조회 실패', 'Error check: failed to load reject statistics');
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
          <td>${r.regime_label || '-'}</td>
          <td>${shortText(r.entry_rationale || '-', 120)}</td>
          <td>${shortText(parseMarketStateSummary(r.market_state), 140)}</td>
          <td>${r.slippage_cause || '-'}</td>
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
        area.innerHTML = `<div class="reject-alert ok">${tr('검증 알람 상태: 정상', 'Validation alert status: normal')}</div>`;
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
          document.getElementById('lastMessage').textContent = tr(`검증 알람 테스트(${lv}) 발송 시도 완료`, `Validation alert test (${lv}) send attempt completed`);
        } else {
          document.getElementById('lastMessage').textContent = tr(`검증 알람 테스트(${lv}) 실패/스킵: ${result.reason || result.status}`, `Validation alert test (${lv}) failed/skipped: ${result.reason || result.status}`);
        }
        await refreshAll();
      } catch (e) {
        document.getElementById('lastMessage').textContent = tr('검증 알람 테스트 실패: ', 'Validation alert test failed: ') + e.message;
      }
    }

    function yesNo(v) {
      return v ? t('common.pass') : t('common.fail');
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
          <div class="metric"><b>${tr('최근 검증 횟수', 'Recent validation runs')}</b>${total}</div>
          <div class="metric"><b>${tr('통과율', 'Pass rate')}</b>${percentOrText(passRate)}</div>
          <div class="metric"><b>${tr('평균 PnL', 'Average PnL')}</b>${numberOrText(avgPnl, 2)}</div>
          <div class="metric"><b>${tr('평균 승률', 'Average win rate')}</b>${percentOrText(avgWin)}</div>
          <div class="metric"><b>${tr('평균 MDD', 'Average MDD')}</b>${percentOrText(avgDd)}</div>
          <div class="metric"><b>${tr('최근 상태', 'Latest status')}</b>${yesNo(!!latest.overall_passed)}</div>
        `;

        const tbody = document.getElementById('validationHistoryBody');
        if (!rows.length) {
          tbody.innerHTML = `<tr><td colspan="7" class="muted">${tr('검증 이력이 없습니다.', 'No validation history.')}</td></tr>`;
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
        document.getElementById('validationOverview').innerHTML = `<div class="metric"><b>${tr('검증 비교', 'Validation comparison')}</b> ${tr('조회 실패', 'load failed')}</div>`;
        document.getElementById('validationHistoryBody').innerHTML = `<tr><td colspan="7" class="muted">${tr('검증 비교 데이터를 불러오지 못했습니다.', 'Unable to load validation comparison data.')}</td></tr>`;
      }
    }

    function shortText(raw, maxLen = 120) {
      const text = String(raw || '');
      if (text.length <= maxLen) return text;
      return text.slice(0, maxLen - 3) + '...';
    }

    function parseMarketStateSummary(raw) {
      if (!raw) return '-';
      try {
        const v = typeof raw === 'string' ? JSON.parse(raw) : raw;
        if (!v || typeof v !== 'object') return String(raw);
        const regime = v.regime || '-';
        const vol = Number(v.volatility || 0);
        const spread = Number(v.spread_bps || 0);
        const shock = Number(v.kalman_innovation_z || 0);
        return `regime=${regime}, vol=${vol.toFixed(4)}, spread=${spread.toFixed(1)}, shock=${shock.toFixed(2)}`;
      } catch (_e) {
        return shortText(raw, 140);
      }
    }

    function flattenLeaderboardRows(leaderboard) {
      const rows = [];
      const pushRows = (category, keyField, items) => {
        (items || []).forEach((item) => {
          rows.push({
            category,
            key: item[keyField] || '-',
            trades: Number(item.trades || 0),
            win_rate: Number(item.win_rate || 0),
            total_pnl: Number(item.total_pnl || 0),
            avg_pnl: Number(item.avg_pnl || 0),
          });
        });
      };
      pushRows('strategy', 'strategy', leaderboard.strategy || []);
      pushRows('regime', 'regime', leaderboard.regime || []);
      pushRows('symbol', 'symbol', leaderboard.symbol || []);
      return rows;
    }

    async function loadLearning() {
      const days = parseInt(document.getElementById('windowDays').value || '14', 10);
      const payload = await apiGet(`/api/learning?window_days=${days}`);
      const rows = payload.tuning || [];
      const auto = payload.auto_learning || {};
      const pending = payload.pending_proposals || [];
      const proposalStats = payload.proposal_stats || {};
      const leaderboard = payload.leaderboard || {};

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

      document.getElementById('learningProposalBody').innerHTML = pending.map((x) => `
        <tr>
          <td><input type="checkbox" class="proposal-check" value="${x.id}" /></td>
          <td>${x.id}</td>
          <td>${x.strategy || '-'}</td>
          <td>${x.action || '-'}</td>
          <td>${Number(x.current_weight || 0).toFixed(2)}</td>
          <td>${Number(x.suggested_weight || 0).toFixed(2)}</td>
          <td>${((x.confidence || 0) * 100).toFixed(1)}%</td>
          <td>${shortText(x.reason || '-', 120)}</td>
          <td>${x.status || '-'}</td>
          <td>${String(x.ts || '-').slice(0, 19)}</td>
        </tr>
      `).join('') || `<tr><td colspan="10" class="muted">${tr('대기 중인 승인 제안이 없습니다.', 'There are no pending approval proposals.')}</td></tr>`;

      const lbRows = flattenLeaderboardRows(leaderboard);
      document.getElementById('learningLeaderboardBody').innerHTML = lbRows.map((x) => `
        <tr>
          <td>${x.category}</td>
          <td>${x.key}</td>
          <td>${x.trades}</td>
          <td>${percentOrText(x.win_rate)}</td>
          <td>${numberOrText(x.total_pnl, 2)}</td>
          <td>${numberOrText(x.avg_pnl, 2)}</td>
        </tr>
      `).join('') || `<tr><td colspan="6" class="muted">${tr('리더보드 샘플이 아직 부족합니다.', 'Leaderboard sample size is still too small.')}</td></tr>`;

      document.getElementById('learningLeaderboardSummary').innerHTML = `
        <div class="metric"><b>${tr('리더보드 샘플', 'Leaderboard samples')}</b>${Number(leaderboard.sample_count || 0)}</div>
        <div class="metric"><b>${tr('전략 Top', 'Top strategies')}</b>${(leaderboard.strategy || []).length}</div>
        <div class="metric"><b>${tr('레짐 Top', 'Top regimes')}</b>${(leaderboard.regime || []).length}</div>
        <div class="metric"><b>${tr('심볼 Top', 'Top symbols')}</b>${(leaderboard.symbol || []).length}</div>
      `;

      const pendingCount = Number(proposalStats.pending || pending.length || 0);
      const applyMode = String(auto.apply_mode || 'manual_approval');
      document.getElementById('learningProposalMsg').textContent =
        tr(`대기 제안 ${pendingCount}개 | 모드=${applyMode} | 만료=${Number(auto.proposal_expiry_hours || 0)}h`, `Pending proposals ${pendingCount} | mode=${applyMode} | expiry=${Number(auto.proposal_expiry_hours || 0)}h`);

      const changeCount = rows.filter((r) => r.action !== 'hold').length;
      let learningMsg = tr(`변경 제안: ${changeCount}개`, `Change suggestions: ${changeCount}`);
      if (!rows.length) learningMsg = tr('적용 가능한 제안이 없습니다.', 'No applicable suggestions.');
      if (auto.enabled) {
        const autoStatus = ((auto.last_result || {}).status) || 'idle';
        const remain = Number(auto.remaining_cycles_to_next_apply || 0);
        learningMsg += tr(` | 자동학습: ${autoStatus} (다음까지 ${remain} cycle, 모드=${applyMode})`, ` | Auto-learning: ${autoStatus} (${remain} cycles to next apply, mode=${applyMode})`);
      } else {
        learningMsg += tr(' | 자동학습: 비활성', ' | Auto-learning: disabled');
      }
      document.getElementById('learningMsg').textContent = learningMsg;
    }

    async function applyLearning(mode) {
      const days = parseInt(document.getElementById('windowDays').value || '14', 10);
      const selected = [...document.querySelectorAll('.tune-check:checked')].map((x) => x.value);
      const body = { window_days: days };
      if (mode === 'selected') {
        if (!selected.length) {
          document.getElementById('learningMsg').textContent = tr('선택할 전략이 없습니다.', 'No strategies selected.');
          return;
        }
        body.strategy_filter = selected;
      }

      const result = await apiPost('/api/learning/apply', body);
      document.getElementById('learningMsg').textContent = tr(`튜닝 적용: ${result.applied_count}개`, `Tuning applied: ${result.applied_count}`);
      await loadLearning();
      await loadConfig();
    }

    async function reviewLearningProposals(action) {
      const selectedIds = [...document.querySelectorAll('.proposal-check:checked')]
        .map((x) => parseInt(x.value, 10))
        .filter((x) => Number.isFinite(x));
      const body = {
        action: String(action || 'approve'),
        proposal_ids: selectedIds,
        all_pending: selectedIds.length === 0,
      };
      const result = await apiPost('/api/learning/proposals/review', body);
      const verb = body.action === 'reject' ? tr('거절', 'Rejected') : tr('승인적용', 'Approved');
      const changed = Number(result.changed_count || result.applied_count || 0);
      document.getElementById('learningMsg').textContent = tr(`제안 ${verb}: ${changed}개 (${result.status || '-'})`, `Proposal ${verb}: ${changed} (${result.status || '-'})`);
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
      const anchor = document.getElementById('notifyIncludeSummary');
      if (!anchor) return;

      const fieldNode = anchor.closest ? anchor.closest('.field') : null;
      const host = (fieldNode && fieldNode.parentElement) ? fieldNode.parentElement : anchor.parentElement;
      if (!host) return;

      let wrap = document.getElementById('validationAlertControlWrap');
      if (!wrap) {
        wrap = document.createElement('div');
        wrap.className = 'field';
        wrap.id = 'validationAlertControlWrap';
        host.appendChild(wrap);
      }
      wrap.innerHTML = `
        <label><b>${tr('검증 이력 알람 임계치', 'Validation history alert thresholds')}</b></label>
        <div class="inline-check">
          <input id="validationAlertEnabled" type="checkbox" checked /> ${tr('활성화', 'Enabled')}
        </div>
        <div class="form-grid" style="margin-top:8px;">
          <div><label for="validationAlertMinSamples">${tr('최소 샘플 수', 'Minimum samples')}</label><input id="validationAlertMinSamples" type="number" min="1" value="5" /></div>
          <div><label for="validationPassWarn">${tr('통과율 경고 이하(0~1)', 'Pass rate warn below (0~1)')}</label><input id="validationPassWarn" type="number" step="0.01" min="0" max="1" value="0.6" /></div>
          <div><label for="validationPassCritical">${tr('통과율 critical 이하(0~1)', 'Pass rate critical below (0~1)')}</label><input id="validationPassCritical" type="number" step="0.01" min="0" max="1" value="0.4" /></div>
          <div><label for="validationDdWarn">${tr('MDD 경고 이상(0~1)', 'MDD warn above (0~1)')}</label><input id="validationDdWarn" type="number" step="0.01" min="0" max="1" value="0.25" /></div>
          <div><label for="validationDdCritical">${tr('MDD critical 이상(0~1)', 'MDD critical above (0~1)')}</label><input id="validationDdCritical" type="number" step="0.01" min="0" max="1" value="0.35" /></div>
        </div>
      `;
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
        document.getElementById('lastMessage').textContent = tr('알림 설정이 저장되었습니다.', 'Notification settings saved.');
        await loadConfig();
      } catch (e) {
        document.getElementById('lastMessage').textContent = tr('알림 설정 저장 실패: ', 'Failed to save notification settings: ') + e.message;
      }
    }
    async function runOnce() {
      try {
        const result = await apiPost('/api/run-once', {});
        const detail = result.auto_halt?.reason ? ` (${result.auto_halt.reason})` : '';
        document.getElementById('lastMessage').textContent = tr(`1회 실행 완료: executed=${result.executed || 0}, rejected=${result.rejected || 0}${detail}`, `Run once complete: executed=${result.executed || 0}, rejected=${result.rejected || 0}${detail}`);
        await refreshAll();
      } catch (e) {
        document.getElementById('lastMessage').textContent = tr('1회 실행 실패: ', 'Run once failed: ') + e.message;
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
          document.getElementById('lastMessage').textContent = tr(`자동 실행 차단(preflight): ${errors}`, `Auto start blocked (preflight): ${errors}`);
          await refreshAll();
          return;
        }
        if (result.status === 'reject_validation_gate') {
          const errors = ((result.validation_gate || {}).errors || []).join(' / ') || 'validation gate failed';
          document.getElementById('lastMessage').textContent = tr(`자동 실행 차단(validation): ${errors}`, `Auto start blocked (validation): ${errors}`);
          await refreshAll();
          return;
        }
        if (result.status === 'reject_live_ack') {
          document.getElementById('lastMessage').textContent = tr('자동 실행 차단: LIVE 시작 토큰 불일치', 'Auto start blocked: LIVE start token mismatch');
          await refreshAll();
          return;
        }
        document.getElementById('lastMessage').textContent = tr(`자동 실행: ${result.status}`, `Auto run: ${result.status}`);
        await refreshAll();
      } catch (e) {
        document.getElementById('lastMessage').textContent = tr('시작 실패: ', 'Start failed: ') + e.message;
      }
    }

    async function runLiveReadiness() {
      try {
        const payload = await apiGet('/api/live/readiness');
        const checks = payload.checks || [];
        const failed = checks.filter((c) => c.required && !c.passed);
        document.getElementById('lastMessage').textContent = payload.overall_passed
          ? tr('실거래 준비 점검 통과', 'Live readiness check passed')
          : tr(`실거래 준비 점검 실패(${failed.length}개)`, `Live readiness check failed (${failed.length})`);

        const boxClass = payload.overall_passed ? 'reject-alert ok' : 'reject-alert critical';
        const lines = checks.slice(0, 8).map((c) => {
          const mark = c.passed ? 'PASS' : 'FAIL';
          return `<li>[${mark}] ${c.code}: ${c.detail || '-'}</li>`;
        }).join('');
        document.getElementById('liveReadinessArea').innerHTML = `
          <div class="${boxClass}">
            <b>${tr('실거래 준비 점검 결과', 'Live readiness result')}: ${payload.overall_passed ? t('common.pass') : t('common.fail')}</b>
            <ul class="sketch-list compact" style="margin-top:6px;">${lines || `<li>${tr('점검 항목 없음', 'No checks')}</li>`}</ul>
          </div>
        `;
      } catch (e) {
        document.getElementById('lastMessage').textContent = tr('실거래 준비 점검 실패: ', 'Live readiness check failed: ') + e.message;
      }
    }

    async function saveLiveReadinessReport() {
      try {
        const customPath = window.prompt(tr('저장 경로(비우면 자동 경로):', 'Save path (leave blank for automatic path):'), '');
        const body = {};
        if (customPath && customPath.trim()) body.output_path = customPath.trim();
        const payload = await apiPost('/api/live/readiness/report', body);
        const reportPath = (payload || {}).report_path || '-';
        document.getElementById('lastMessage').textContent = tr(`실거래 점검 리포트 저장 완료: ${reportPath}`, `Live readiness report saved: ${reportPath}`);
        await runLiveReadiness();
      } catch (e) {
        document.getElementById('lastMessage').textContent = tr('실거래 점검 리포트 저장 실패: ', 'Failed to save live readiness report: ') + e.message;
      }
    }

    function renderLiveRehearsal(payload) {
      const box = document.getElementById('liveRehearsalArea');
      if (!box) return;
      if (!payload || typeof payload !== 'object') {
        box.innerHTML = '';
        return;
      }
      const readiness = payload.readiness_summary || {};
      const stages = (((payload.runbook || {}).stage_plan) || []).slice(0, 3);
      const scenarios = (payload.failure_scenarios || []).slice(0, 4);
      const stageLines = stages.map((s) =>
        `<li>Stage ${s.stage}: cap=${Number(s.max_order_usdt || 0).toFixed(2)} USDT, target=${s.trade_count_target || 0} trades</li>`
      ).join('');
      const scenarioLines = scenarios.map((x) =>
        `<li><b>${x.code}</b>: ${shortText(x.immediate_action || '-', 120)}</li>`
      ).join('');
      const pass = !!(readiness.preflight_passed && readiness.validation_gate_passed);
      const css = pass ? 'reject-alert ok' : 'reject-alert warn';
      box.innerHTML = `
        <div class="${css}">
          <b>${tr('실거래 리허설 계획', 'Live rehearsal plan')}: ${pass ? t('common.ready') : t('common.check')}</b>
          <span class="small" style="margin-left:8px;">preflight=${yesNo(!!readiness.preflight_passed)}, gate=${yesNo(!!readiness.validation_gate_passed)}, probe=${yesNo(!!readiness.exchange_probe_passed)}</span>
          <div class="small" style="margin-top:6px;">${tr('Stage Plan', 'Stage Plan')}</div>
          <ul class="sketch-list compact">${stageLines || `<li>${tr('stage plan 없음', 'No stage plan')}</li>`}</ul>
          <div class="small" style="margin-top:6px;">${tr('Failure Scenarios', 'Failure Scenarios')}</div>
          <ul class="sketch-list compact">${scenarioLines || `<li>${tr('시나리오 없음', 'No scenarios')}</li>`}</ul>
        </div>
      `;
    }

    async function runLiveRehearsal() {
      try {
        const payload = await apiGet('/api/live/rehearsal');
        renderLiveRehearsal(payload);
        const ready = (payload.readiness_summary || {});
        document.getElementById('lastMessage').textContent =
          tr(`리허설 생성 완료(preflight=${yesNo(!!ready.preflight_passed)}, gate=${yesNo(!!ready.validation_gate_passed)}, probe=${yesNo(!!ready.exchange_probe_passed)})`, `Rehearsal created (preflight=${yesNo(!!ready.preflight_passed)}, gate=${yesNo(!!ready.validation_gate_passed)}, probe=${yesNo(!!ready.exchange_probe_passed)})`);
      } catch (e) {
        document.getElementById('lastMessage').textContent = tr('실거래 리허설 생성 실패: ', 'Failed to create live rehearsal: ') + e.message;
      }
    }

    async function saveLiveRehearsalReport() {
      try {
        const customPath = window.prompt(tr('리허설 리포트 저장 경로(비우면 자동):', 'Rehearsal report save path (blank for auto):'), '');
        const body = {};
        if (customPath && customPath.trim()) body.output_path = customPath.trim();
        const payload = await apiPost('/api/live/rehearsal/report', body);
        const reportPath = (payload || {}).report_path || '-';
        renderLiveRehearsal((payload || {}).report || {});
        document.getElementById('lastMessage').textContent = tr(`리허설 리포트 저장 완료: ${reportPath}`, `Rehearsal report saved: ${reportPath}`);
      } catch (e) {
        document.getElementById('lastMessage').textContent = tr('리허설 리포트 저장 실패: ', 'Failed to save rehearsal report: ') + e.message;
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
      const symbolRows = Array.isArray(payload.symbols) ? payload.symbols.slice(0, 4) : [];
      const symbolLines = symbolRows.map((row) => {
        const verdict = row.verdict || t('common.check');
        const minOrder = row.min_order_usdt_estimate == null ? '-' : Number(row.min_order_usdt_estimate).toFixed(4);
        const precision = row.precision_verified ? 'ok' : 'check';
        return `<li>${row.symbol || '-'}: ${verdict}, minOrder=${minOrder}, precision=${precision}, reduceOnly=${yesNo(!!row.reduce_only_supported)}, posMode=${yesNo(!!row.position_mode_supported)}</li>`;
      }).join('');
      box.innerHTML = `
        <div class="${css}">
          <b>${tr('거래소 파라미터 점검', 'Exchange parameter check')}: ${payload.overall_passed ? t('common.pass') : t('common.check')}</b>
          <span class="small" style="margin-left:8px;">${tr('필수 실패', 'Required failures')} ${failedRequired.length} / critical ${payload.critical_failures || 0}</span>
          <ul class="sketch-list compact" style="margin-top:6px;">${lines || `<li>${tr('점검 항목 없음', 'No checks')}</li>`}</ul>
          ${symbolLines ? `<div class="small" style="margin-top:6px;">${tr('심볼 실증', 'Symbol verification')}</div><ul class="sketch-list compact">${symbolLines}</ul>` : ''}
          ${warnLines ? `<div class="small" style="margin-top:6px;">${tr('주요 경고', 'Key warnings')}</div><ul class="sketch-list compact">${warnLines}</ul>` : ''}
        </div>
      `;
    }

    async function runExchangeProbe() {
      try {
        const payload = await apiGet('/api/exchange/probe');
        window.__lastExchangeProbe = payload;
        renderExchangeProbe(payload);
        document.getElementById('lastMessage').textContent = payload.overall_passed
          ? tr(`거래소 파라미터 점검 PASS (critical=${payload.critical_failures || 0})`, `Exchange parameter check PASS (critical=${payload.critical_failures || 0})`)
          : tr(`거래소 파라미터 점검 CHECK (critical=${payload.critical_failures || 0})`, `Exchange parameter check CHECK (critical=${payload.critical_failures || 0})`);
        renderSketchConfigSummary((window.__loadedConfig || {}));
      } catch (e) {
        document.getElementById('lastMessage').textContent = tr('거래소 파라미터 점검 실패: ', 'Exchange parameter check failed: ') + e.message;
      }
    }

    async function saveExchangeProbeReport() {
      try {
        const customPath = window.prompt(tr('저장 경로(비우면 자동 경로):', 'Save path (leave blank for automatic path):'), '');
        const body = {};
        if (customPath && customPath.trim()) body.output_path = customPath.trim();
        const payload = await apiPost('/api/exchange/probe/report', body);
        const reportPath = (payload || {}).report_path || '-';
        const report = (payload || {}).report || {};
        window.__lastExchangeProbe = report;
        renderExchangeProbe(report);
        document.getElementById('lastMessage').textContent = tr(`거래소 점검 리포트 저장 완료: ${reportPath}`, `Exchange report saved: ${reportPath}`);
        renderSketchConfigSummary((window.__loadedConfig || {}));
      } catch (e) {
        document.getElementById('lastMessage').textContent = tr('거래소 점검 리포트 저장 실패: ', 'Failed to save exchange report: ') + e.message;
      }
    }

    function renderLlmTestResult(payload) {
      const box = document.getElementById('llmTestResult');
      if (!box) return;
      if (!payload || typeof payload !== 'object') {
        box.textContent = tr('AI 연결 테스트 결과를 표시할 수 없습니다.', 'Unable to display AI connection test results.');
        return;
      }
      const status = String(payload.status || '-');
      const provider = String(payload.provider || '-');
      const mode = String(payload.request_mode || '-');
      const model = String(payload.model || '-');
      const scored = Number(payload.scored_count || 0);
      const passText = payload.passed ? `<span class="ok">${t('common.pass')}</span>` : `<span class="warn">${t('common.check')}</span>`;
      box.innerHTML = `
        <b>${tr('AI 연결 테스트', 'AI connection test')}:</b> ${passText}<br/>
        provider=${provider}, mode=${mode}, model=${model}, status=${status}, scored=${scored}
      `;
    }

    async function testLlmConnection() {
      try {
        const payload = await apiPost('/api/llm/test', {});
        window.__lastLlmTest = payload;
        renderLlmTestResult(payload);
        document.getElementById('lastMessage').textContent = payload.passed
          ? tr(`AI 연결 테스트 PASS (${payload.status || '-'})`, `AI connection test PASS (${payload.status || '-'})`)
          : tr(`AI 연결 테스트 CHECK (${payload.status || '-'})`, `AI connection test CHECK (${payload.status || '-'})`);
        renderSketchConfigSummary((window.__loadedConfig || {}));
      } catch (e) {
        document.getElementById('lastMessage').textContent = tr('AI 연결 테스트 실패: ', 'AI connection test failed: ') + e.message;
      }
    }

    async function stopLoop() {
      try {
        const result = await apiPost('/api/stop', {});
        document.getElementById('lastMessage').textContent = tr(`자동 실행: ${result.status}`, `Auto run: ${result.status}`);
        await refreshAll();
      } catch (e) {
        document.getElementById('lastMessage').textContent = tr('중지 실패: ', 'Stop failed: ') + e.message;
      }
    }

    async function clearRiskHalt() {
      const now = Date.now();
      if (clearState.lockUntil > now) {
        const remain = Math.max(1, Math.ceil((clearState.lockUntil - now) / 1000));
        document.getElementById('lastMessage').textContent = tr(`리스크 해제 잠금중 ${remain}초 남았습니다.`, `Risk clear is locked for ${remain}s.`);
        return;
      }

      const policy = window.__riskClearPolicy || { confirmTokenHint: 'UNHALT' };
      const token = window.prompt(tr(`리스크 해제 확인 토큰을 입력하세요 (${policy.confirmTokenHint})`, `Enter the risk clear confirmation token (${policy.confirmTokenHint})`));
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
          document.getElementById('lastMessage').textContent = tr(`리스크 해제가 완료되었습니다.${detail}${evt}`, `Risk clear completed.${detail}${evt}`);
          await refreshAll();
          return;
        }

        if (clearProtection.locked || clearProtection.locked_remaining_ms > 0 || result.locked) {
          const remain = Math.max(1, Math.ceil(Number(clearProtection.locked_remaining_ms || 0) / 1000));
          document.getElementById('lastMessage').textContent = tr(`리스크 해제 실패 누적으로 잠금됩니다. ${remain}초 뒤 재시도 가능합니다.`, `Risk clear locked after repeated failures. Retry in ${remain}s.`);
        } else {
          document.getElementById('lastMessage').textContent = tr(`리스크 해제 실패 (${result.reason || '토큰 불일치'}). 시도 ${clearState.failCount}/${policy.maxFailedAttempts}`, `Risk clear failed (${result.reason || 'token mismatch'}). Attempt ${clearState.failCount}/${policy.maxFailedAttempts}`);
        }
        await refreshAll();
      } catch (e) {
        document.getElementById('lastMessage').textContent = tr('리스크 해제 실패: ', 'Risk clear failed: ') + e.message;
      }
    }

    async function loadConfig() {
      const cfg = await apiGet('/api/config');
      window.__loadedConfig = cfg;
      applyLanguage((cfg.ui || {}).language || 'ko', true);
      document.getElementById('configJson').value = JSON.stringify(cfg, null, 2);
      renderNotificationSettings(cfg);
      renderSketchConfigSummary(cfg);
      applyTheme((cfg.ui || {}).style_preset || 'premium', true);
      document.getElementById('lastMessage').textContent = tr('설정을 불러왔습니다.', 'Configuration loaded.');
    }

    async function saveConfig() {
      let payload;
      try {
        payload = JSON.parse(document.getElementById('configJson').value);
      } catch (_e) {
        document.getElementById('lastMessage').textContent = tr('설정 JSON 형식이 올바르지 않습니다.', 'Config JSON format is invalid.');
        return;
      }
      const uiPayload = buildNotificationPayload();
      payload.notifications = { ...(payload.notifications || {}), ...uiPayload.notifications };
      payload.risk_limits = { ...(payload.risk_limits || {}), ...uiPayload.risk_limits };
      payload.validation_gate = { ...(payload.validation_gate || {}), ...uiPayload.validation_gate };
      await apiPost('/api/config', payload);
      await loadConfig();
      document.getElementById('lastMessage').textContent = tr('설정이 저장되었습니다.', 'Configuration saved.');
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
        document.getElementById('lastMessage').textContent = tr('상태 조회 실패: ', 'Failed to load status: ') + e.message;
      }
    }

    window.addEventListener('load', () => {
      loadTheme();
      loadLanguage();
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

    @app.get("/api/live/rehearsal")
    def live_rehearsal() -> dict[str, Any]:
        try:
            return runtime.run_live_rehearsal()
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc))

    @app.post("/api/live/rehearsal/report")
    def save_live_rehearsal_report(payload: dict[str, Any] = Body(default_factory=dict)) -> dict[str, Any]:
        try:
            output_path = None
            if isinstance(payload, dict):
                output_path = payload.get("output_path")
            return runtime.save_live_rehearsal_report(output_path=output_path)
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

    @app.get("/api/learning/leaderboard")
    def get_learning_leaderboard(window_days: int = 14, limit: int = 10) -> dict[str, Any]:
        try:
            return runtime.get_learning_leaderboard(window_days=window_days, limit=limit)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc))

    @app.post("/api/learning/apply")
    def apply_learning(payload: dict[str, Any] = Body(default_factory=dict)) -> dict[str, Any]:
        try:
            window_days = payload.get("window_days", 14) if isinstance(payload, dict) else 14
            strategy_filter = payload.get("strategy_filter") if isinstance(payload, dict) else None
            return runtime.apply_learning(window_days=window_days, strategy_filter=strategy_filter)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc))

    @app.get("/api/learning/proposals")
    def get_learning_proposals(limit: int = 100, status: str | None = None, source: str | None = None) -> dict[str, Any]:
        try:
            return runtime.get_learning_proposals(limit=limit, status=status, source=source)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc))

    @app.post("/api/learning/proposals/review")
    def review_learning_proposals(payload: dict[str, Any] = Body(default_factory=dict)) -> dict[str, Any]:
        try:
            action = str(payload.get("action", "approve") if isinstance(payload, dict) else "approve")
            proposal_ids = payload.get("proposal_ids") if isinstance(payload, dict) else None
            all_pending = bool(payload.get("all_pending", False)) if isinstance(payload, dict) else False
            decision_note = str(payload.get("decision_note", "") if isinstance(payload, dict) else "")
            return runtime.review_learning_proposals(
                action=action,
                proposal_ids=proposal_ids if isinstance(proposal_ids, list) else None,
                all_pending=all_pending,
                decision_note=decision_note,
            )
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











