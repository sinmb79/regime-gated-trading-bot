from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import Body, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from .multi_runtime import MultiRuntimeManager


def _parse_symbols(raw: str) -> list[str]:
    return [x.strip().upper() for x in str(raw or "").split(",") if x.strip()]


def create_multi_dashboard_app(multi_config_path: str = "configs/multi_accounts.sample.json") -> FastAPI:
    multi_config_path = str(Path(multi_config_path))
    manager = MultiRuntimeManager(multi_config_path)

    app = FastAPI(title="Boss Multi Trading Dashboard", version="0.3.0")
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
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Boss Multi Trading Dashboard</title>
  <style>
    :root {
      --bg: #0b1220;
      --panel: #101b33;
      --line: #2b3f66;
      --text: #eaf1ff;
      --muted: #9eb2d8;
      --ok: #22c55e;
      --warn: #f59e0b;
      --bad: #ef4444;
      --accent: #3b82f6;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      color: var(--text);
      background: radial-gradient(circle at top, #14244a, var(--bg));
      font-family: "Segoe UI", "Apple SD Gothic Neo", Arial, sans-serif;
    }
    .wrap {
      max-width: 1700px;
      margin: 0 auto;
      padding: 10px;
      display: grid;
      gap: 10px;
    }
    .panel {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 12px;
      padding: 12px;
    }
    .topbar {
      background: linear-gradient(180deg, rgba(36,57,96,0.7), rgba(16,27,51,0.8));
      border: 1px solid var(--line);
      border-radius: 12px;
      padding: 10px;
      display: grid;
      gap: 8px;
    }
    .tabs {
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
      align-items: center;
    }
    .tab {
      border: 1px solid #4a6598;
      border-radius: 9px;
      padding: 6px 10px;
      font-size: 12px;
      background: #0e1b36;
      color: #d8e4ff;
      cursor: pointer;
      user-select: none;
      transition: all .16s ease;
    }
    .tab.active {
      border-color: #87a7df;
      background: #1f3b70;
      color: #ffffff;
      box-shadow: 0 0 0 1px rgba(135,167,223,0.18) inset;
    }
    .hidden-view {
      display: none !important;
    }
    .workspace {
      display: grid;
      gap: 10px;
      grid-template-columns: 3fr 1.15fr;
      align-items: start;
    }
    .main-col, .side-col {
      display: grid;
      gap: 10px;
    }
    .section-row {
      display: grid;
      gap: 10px;
      grid-template-columns: 180px 1fr;
      align-items: stretch;
    }
    .section-label {
      border: 1px solid #365189;
      border-radius: 10px;
      background: #0c1731;
      padding: 10px;
      font-weight: 800;
      font-size: 18px;
      line-height: 1.25;
      display: flex;
      align-items: center;
      justify-content: center;
      text-align: center;
      min-height: 120px;
    }
    .section-body {
      border: 1px solid #365189;
      border-radius: 10px;
      background: #0a1328;
      padding: 10px;
      min-height: 120px;
    }
    .source-list {
      margin: 0;
      padding-left: 18px;
      line-height: 1.6;
      font-size: 12px;
      color: #d7e4ff;
    }
    h1, h2, h3 { margin: 4px 0 10px; }
    .toolbar {
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
      align-items: center;
    }
    .btn {
      border: 0;
      border-radius: 9px;
      padding: 8px 11px;
      color: #fff;
      font-weight: 700;
      cursor: pointer;
      background: var(--accent);
      font-size: 12px;
    }
    .btn-sub { background: #334155; }
    .btn-danger { background: #b91c1c; }
    input, select, textarea {
      border: 1px solid #365189;
      background: #0a1328;
      color: var(--text);
      border-radius: 8px;
      padding: 8px;
      min-width: 80px;
      font-size: 12px;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      font-size: 12px;
    }
    th, td {
      border-bottom: 1px solid #2d4372;
      padding: 7px;
      text-align: left;
      vertical-align: top;
    }
    th { color: #c8d7f8; }
    .muted { color: var(--muted); font-size: 12px; }
    .ok { color: var(--ok); }
    .warn { color: var(--warn); }
    .bad { color: var(--bad); }
    .grid {
      display: grid;
      gap: 10px;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    }
    .metric {
      border: 1px solid #334f86;
      border-radius: 10px;
      background: #0c1731;
      padding: 9px;
    }
    .metric b {
      display: block;
      color: #c4d5f7;
      font-size: 12px;
      margin-bottom: 4px;
    }
    .small { font-size: 12px; }
    .alert {
      border-left: 4px solid var(--warn);
      background: rgba(245, 158, 11, 0.12);
      border-radius: 10px;
      padding: 8px 10px;
    }
    .code {
      white-space: pre-wrap;
      margin: 6px 0 0;
      padding: 8px;
      border-radius: 8px;
      background: #0a1328;
      border: 1px solid #2d4372;
      max-height: 320px;
      overflow: auto;
    }
    .two-col {
      display: grid;
      gap: 10px;
      grid-template-columns: 2fr 3fr;
    }
    .editor-grid {
      display: grid;
      gap: 10px;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    }
    .field {
      display: grid;
      gap: 4px;
    }
    .field label {
      font-size: 11px;
      color: var(--muted);
    }
    @media (max-width: 1200px) {
      .workspace { grid-template-columns: 1fr; }
      .section-row { grid-template-columns: 1fr; }
      .section-label { min-height: 64px; font-size: 16px; }
    }
    @media (max-width: 1080px) {
      .two-col { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <div class="wrap">
    <div class="topbar">
      <div class="tabs">
        <div class="tab">시작</div>
        <div class="tab">진행중</div>
        <div class="tab">내계정</div>
        <div class="tab">거래소 API</div>
        <div class="tab">트레이딩 로그</div>
      </div>
      <div class="toolbar">
        <button class="btn" onclick="runOnceAll()">전체 1회 실행</button>
        <button class="btn" onclick="startAll()">전체 시작</button>
        <button class="btn btn-danger" onclick="stopAll()">전체 중지</button>
        <input id="intervalInput" type="number" min="1" value="5" title="interval seconds" />
        <input id="liveTokenInput" type="text" placeholder="live token (optional)" style="min-width:170px;" />
        <input id="riskTokenInput" type="text" placeholder="risk clear token" style="min-width:170px;" />
        <input id="sampleSymbolInput" type="text" placeholder="LLM symbol (BTCUSDT)" style="min-width:170px;" />
        <input id="probeSymbolsInput" type="text" placeholder="probe symbols, comma" style="min-width:190px;" />
        <button class="btn btn-sub" onclick="refreshAll()">새로고침</button>
      </div>
      <div class="muted">상태 메시지: <span id="lastMessage">-</span></div>
    </div>

    <div class="workspace">
      <div class="main-col">
        <div class="section-row">
          <div class="section-label">시장<br/>분석</div>
          <div class="section-body">
            <div id="summary" class="grid"></div>
            <div id="accountTabPanel" class="hidden-view" style="margin-top:8px;">
              <div class="toolbar" style="margin-bottom:8px;">
                <select id="accountProfileSelect" title="account profile"></select>
                <input id="accountChartLimitInput" type="number" min="10" max="500" value="200" title="chart executions limit" />
                <button class="btn btn-sub" onclick="refreshAccountPnlChart()">P&L chart refresh</button>
              </div>
              <div class="muted" style="margin-bottom:6px;">내계정/리스크 요약</div>
              <div style="overflow:auto;">
                <table>
                  <thead>
                    <tr>
                      <th>profile</th>
                      <th>running</th>
                      <th>mode</th>
                      <th>USDT</th>
                      <th>equity</th>
                      <th>exposure</th>
                      <th>positions</th>
                      <th>risk</th>
                      <th>execution_guard</th>
                      <th>error</th>
                    </tr>
                  </thead>
                  <tbody id="accountRiskBody">
                    <tr><td colspan="10" class="muted">No account data.</td></tr>
                  </tbody>
                </table>
              </div>
              <div id="accountPnlSummary" class="grid" style="margin-top:8px;"></div>
              <div id="accountPnlChart" class="code" style="margin-top:8px;">No chart data.</div>
            </div>
          </div>
        </div>

        <div class="section-row">
          <div class="section-label">AI<br/>전략</div>
          <div class="section-body">
            <div id="rejectMetricsResult" class="alert small">No metrics yet.</div>
            <div id="exchangeTabPanel" class="hidden-view" style="margin-top:10px;">
              <div class="toolbar">
                <select id="exchangeProfileSelect" title="exchange profile"></select>
                <button class="btn btn-sub" onclick="refreshExchangeTab()">API 상태 새로고침</button>
                <button class="btn btn-sub" onclick="exchangeProbeFromTab()">거래소 점검</button>
                <button class="btn btn-sub" onclick="readinessFromTab()">Readiness 점검</button>
              </div>
              <div id="exchangeSummary" class="grid" style="margin-top:8px;"></div>
              <div id="exchangeActionResult" class="alert small" style="margin-top:8px;">No exchange action yet.</div>
            </div>
          </div>
        </div>

        <div class="section-row">
          <div class="section-label">매매<br/>봇</div>
          <div class="section-body">
            <table>
              <thead>
                <tr>
                  <th>Profile</th>
                  <th>Enabled</th>
                  <th>Running</th>
                  <th>Mode</th>
                  <th>Cycle</th>
                  <th>Risk</th>
                  <th>USDT</th>
                  <th>Error</th>
                  <th>Controls</th>
                </tr>
              </thead>
              <tbody id="profileBody">
                <tr><td colspan="9" class="muted">Loading...</td></tr>
              </tbody>
            </table>
          </div>
        </div>

        <div class="section-row">
          <div class="section-label">실시간<br/>모니터링</div>
          <div class="section-body">
            <div id="profileResult" class="alert small">No result yet.</div>
            <div id="logsTabPanel" class="hidden-view" style="margin-top:10px;">
              <div class="toolbar">
                <select id="logsProfileSelect" title="logs profile"></select>
                <input id="logsLimitInput" type="number" min="1" max="200" value="50" title="logs limit" />
                <select id="logsStatusFilter" title="status filter">
                  <option value="">status: all</option>
                  <option value="filled">filled</option>
                  <option value="partially_filled">partially_filled</option>
                  <option value="rejected">rejected</option>
                </select>
                <select id="logsPartialFilter" title="partial filter">
                  <option value="">partial: all</option>
                  <option value="true">partial only</option>
                  <option value="false">non-partial only</option>
                </select>
                <input id="logsRejectFilter" type="text" placeholder="reject reason filter (optional)" />
                <button class="btn btn-sub" onclick="refreshLogsTab()">로그 조회</button>
              </div>
              <div id="logsSummary" class="grid" style="margin-top:8px;"></div>
              <div style="overflow:auto; margin-top:8px;">
                <table>
                  <thead>
                    <tr>
                      <th>ts</th>
                      <th>symbol</th>
                      <th>side</th>
                      <th>status</th>
                      <th>size</th>
                      <th>lev</th>
                      <th>pnl</th>
                      <th>reject</th>
                      <th>attempt</th>
                      <th>partial</th>
                      <th>note</th>
                    </tr>
                  </thead>
                  <tbody id="logsBody">
                    <tr><td colspan="11" class="muted">No logs loaded.</td></tr>
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="side-col">
        <div class="panel">
          <h3>보조 참고</h3>
          <ul class="source-list">
            <li>TradingView</li>
            <li>Google News</li>
            <li>VIX Index</li>
            <li>사용자 메모</li>
          </ul>
        </div>

        <div class="panel">
          <h3>알림 임계치</h3>
          <div class="toolbar">
            <input id="rejectWarnInput" type="number" step="0.01" min="0" max="1" value="0.35" title="reject rate warn" />
            <input id="rejectCriticalInput" type="number" step="0.01" min="0" max="1" value="0.60" title="reject rate critical" />
            <input id="reasonWarnInput" type="number" step="0.01" min="0" max="1" value="0.30" title="reason rate warn" />
            <input id="reasonCriticalInput" type="number" step="0.01" min="0" max="1" value="0.50" title="reason rate critical" />
            <input id="rejectMinSamplesInput" type="number" min="1" value="20" title="reject min samples" />
            <select id="rejectProfileInput" title="reject profile">
              <option value="auto" selected>reject profile: auto</option>
              <option value="tight">reject profile: tight</option>
              <option value="normal">reject profile: normal</option>
              <option value="loose">reject profile: loose</option>
            </select>
          </div>
          <div class="toolbar" style="margin-top:8px;">
            <input id="validationMinSamplesInput" type="number" min="1" value="5" title="validation alert min samples" />
            <input id="passWarnInput" type="number" step="0.01" min="0" max="1" value="0.60" title="pass rate warn" />
            <input id="passCriticalInput" type="number" step="0.01" min="0" max="1" value="0.40" title="pass rate critical" />
            <input id="ddWarnInput" type="number" step="0.01" min="0" max="1" value="0.25" title="max drawdown warn" />
            <input id="ddCriticalInput" type="number" step="0.01" min="0" max="1" value="0.35" title="max drawdown critical" />
            <select id="validationAlertEnabledInput" title="validation alert enabled">
              <option value="true" selected>validation alert on</option>
              <option value="false">validation alert off</option>
            </select>
          </div>
          <div class="toolbar" style="margin-top:8px;">
            <input id="cooldownInput" type="number" min="0" value="900" title="notification cooldown seconds" />
            <input id="maxPerHourInput" type="number" min="0" value="0" title="notification max per hour (0=unlimited)" />
            <select id="notifyEnabledInput" title="notification enabled">
              <option value="true" selected>notification on</option>
              <option value="false">notification off</option>
            </select>
            <select id="alertLevelInput" title="alert test level">
              <option value="warn" selected>alert test warn</option>
              <option value="critical">alert test critical</option>
            </select>
          </div>
        </div>

        <div class="panel">
          <h3>학습 설정</h3>
          <div class="toolbar">
            <select id="learningEnabledInput" title="auto learning enabled">
              <option value="false" selected>auto learning off</option>
              <option value="true">auto learning on</option>
            </select>
            <select id="learningPaperOnlyInput" title="paper only">
              <option value="true" selected>paper only on</option>
              <option value="false">paper only off</option>
            </select>
            <select id="learningApplyModeInput" title="learning apply mode">
              <option value="manual_approval" selected>manual approval</option>
              <option value="auto_apply">auto apply</option>
            </select>
            <select id="learningAllowPauseInput" title="allow pause">
              <option value="false" selected>allow pause off</option>
              <option value="true">allow pause on</option>
            </select>
            <input id="learningApplyIntervalInput" type="number" min="1" value="20" title="apply interval cycles" />
            <input id="learningWindowDaysInput" type="number" min="1" value="14" title="window days" />
            <input id="learningMinTradesInput" type="number" min="1" value="8" title="min trades per strategy" />
          </div>
          <div class="toolbar" style="margin-top:8px;">
            <input id="learningMinConfidenceInput" type="number" step="0.01" min="0" max="1" value="0.62" title="min confidence" />
            <input id="learningMaxWeightStepInput" type="number" step="0.01" min="0" max="1" value="0.20" title="max weight step pct" />
            <input id="learningMaxChangesInput" type="number" min="1" value="3" title="max strategy changes per apply" />
            <input id="learningMaxAppliesInput" type="number" min="1" value="8" title="max applies per day" />
            <input id="learningMaxPendingInput" type="number" min="1" value="100" title="max pending proposals" />
            <input id="learningProposalExpiryInput" type="number" min="1" value="72" title="proposal expiry hours" />
            <input id="validationHistoryLimitInput" type="number" min="1" value="30" title="validation history limit" />
          </div>
        </div>

        <div class="panel">
          <h3>사용자 전략 편집</h3>
          <div class="toolbar">
            <input id="strategyIdInput" type="text" value="trend" title="strategy id" />
            <select id="strategyBotTypeInput" title="bot type">
              <option value="">bot type: keep current</option>
              <option value="grid">grid</option>
              <option value="trend">trend</option>
              <option value="defensive">defensive</option>
              <option value="funding_arb">funding_arb</option>
              <option value="indicator">indicator</option>
              <option value="custom">custom</option>
            </select>
            <label class="muted"><input id="strategyAdvancedToggle" type="checkbox" onchange="setStrategyJsonEditorVisible()" /> show advanced JSON editor</label>
            <button class="btn btn-sub" onclick="syncStrategyJsonFromBeginner()">Beginner -> JSON</button>
          </div>
          <div class="editor-grid" style="margin-top:8px;">
            <div class="field">
              <label>position_size_multiplier</label>
              <input id="sbPosMultInput" type="number" step="0.01" min="0" value="1.00" />
            </div>
            <div class="field">
              <label>position_size_max</label>
              <input id="sbPosMaxInput" type="number" step="0.01" min="0" value="0.12" />
            </div>
            <div class="field">
              <label>target_leverage</label>
              <input id="sbTargetLevInput" type="number" step="0.1" min="1" value="2.0" />
            </div>
            <div class="field">
              <label>leverage_max</label>
              <input id="sbLevMaxInput" type="number" step="0.1" min="1" value="4.0" />
            </div>
            <div class="field">
              <label>stop_loss_pct</label>
              <input id="sbSlInput" type="number" step="0.001" min="0" value="0.010" />
            </div>
            <div class="field">
              <label>take_profit_pct</label>
              <input id="sbTpInput" type="number" step="0.001" min="0" value="0.020" />
            </div>
            <div class="field">
              <label>range.position_size_multiplier</label>
              <input id="sbRangePosMultInput" type="number" step="0.01" min="0" value="1.10" />
            </div>
            <div class="field">
              <label>panic.position_size_multiplier</label>
              <input id="sbPanicPosMultInput" type="number" step="0.01" min="0" value="0.70" />
            </div>
          </div>
          <div id="strategyJsonEditor" class="editor-grid" style="margin-top:8px; display:none;">
            <div>
              <div class="muted">bot_profile JSON</div>
              <textarea id="strategyBotProfileJsonInput" rows="7" style="width:100%;">{
  "position_size_multiplier": 1.0,
  "position_size_max": 0.12,
  "target_leverage": 2.0
}</textarea>
            </div>
            <div>
              <div class="muted">bot_profile_by_regime JSON</div>
              <textarea id="strategyBotProfileByRegimeJsonInput" rows="7" style="width:100%;">{
  "range": { "position_size_multiplier": 1.1 },
  "panic": { "position_size_multiplier": 0.7 }
}</textarea>
            </div>
          </div>
          <div class="muted" style="margin-top:8px;">
            Valid regimes: trend_up, trend_down, range, panic, unknown
          </div>
        </div>
      </div>
    </div>
  </div>

  <script>
    const POLL_MS = 3000;
    const TAB_KEYS = ['start', 'progress', 'account', 'exchange', 'logs'];
    const VIEW_LAYOUT = {
      start: { mainIndexes: [0, 1, 2, 3], sideIndexes: [0, 1, 2, 3] },
      progress: { mainIndexes: [1, 2, 3], sideIndexes: [0, 1] },
      account: { mainIndexes: [0], sideIndexes: [] },
      exchange: { mainIndexes: [1], sideIndexes: [0, 1] },
      logs: { mainIndexes: [3], sideIndexes: [0] },
    };
    let currentView = 'start';
    let latestStatusPayload = null;

    function getMainSectionNodes() {
      return Array.from(document.querySelectorAll('.main-col .section-row'));
    }

    function getSidePanelNodes() {
      return Array.from(document.querySelectorAll('.side-col .panel'));
    }

    function getTabNodes() {
      return Array.from(document.querySelectorAll('.tabs .tab'));
    }

    function setView(viewName) {
      const key = Object.prototype.hasOwnProperty.call(VIEW_LAYOUT, viewName) ? viewName : 'start';
      currentView = key;
      const spec = VIEW_LAYOUT[key];
      const main = getMainSectionNodes();
      const side = getSidePanelNodes();
      const tabs = getTabNodes();

      main.forEach((node, idx) => node.classList.toggle('hidden-view', !spec.mainIndexes.includes(idx)));
      side.forEach((node, idx) => node.classList.toggle('hidden-view', !spec.sideIndexes.includes(idx)));
      tabs.forEach((node, idx) => node.classList.toggle('active', TAB_KEYS[idx] === key));

      const profileResultNode = document.getElementById('profileResult');
      const logsPanelNode = document.getElementById('logsTabPanel');
      const logsMode = key === 'logs';
      if (profileResultNode) profileResultNode.classList.toggle('hidden-view', logsMode);
      if (logsPanelNode) logsPanelNode.classList.toggle('hidden-view', !logsMode);
      if (logsMode) {
        refreshLogsTab().catch(() => {});
      }

      const summaryNode = document.getElementById('summary');
      const accountPanelNode = document.getElementById('accountTabPanel');
      const rejectNode = document.getElementById('rejectMetricsResult');
      const exchangePanelNode = document.getElementById('exchangeTabPanel');
      const accountMode = key === 'account';
      const exchangeMode = key === 'exchange';
      if (summaryNode) summaryNode.classList.toggle('hidden-view', accountMode);
      if (accountPanelNode) accountPanelNode.classList.toggle('hidden-view', !accountMode);
      if (rejectNode) rejectNode.classList.toggle('hidden-view', exchangeMode);
      if (exchangePanelNode) exchangePanelNode.classList.toggle('hidden-view', !exchangeMode);
      if (accountMode) {
        refreshAccountTab();
        refreshAccountPnlChart().catch(() => {});
      }
      if (exchangeMode) {
        refreshExchangeTab();
      }

      const msg = document.getElementById('lastMessage');
      if (msg) msg.textContent = `view changed: ${key}`;
    }

    function initTabs() {
      const tabs = getTabNodes();
      tabs.forEach((node, idx) => {
        const key = TAB_KEYS[idx] || 'start';
        node.setAttribute('data-view-key', key);
        node.onclick = () => setView(key);
      });
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

    function yesNo(v) { return v ? '<span class="ok">YES</span>' : '<span class="bad">NO</span>'; }
    function num(v, d=2) { return (typeof v === 'number' && Number.isFinite(v)) ? v.toFixed(d) : '-'; }
    function toFloat(id, fallback) {
      const n = parseFloat(String(document.getElementById(id).value || ''));
      return Number.isFinite(n) ? n : fallback;
    }
    function toInt(id, fallback) {
      const n = parseInt(String(document.getElementById(id).value || ''), 10);
      return Number.isFinite(n) ? n : fallback;
    }
    function toBool(id, fallback) {
      const v = String(document.getElementById(id).value || '').trim().toLowerCase();
      if (v === 'true') return true;
      if (v === 'false') return false;
      return fallback;
    }

    function escapeHtml(value) {
      return String(value ?? '')
        .replaceAll('&', '&amp;')
        .replaceAll('<', '&lt;')
        .replaceAll('>', '&gt;')
        .replaceAll('"', '&quot;')
        .replaceAll("'", '&#39;');
    }

    function parsePartialFilter(raw) {
      const v = String(raw || '').trim().toLowerCase();
      if (v === 'true' || v === '1' || v === 'yes') return 'true';
      if (v === 'false' || v === '0' || v === 'no') return 'false';
      return '';
    }

    function syncLogsProfileSelector(profileNames) {
      const select = document.getElementById('logsProfileSelect');
      if (!select) return;
      const names = Array.isArray(profileNames) ? profileNames : [];
      const current = String(select.value || '').trim();
      if (!names.length) {
        select.innerHTML = '<option value="">no profile</option>';
        return;
      }
      select.innerHTML = names.map((name) => `<option value="${escapeHtml(name)}">${escapeHtml(name)}</option>`).join('');
      if (current && names.includes(current)) {
        select.value = current;
      } else {
        select.value = names[0];
      }
    }

    function syncExchangeProfileSelector(profileNames) {
      const select = document.getElementById('exchangeProfileSelect');
      if (!select) return;
      const names = Array.isArray(profileNames) ? profileNames : [];
      const current = String(select.value || '').trim();
      if (!names.length) {
        select.innerHTML = '<option value="">no profile</option>';
        return;
      }
      select.innerHTML = names.map((name) => `<option value="${escapeHtml(name)}">${escapeHtml(name)}</option>`).join('');
      if (current && names.includes(current)) {
        select.value = current;
      } else {
        select.value = names[0];
      }
    }

    function syncAccountProfileSelector(profileNames) {
      const select = document.getElementById('accountProfileSelect');
      if (!select) return;
      const names = Array.isArray(profileNames) ? profileNames : [];
      const current = String(select.value || '').trim();
      if (!names.length) {
        select.innerHTML = '<option value="">no profile</option>';
        return;
      }
      select.innerHTML = names.map((name) => `<option value="${escapeHtml(name)}">${escapeHtml(name)}</option>`).join('');
      if (current && names.includes(current)) {
        select.value = current;
      } else {
        select.value = names[0];
      }
    }

    function refreshAccountTab(payloadArg) {
      const payload = payloadArg || latestStatusPayload;
      const body = document.getElementById('accountRiskBody');
      if (!body) return;
      if (!payload || typeof payload !== 'object') {
        body.innerHTML = '<tr><td colspan="10" class="muted">No account data.</td></tr>';
        return;
      }
      const profiles = (payload.profiles && typeof payload.profiles === 'object') ? payload.profiles : {};
      const names = Object.keys(profiles).sort();
      if (!names.length) {
        body.innerHTML = '<tr><td colspan="10" class="muted">No profiles.</td></tr>';
        return;
      }
      body.innerHTML = names.map((name) => {
        const row = profiles[name] || {};
        const st = (row.status && typeof row.status === 'object') ? row.status : {};
        const bal = (st.balance && typeof st.balance === 'object') ? st.balance : {};
        const risk = (st.risk_guard && typeof st.risk_guard === 'object') ? st.risk_guard : {};
        const guard = (st.execution_guard && typeof st.execution_guard === 'object') ? st.execution_guard : {};
        const g = (guard.global && typeof guard.global === 'object') ? guard.global : {};
        const riskText = risk.halted ? `HALT(${escapeHtml(risk.reason || '-')})` : 'OK';
        const guardText = g.blocked ? `BLOCK(${escapeHtml(g.reason || '-')})` : 'OK';
        return `
          <tr>
            <td>${escapeHtml(name)}</td>
            <td>${st.running ? 'RUN' : 'STOP'}</td>
            <td>${escapeHtml(st.mode || '-')}</td>
            <td>${Number(bal.USDT || 0).toFixed(2)}</td>
            <td>${Number(bal.equity_usdt || 0).toFixed(2)}</td>
            <td>${Number(bal.notional_exposure || 0).toFixed(2)}</td>
            <td>${escapeHtml(bal.position_count ?? 0)}</td>
            <td>${riskText}</td>
            <td>${guardText}</td>
            <td>${escapeHtml(row.error || st.last_error || '-')}</td>
          </tr>
        `;
      }).join('');
    }

    function buildDailyPnlSeries(rows) {
      const map = new Map();
      const list = Array.isArray(rows) ? rows : [];
      for (const r of list) {
        const ts = String(r.ts || '');
        const day = ts.length >= 10 ? ts.slice(0, 10) : 'unknown';
        const pnl = Number(r.realized_pnl || 0);
        if (!Number.isFinite(pnl)) continue;
        map.set(day, (map.get(day) || 0) + pnl);
      }
      return Array.from(map.entries())
        .sort((a, b) => a[0].localeCompare(b[0]))
        .map(([day, pnl]) => ({ day, pnl }));
    }

    function renderPnlSvg(series) {
      const width = 920;
      const height = 220;
      if (!series.length) {
        return '<div class="muted">No realized pnl data for chart.</div>';
      }
      let min = Number.POSITIVE_INFINITY;
      let max = Number.NEGATIVE_INFINITY;
      let sum = 0;
      for (const p of series) {
        min = Math.min(min, p.pnl);
        max = Math.max(max, p.pnl);
        sum += p.pnl;
      }
      if (!Number.isFinite(min) || !Number.isFinite(max)) {
        return '<div class="muted">Invalid chart data.</div>';
      }
      const range = Math.max(1e-9, max - min);
      const points = series.map((p, idx) => {
        const x = series.length === 1 ? 20 : 20 + (idx * (width - 40) / (series.length - 1));
        const y = 20 + ((max - p.pnl) / range) * (height - 60);
        return `${x.toFixed(2)},${y.toFixed(2)}`;
      }).join(' ');

      const zeroY = 20 + ((max - 0) / range) * (height - 60);
      const avg = sum / series.length;
      const latest = series[series.length - 1];
      const first = series[0];
      const delta = latest.pnl - first.pnl;
      const upColor = '#22c55e';
      const downColor = '#ef4444';
      const lineColor = delta >= 0 ? upColor : downColor;
      return `
        <svg width="100%" viewBox="0 0 ${width} ${height}" role="img" aria-label="daily pnl chart">
          <rect x="0" y="0" width="${width}" height="${height}" fill="#0a1328" />
          <line x1="20" y1="${zeroY.toFixed(2)}" x2="${(width - 20)}" y2="${zeroY.toFixed(2)}" stroke="#334155" stroke-dasharray="4 4" />
          <polyline points="${points}" fill="none" stroke="${lineColor}" stroke-width="2.5" />
          <text x="20" y="${height - 8}" fill="#9eb2d8" font-size="11">days: ${series.length}</text>
          <text x="170" y="${height - 8}" fill="#9eb2d8" font-size="11">avg pnl: ${avg.toFixed(4)}</text>
          <text x="350" y="${height - 8}" fill="#9eb2d8" font-size="11">latest day: ${escapeHtml(latest.day)} (${latest.pnl.toFixed(4)})</text>
        </svg>
      `;
    }

    async function refreshAccountPnlChart() {
      const profile = String((document.getElementById('accountProfileSelect') || {}).value || '').trim();
      const limit = Math.max(10, Math.min(500, toInt('accountChartLimitInput', 200)));
      const summaryNode = document.getElementById('accountPnlSummary');
      const chartNode = document.getElementById('accountPnlChart');
      if (!profile) {
        if (chartNode) chartNode.innerHTML = 'No profile selected.';
        return;
      }
      try {
        const rows = await apiGet('/api/profile/' + encodeURIComponent(profile) + '/executions?limit=' + encodeURIComponent(String(limit)));
        const list = Array.isArray(rows) ? rows : [];
        const series = buildDailyPnlSeries(list);
        const total = list.reduce((acc, r) => acc + Number(r.realized_pnl || 0), 0);
        const wins = list.filter((r) => Number(r.realized_pnl || 0) > 0).length;
        const losses = list.filter((r) => Number(r.realized_pnl || 0) < 0).length;
        const rejects = list.filter((r) => String(r.order_status || '') === 'rejected').length;

        if (summaryNode) {
          summaryNode.innerHTML = `
            <div class="metric"><b>profile</b>${escapeHtml(profile)}</div>
            <div class="metric"><b>rows</b>${list.length}</div>
            <div class="metric"><b>wins / losses</b>${wins} / ${losses}</div>
            <div class="metric"><b>rejected</b>${rejects}</div>
            <div class="metric"><b>sum realized pnl</b>${Number(total).toFixed(4)}</div>
            <div class="metric"><b>days in chart</b>${series.length}</div>
          `;
        }
        if (chartNode) {
          chartNode.innerHTML = renderPnlSvg(series);
        }
        document.getElementById('lastMessage').textContent = `${profile} account chart loaded`;
      } catch (e) {
        if (chartNode) chartNode.innerHTML = '<span class="bad">Failed to load account chart.</span>';
        document.getElementById('lastMessage').textContent = `${profile} account chart failed: ` + e.message;
      }
    }

    function refreshExchangeTab(payloadArg) {
      const payload = payloadArg || latestStatusPayload;
      const summary = document.getElementById('exchangeSummary');
      if (!summary) return;
      const select = document.getElementById('exchangeProfileSelect');
      const profile = String((select || {}).value || '').trim();

      if (!payload || typeof payload !== 'object') {
        summary.innerHTML = '<div class="metric"><b>exchange</b>no status</div>';
        return;
      }
      const profiles = (payload.profiles && typeof payload.profiles === 'object') ? payload.profiles : {};
      const names = Object.keys(profiles).sort();
      if (select && (!profile || !names.includes(profile))) {
        syncExchangeProfileSelector(names);
      }
      const selected = String((document.getElementById('exchangeProfileSelect') || {}).value || '').trim();
      const row = profiles[selected] || {};
      const st = (row.status && typeof row.status === 'object') ? row.status : {};
      const preflight = (st.live_preflight && typeof st.live_preflight === 'object') ? st.live_preflight : {};
      const gate = (st.validation_gate && typeof st.validation_gate === 'object') ? st.validation_gate : {};
      const cfg = (st.config && typeof st.config === 'object') ? st.config : {};
      const exchangeCfg = (cfg.exchange && typeof cfg.exchange === 'object') ? cfg.exchange : {};
      const exchangeName = st.exchange || '-';
      const allowLive = !!st.allow_live;
      const testnet = !!st.testnet;
      const preflightPassed = !!preflight.passed;
      const gatePassed = !!gate.passed;
      const hasApiKey = !!String(exchangeCfg.api_key || '').trim();
      const hasApiSecret = !!String(exchangeCfg.api_secret || '').trim();
      const hasApiPassphrase = !!String(exchangeCfg.api_passphrase || '').trim();
      const keyEnv = String(exchangeCfg.api_key_env || '').trim() || '-';
      const secretEnv = String(exchangeCfg.api_secret_env || '').trim() || '-';
      const passphraseEnv = String(exchangeCfg.api_passphrase_env || '').trim() || '-';

      summary.innerHTML = `
        <div class="metric"><b>profile</b>${escapeHtml(selected || '-')}</div>
        <div class="metric"><b>exchange</b>${escapeHtml(exchangeName)}</div>
        <div class="metric"><b>allow_live / testnet</b>${allowLive ? 'YES' : 'NO'} / ${testnet ? 'YES' : 'NO'}</div>
        <div class="metric"><b>api key / secret / passphrase</b>${hasApiKey ? 'SET' : 'EMPTY'} / ${hasApiSecret ? 'SET' : 'EMPTY'} / ${hasApiPassphrase ? 'SET' : 'EMPTY'}</div>
        <div class="metric"><b>api env refs</b>${escapeHtml(keyEnv)} | ${escapeHtml(secretEnv)} | ${escapeHtml(passphraseEnv)}</div>
        <div class="metric"><b>preflight</b>${preflightPassed ? 'PASS' : 'CHECK'}</div>
        <div class="metric"><b>validation gate</b>${gatePassed ? 'PASS' : 'CHECK'}</div>
        <div class="metric"><b>last error</b>${escapeHtml(row.error || st.last_error || '-')}</div>
      `;
    }

    async function exchangeProbeFromTab() {
      const profile = String((document.getElementById('exchangeProfileSelect') || {}).value || '').trim();
      if (!profile) {
        document.getElementById('lastMessage').textContent = 'exchange profile is empty';
        return;
      }
      const resultNode = document.getElementById('exchangeActionResult');
      const rawSymbols = String(document.getElementById('probeSymbolsInput').value || '').trim();
      const query = rawSymbols ? ('?symbols=' + encodeURIComponent(rawSymbols)) : '';
      try {
        const payload = await apiGet('/api/profile/' + encodeURIComponent(profile) + '/exchange/probe' + query);
        if (resultNode) {
          const checks = Array.isArray(payload.checks) ? payload.checks : [];
          const top = checks.slice(0, 8).map((c) => `<li>${escapeHtml(c.code || '-')} : ${c.passed ? 'PASS' : 'FAIL'} (${escapeHtml(c.detail || c.message || '-')})</li>`).join('');
          resultNode.innerHTML = `
            <b>${escapeHtml(profile)} exchange probe</b>
            <div class="muted">overall: ${payload.overall_passed ? 'PASS' : 'CHECK'} / critical_failures: ${Number(payload.critical_failures || 0)}</div>
            <ul class="source-list">${top || '<li>no checks</li>'}</ul>
            <div class="code">${escapeHtml(JSON.stringify(payload || {}, null, 2))}</div>
          `;
        }
        document.getElementById('lastMessage').textContent = `${profile} exchange probe loaded`;
      } catch (e) {
        document.getElementById('lastMessage').textContent = `${profile} exchange probe failed: ` + e.message;
      }
    }

    async function readinessFromTab() {
      const profile = String((document.getElementById('exchangeProfileSelect') || {}).value || '').trim();
      if (!profile) {
        document.getElementById('lastMessage').textContent = 'exchange profile is empty';
        return;
      }
      const resultNode = document.getElementById('exchangeActionResult');
      try {
        const payload = await apiGet('/api/profile/' + encodeURIComponent(profile) + '/live/readiness');
        if (resultNode) {
          resultNode.innerHTML = `<b>${escapeHtml(profile)} readiness</b><div class="code">${escapeHtml(JSON.stringify(payload || {}, null, 2))}</div>`;
        }
        document.getElementById('lastMessage').textContent = `${profile} readiness loaded`;
      } catch (e) {
        document.getElementById('lastMessage').textContent = `${profile} readiness failed: ` + e.message;
      }
    }

    function renderStatus(payload) {
      latestStatusPayload = payload;
      const rows = payload.profiles || {};
      const names = Object.keys(rows).sort();
      const activeCount = Number(payload.active_count || 0);
      const profileCount = Number(payload.profile_count || 0);
      syncLogsProfileSelector(names);
      syncExchangeProfileSelector(names);
      syncAccountProfileSelector(names);

      document.getElementById('summary').innerHTML = `
        <div class="metric"><b>Profile count</b>${profileCount}</div>
        <div class="metric"><b>Active runtimes</b>${activeCount}</div>
        <div class="metric"><b>Multi config</b>${payload.multi_config_path || '-'}</div>
        <div class="metric"><b>Updated at</b>${payload.timestamp || '-'}</div>
      `;

      if (!names.length) {
        document.getElementById('profileBody').innerHTML = '<tr><td colspan="9" class="muted">No profiles</td></tr>';
        return;
      }

      document.getElementById('profileBody').innerHTML = names.map((name) => {
        const row = rows[name] || {};
        const enabled = !!row.enabled;
        const st = row.status || {};
        const running = (typeof st === 'object') ? !!st.running : false;
        const mode = (typeof st === 'object') ? (st.mode || '-') : String(st || '-');
        const cycle = (typeof st === 'object') ? (st.cycle_count || 0) : '-';
        const bal = (typeof st === 'object') ? (st.balance || {}) : {};
        const usdt = (typeof bal === 'object') ? bal.USDT : null;
        const risk = (typeof st === 'object') ? (st.risk_guard || {}) : {};
        const halted = !!risk.halted;
        const riskText = halted ? `<span class="bad">HALT</span> ${risk.reason || '-'}` : '<span class="ok">OK</span>';
        const err = row.error || ((typeof st === 'object') ? (st.last_error || '-') : '-');
        return `
          <tr>
            <td>${name}</td>
            <td>${yesNo(enabled)}</td>
            <td>${running ? '<span class="ok">RUN</span>' : '<span class="warn">STOP</span>'}</td>
            <td>${mode}</td>
            <td>${cycle}</td>
            <td>${riskText}</td>
            <td>${num(Number(usdt || 0), 2)}</td>
            <td>${err || '-'}</td>
            <td>
              <div class="toolbar">
                <button class="btn btn-sub" onclick="runOnceProfile('${name}')">Run once</button>
                <button class="btn btn-sub" onclick="startProfile('${name}')">Start</button>
                <button class="btn btn-danger" onclick="stopProfile('${name}')">Stop</button>
                <button class="btn btn-sub" onclick="readinessProfile('${name}')">Readiness</button>
                <button class="btn btn-sub" onclick="saveReadinessProfile('${name}')">Readiness report</button>
                <button class="btn btn-sub" onclick="llmTestProfile('${name}')">LLM test</button>
                <button class="btn btn-sub" onclick="exchangeProbeProfile('${name}')">Exchange probe</button>
                <button class="btn btn-sub" onclick="saveExchangeProbeProfile('${name}')">Probe report</button>
                <button class="btn btn-sub" onclick="rejectMetricsProfile('${name}')">Reject metrics</button>
                <button class="btn btn-sub" onclick="applyAlertConfigProfile('${name}')">Apply alert config</button>
                <button class="btn btn-sub" onclick="validationAlertTestProfile('${name}')">Validation alert test</button>
                <button class="btn btn-sub" onclick="learningStatusProfile('${name}')">Learning status</button>
                <button class="btn btn-sub" onclick="validationHistoryProfile('${name}')">Validation history</button>
                <button class="btn btn-sub" onclick="applyLearningConfigProfile('${name}')">Apply learning config</button>
                <button class="btn btn-sub" onclick="loadStrategyBotProfile('${name}')">Strategy bot load</button>
                <button class="btn btn-sub" onclick="applyStrategyBotProfile('${name}')">Strategy bot apply</button>
                <button class="btn btn-danger" onclick="clearRiskProfile('${name}')">Clear risk halt</button>
              </div>
            </td>
          </tr>
        `;
      }).join('');

      if (currentView === 'account') {
        refreshAccountTab(payload);
        refreshAccountPnlChart().catch(() => {});
      }
      if (currentView === 'exchange') {
        refreshExchangeTab(payload);
      }
    }

    function showProfileResult(title, payload) {
      const node = document.getElementById('profileResult');
      if (!node) return;
      let text = '';
      try {
        text = JSON.stringify(payload || {}, null, 2);
      } catch (_e) {
        text = String(payload || '-');
      }
      node.innerHTML = `<b>${title}</b><div class="code">${text}</div>`;
    }

    function showRejectMetricsResult(title, payload) {
      const node = document.getElementById('rejectMetricsResult');
      if (!node) return;
      let text = '';
      try {
        text = JSON.stringify(payload || {}, null, 2);
      } catch (_e) {
        text = String(payload || '-');
      }
      node.innerHTML = `<b>${title}</b><div class="code">${text}</div>`;
    }

    function buildAlertConfigPayload() {
      return {
        reject_rate_warn: toFloat('rejectWarnInput', 0.35),
        reject_rate_critical: toFloat('rejectCriticalInput', 0.60),
        reject_reason_rate_warn: toFloat('reasonWarnInput', 0.30),
        reject_reason_rate_critical: toFloat('reasonCriticalInput', 0.50),
        reject_reason_min_samples: toInt('rejectMinSamplesInput', 20),
        reject_alert_profile: String(document.getElementById('rejectProfileInput').value || 'auto'),
        alert_enabled: toBool('validationAlertEnabledInput', true),
        alert_min_samples: toInt('validationMinSamplesInput', 5),
        alert_pass_rate_warn: toFloat('passWarnInput', 0.60),
        alert_pass_rate_critical: toFloat('passCriticalInput', 0.40),
        alert_max_drawdown_warn: toFloat('ddWarnInput', 0.25),
        alert_max_drawdown_critical: toFloat('ddCriticalInput', 0.35),
        enabled: toBool('notifyEnabledInput', true),
        cooldown_seconds: toInt('cooldownInput', 900),
        max_per_hour: toInt('maxPerHourInput', 0),
      };
    }

    function buildLearningConfigPayload() {
      return {
        enabled: toBool('learningEnabledInput', false),
        paper_only: toBool('learningPaperOnlyInput', true),
        apply_mode: String(document.getElementById('learningApplyModeInput').value || 'manual_approval'),
        allow_pause: toBool('learningAllowPauseInput', false),
        apply_interval_cycles: toInt('learningApplyIntervalInput', 20),
        window_days: toInt('learningWindowDaysInput', 14),
        min_trades_per_strategy: toInt('learningMinTradesInput', 8),
        min_confidence: toFloat('learningMinConfidenceInput', 0.62),
        max_weight_step_pct: toFloat('learningMaxWeightStepInput', 0.20),
        max_strategy_changes_per_apply: toInt('learningMaxChangesInput', 3),
        max_applies_per_day: toInt('learningMaxAppliesInput', 8),
        max_pending_proposals: toInt('learningMaxPendingInput', 100),
        proposal_expiry_hours: toInt('learningProposalExpiryInput', 72),
      };
    }

    function setStrategyJsonEditorVisible() {
      const toggle = document.getElementById('strategyAdvancedToggle');
      const node = document.getElementById('strategyJsonEditor');
      if (!toggle || !node) return;
      node.style.display = toggle.checked ? 'grid' : 'none';
    }

    function syncStrategyJsonFromBeginner() {
      const botProfile = {
        position_size_multiplier: toFloat('sbPosMultInput', 1.0),
        position_size_max: toFloat('sbPosMaxInput', 0.12),
        target_leverage: toFloat('sbTargetLevInput', 2.0),
        leverage_max: toFloat('sbLevMaxInput', 4.0),
        stop_loss_pct: toFloat('sbSlInput', 0.01),
        take_profit_pct: toFloat('sbTpInput', 0.02),
      };
      const byRegime = {
        range: { position_size_multiplier: toFloat('sbRangePosMultInput', 1.1) },
        panic: { position_size_multiplier: toFloat('sbPanicPosMultInput', 0.7) },
      };
      const botProfileNode = document.getElementById('strategyBotProfileJsonInput');
      const byRegimeNode = document.getElementById('strategyBotProfileByRegimeJsonInput');
      if (botProfileNode) botProfileNode.value = JSON.stringify(botProfile, null, 2);
      if (byRegimeNode) byRegimeNode.value = JSON.stringify(byRegime, null, 2);
    }

    function hydrateStrategyBeginnerFromPayload(payload) {
      const bp = (payload && typeof payload.bot_profile === 'object' && payload.bot_profile) ? payload.bot_profile : {};
      const br = (payload && typeof payload.bot_profile_by_regime === 'object' && payload.bot_profile_by_regime) ? payload.bot_profile_by_regime : {};
      const range = (br && typeof br.range === 'object' && br.range) ? br.range : {};
      const panic = (br && typeof br.panic === 'object' && br.panic) ? br.panic : {};

      const setNum = (id, value, fallback) => {
        const node = document.getElementById(id);
        if (!node) return;
        const n = Number(value);
        node.value = String(Number.isFinite(n) ? n : fallback);
      };

      setNum('sbPosMultInput', bp.position_size_multiplier, 1.0);
      setNum('sbPosMaxInput', bp.position_size_max, 0.12);
      setNum('sbTargetLevInput', bp.target_leverage, 2.0);
      setNum('sbLevMaxInput', bp.leverage_max, 4.0);
      setNum('sbSlInput', bp.stop_loss_pct, 0.01);
      setNum('sbTpInput', bp.take_profit_pct, 0.02);
      setNum('sbRangePosMultInput', range.position_size_multiplier, 1.1);
      setNum('sbPanicPosMultInput', panic.position_size_multiplier, 0.7);
    }

    function parseJsonObjectInput(id) {
      const raw = String(document.getElementById(id).value || '').trim();
      if (!raw) return {};
      const parsed = JSON.parse(raw);
      if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
        throw new Error(id + ' must be JSON object');
      }
      return parsed;
    }

    function buildStrategyBotPayload() {
      const strategyId = String(document.getElementById('strategyIdInput').value || '').trim();
      if (!strategyId) throw new Error('strategyIdInput is required');
      const botType = String(document.getElementById('strategyBotTypeInput').value || '').trim();
      const advanced = !!(document.getElementById('strategyAdvancedToggle') && document.getElementById('strategyAdvancedToggle').checked);
      if (!advanced) {
        syncStrategyJsonFromBeginner();
      }
      const body = { strategy_id: strategyId };
      if (botType) body.bot_type = botType;
      body.bot_profile = parseJsonObjectInput('strategyBotProfileJsonInput');
      body.bot_profile_by_regime = parseJsonObjectInput('strategyBotProfileByRegimeJsonInput');
      return body;
    }

    async function refreshAll() {
      try {
        const payload = await apiGet('/api/status');
        renderStatus(payload);
        if (currentView === 'logs') {
          refreshLogsTab().catch(() => {});
        }
      } catch (e) {
        document.getElementById('lastMessage').textContent = 'Status read failed: ' + e.message;
      }
    }

    async function refreshLogsTab() {
      const profile = String((document.getElementById('logsProfileSelect') || {}).value || '').trim();
      if (!profile) {
        document.getElementById('lastMessage').textContent = 'logs profile is empty';
        return;
      }

      const limitRaw = toInt('logsLimitInput', 50);
      const limit = Math.max(1, Math.min(200, limitRaw));
      const status = String((document.getElementById('logsStatusFilter') || {}).value || '').trim();
      const rejectReason = String((document.getElementById('logsRejectFilter') || {}).value || '').trim();
      const partialFilter = parsePartialFilter((document.getElementById('logsPartialFilter') || {}).value || '');

      const params = new URLSearchParams();
      params.set('limit', String(limit));
      if (status) params.set('status', status);
      if (rejectReason) params.set('reject_reason', rejectReason);
      if (partialFilter) params.set('is_partial', partialFilter);

      const summaryNode = document.getElementById('logsSummary');
      const bodyNode = document.getElementById('logsBody');
      try {
        const metricsLimit = Math.max(50, Math.min(500, limit * 2));
        const [rows, metrics] = await Promise.all([
          apiGet('/api/profile/' + encodeURIComponent(profile) + '/executions?' + params.toString()),
          apiGet('/api/profile/' + encodeURIComponent(profile) + '/reject-metrics?limit=' + encodeURIComponent(String(metricsLimit))),
        ]);

        const list = Array.isArray(rows) ? rows : [];
        const rejected = list.filter((r) => String(r.order_status || '') === 'rejected').length;
        const partial = list.filter((r) => !!r.is_partial).length;

        if (summaryNode) {
          summaryNode.innerHTML = `
            <div class="metric"><b>profile</b>${escapeHtml(profile)}</div>
            <div class="metric"><b>fetched rows</b>${list.length}</div>
            <div class="metric"><b>rejected in rows</b>${rejected}</div>
            <div class="metric"><b>partial in rows</b>${partial}</div>
            <div class="metric"><b>reject rate (recent)</b>${((Number(metrics.reject_rate || 0) * 100).toFixed(2))}%</div>
            <div class="metric"><b>recent rejected</b>${Number(metrics.rejected_executions || 0)} / ${Number(metrics.total_executions || 0)}</div>
          `;
        }

        if (bodyNode) {
          if (!list.length) {
            bodyNode.innerHTML = '<tr><td colspan="11" class="muted">No execution logs in selected filter.</td></tr>';
          } else {
            bodyNode.innerHTML = list.map((r) => `
              <tr>
                <td>${escapeHtml(r.ts || '-')}</td>
                <td>${escapeHtml(r.symbol || '-')}</td>
                <td>${escapeHtml(r.side || '-')}</td>
                <td>${escapeHtml(r.order_status || '-')}</td>
                <td>${Number(r.size_usdt || 0).toFixed(2)}</td>
                <td>${Number(r.leverage || 0).toFixed(2)}</td>
                <td>${Number(r.realized_pnl || 0).toFixed(4)}</td>
                <td>${escapeHtml(r.reject_reason || '-')}</td>
                <td>${escapeHtml(r.attempt_count ?? '-')}</td>
                <td>${r.is_partial ? 'Y' : 'N'}</td>
                <td>${escapeHtml(r.note || '-')}</td>
              </tr>
            `).join('');
          }
        }
        document.getElementById('lastMessage').textContent = `${profile} logs loaded (${list.length})`;
      } catch (e) {
        if (bodyNode) {
          bodyNode.innerHTML = '<tr><td colspan="11" class="bad">Failed to load logs.</td></tr>';
        }
        document.getElementById('lastMessage').textContent = `${profile} logs failed: ` + e.message;
      }
    }

    async function startAll() {
      const interval = parseInt(document.getElementById('intervalInput').value || '5', 10);
      const liveToken = String(document.getElementById('liveTokenInput').value || '').trim();
      try {
        await apiPost('/api/start', { interval_seconds: interval, live_confirm_token: liveToken });
        document.getElementById('lastMessage').textContent = 'Start all requested';
        await refreshAll();
      } catch (e) {
        document.getElementById('lastMessage').textContent = 'Start all failed: ' + e.message;
      }
    }

    async function stopAll() {
      try {
        await apiPost('/api/stop', {});
        document.getElementById('lastMessage').textContent = 'Stop all requested';
        await refreshAll();
      } catch (e) {
        document.getElementById('lastMessage').textContent = 'Stop all failed: ' + e.message;
      }
    }

    async function runOnceAll() {
      try {
        await apiPost('/api/run-once', {});
        document.getElementById('lastMessage').textContent = 'Run once all requested';
        await refreshAll();
      } catch (e) {
        document.getElementById('lastMessage').textContent = 'Run once all failed: ' + e.message;
      }
    }

    async function startProfile(name) {
      const interval = parseInt(document.getElementById('intervalInput').value || '5', 10);
      const liveToken = String(document.getElementById('liveTokenInput').value || '').trim();
      try {
        const payload = await apiPost('/api/profile/' + encodeURIComponent(name) + '/start', { interval_seconds: interval, live_confirm_token: liveToken });
        document.getElementById('lastMessage').textContent = `${name} start requested`;
        showProfileResult(`${name} start`, payload);
        await refreshAll();
      } catch (e) {
        document.getElementById('lastMessage').textContent = `${name} start failed: ` + e.message;
      }
    }

    async function stopProfile(name) {
      try {
        const payload = await apiPost('/api/profile/' + encodeURIComponent(name) + '/stop', {});
        document.getElementById('lastMessage').textContent = `${name} stop requested`;
        showProfileResult(`${name} stop`, payload);
        await refreshAll();
      } catch (e) {
        document.getElementById('lastMessage').textContent = `${name} stop failed: ` + e.message;
      }
    }

    async function runOnceProfile(name) {
      try {
        const payload = await apiPost('/api/profile/' + encodeURIComponent(name) + '/run-once', {});
        document.getElementById('lastMessage').textContent = `${name} run once requested`;
        showProfileResult(`${name} run once`, payload);
        await refreshAll();
      } catch (e) {
        document.getElementById('lastMessage').textContent = `${name} run once failed: ` + e.message;
      }
    }

    async function readinessProfile(name) {
      try {
        const payload = await apiGet('/api/profile/' + encodeURIComponent(name) + '/live/readiness');
        const passed = !!payload.overall_passed;
        document.getElementById('lastMessage').textContent = `${name} readiness ${passed ? 'PASS' : 'CHECK'}`;
        showProfileResult(`${name} readiness`, payload);
      } catch (e) {
        document.getElementById('lastMessage').textContent = `${name} readiness failed: ` + e.message;
      }
    }

    async function saveReadinessProfile(name) {
      try {
        const customPath = window.prompt(`${name} readiness report path (empty = auto):`, '');
        const body = {};
        if (customPath && customPath.trim()) body.output_path = customPath.trim();
        const payload = await apiPost('/api/profile/' + encodeURIComponent(name) + '/live/readiness/report', body);
        document.getElementById('lastMessage').textContent = `${name} readiness report saved`;
        showProfileResult(`${name} readiness report`, payload);
      } catch (e) {
        document.getElementById('lastMessage').textContent = `${name} readiness report failed: ` + e.message;
      }
    }

    async function clearRiskProfile(name) {
      const token = String(document.getElementById('riskTokenInput').value || '').trim();
      if (!token) {
        document.getElementById('lastMessage').textContent = 'Enter risk clear token';
        return;
      }
      try {
        const payload = await apiPost('/api/profile/' + encodeURIComponent(name) + '/risk/clear', { confirm_token: token });
        document.getElementById('lastMessage').textContent = `${name} risk clear requested`;
        showProfileResult(`${name} risk clear`, payload);
        await refreshAll();
      } catch (e) {
        document.getElementById('lastMessage').textContent = `${name} risk clear failed: ` + e.message;
      }
    }

    async function llmTestProfile(name) {
      const sampleSymbol = String(document.getElementById('sampleSymbolInput').value || '').trim() || 'BTCUSDT';
      try {
        const payload = await apiPost('/api/profile/' + encodeURIComponent(name) + '/llm/test', {
          sample_symbol: sampleSymbol,
        });
        const passed = !!payload.passed;
        document.getElementById('lastMessage').textContent = `${name} LLM test ${passed ? 'PASS' : 'CHECK'}`;
        showProfileResult(`${name} LLM test`, payload);
      } catch (e) {
        document.getElementById('lastMessage').textContent = `${name} LLM test failed: ` + e.message;
      }
    }

    async function exchangeProbeProfile(name) {
      const rawSymbols = String(document.getElementById('probeSymbolsInput').value || '').trim();
      const query = rawSymbols ? ('?symbols=' + encodeURIComponent(rawSymbols)) : '';
      try {
        const payload = await apiGet('/api/profile/' + encodeURIComponent(name) + '/exchange/probe' + query);
        const critical = Number(payload.critical_failures || 0);
        document.getElementById('lastMessage').textContent = `${name} exchange probe ${payload.overall_passed ? 'PASS' : 'CHECK'} (critical=${critical})`;
        showProfileResult(`${name} exchange probe`, payload);
      } catch (e) {
        document.getElementById('lastMessage').textContent = `${name} exchange probe failed: ` + e.message;
      }
    }

    async function saveExchangeProbeProfile(name) {
      const customPath = window.prompt(`${name} exchange probe report path (empty = auto):`, '');
      const rawSymbols = String(document.getElementById('probeSymbolsInput').value || '').trim();
      const symbols = rawSymbols ? rawSymbols.split(',').map((x) => x.trim()).filter((x) => x.length > 0) : [];
      const body = {};
      if (customPath && customPath.trim()) body.output_path = customPath.trim();
      if (symbols.length) body.symbols = symbols;
      try {
        const payload = await apiPost('/api/profile/' + encodeURIComponent(name) + '/exchange/probe/report', body);
        document.getElementById('lastMessage').textContent = `${name} exchange probe report saved`;
        showProfileResult(`${name} exchange probe report`, payload);
      } catch (e) {
        document.getElementById('lastMessage').textContent = `${name} exchange probe report failed: ` + e.message;
      }
    }

    async function rejectMetricsProfile(name) {
      try {
        const payload = await apiGet('/api/profile/' + encodeURIComponent(name) + '/reject-metrics?limit=200');
        document.getElementById('lastMessage').textContent = `${name} reject metrics loaded`;
        showRejectMetricsResult(`${name} reject metrics`, payload);
      } catch (e) {
        document.getElementById('lastMessage').textContent = `${name} reject metrics failed: ` + e.message;
      }
    }

    async function applyAlertConfigProfile(name) {
      try {
        const body = buildAlertConfigPayload();
        const payload = await apiPost('/api/profile/' + encodeURIComponent(name) + '/alert/config', body);
        document.getElementById('lastMessage').textContent = `${name} alert config applied`;
        showProfileResult(`${name} alert config`, payload);
        await refreshAll();
      } catch (e) {
        document.getElementById('lastMessage').textContent = `${name} alert config failed: ` + e.message;
      }
    }

    async function validationAlertTestProfile(name) {
      const level = String(document.getElementById('alertLevelInput').value || 'warn').trim().toLowerCase();
      try {
        const payload = await apiPost('/api/profile/' + encodeURIComponent(name) + '/alert/validation-test', { level });
        document.getElementById('lastMessage').textContent = `${name} validation alert test sent`;
        showProfileResult(`${name} validation alert test`, payload);
      } catch (e) {
        document.getElementById('lastMessage').textContent = `${name} validation alert test failed: ` + e.message;
      }
    }

    async function learningStatusProfile(name) {
      try {
        const payload = await apiGet('/api/profile/' + encodeURIComponent(name) + '/learning/status');
        document.getElementById('lastMessage').textContent = `${name} learning status loaded`;
        showProfileResult(`${name} learning status`, payload);
      } catch (e) {
        document.getElementById('lastMessage').textContent = `${name} learning status failed: ` + e.message;
      }
    }

    async function validationHistoryProfile(name) {
      const limit = toInt('validationHistoryLimitInput', 30);
      try {
        const payload = await apiGet('/api/profile/' + encodeURIComponent(name) + '/validation/history?limit=' + encodeURIComponent(String(limit)));
        document.getElementById('lastMessage').textContent = `${name} validation history loaded`;
        showProfileResult(`${name} validation history`, payload);
      } catch (e) {
        document.getElementById('lastMessage').textContent = `${name} validation history failed: ` + e.message;
      }
    }

    async function applyLearningConfigProfile(name) {
      try {
        const body = buildLearningConfigPayload();
        const payload = await apiPost('/api/profile/' + encodeURIComponent(name) + '/learning/config', body);
        document.getElementById('lastMessage').textContent = `${name} learning config applied`;
        showProfileResult(`${name} learning config`, payload);
        await refreshAll();
      } catch (e) {
        document.getElementById('lastMessage').textContent = `${name} learning config failed: ` + e.message;
      }
    }

    async function loadStrategyBotProfile(name) {
      const strategyId = String(document.getElementById('strategyIdInput').value || '').trim();
      if (!strategyId) {
        document.getElementById('lastMessage').textContent = 'Enter strategy id';
        return;
      }
      try {
        const payload = await apiGet('/api/profile/' + encodeURIComponent(name) + '/strategy-bot?strategy_id=' + encodeURIComponent(strategyId));
        document.getElementById('lastMessage').textContent = `${name} strategy bot loaded`;
        if (payload && typeof payload === 'object') {
          if (payload.bot_type) {
            document.getElementById('strategyBotTypeInput').value = String(payload.bot_type);
          }
          if (payload.bot_profile && typeof payload.bot_profile === 'object') {
            document.getElementById('strategyBotProfileJsonInput').value = JSON.stringify(payload.bot_profile, null, 2);
          }
          if (payload.bot_profile_by_regime && typeof payload.bot_profile_by_regime === 'object') {
            document.getElementById('strategyBotProfileByRegimeJsonInput').value = JSON.stringify(payload.bot_profile_by_regime, null, 2);
          }
          hydrateStrategyBeginnerFromPayload(payload);
        }
        showProfileResult(`${name} strategy bot load`, payload);
      } catch (e) {
        document.getElementById('lastMessage').textContent = `${name} strategy bot load failed: ` + e.message;
      }
    }

    async function applyStrategyBotProfile(name) {
      try {
        const body = buildStrategyBotPayload();
        const payload = await apiPost('/api/profile/' + encodeURIComponent(name) + '/strategy-bot', body);
        document.getElementById('lastMessage').textContent = `${name} strategy bot applied`;
        showProfileResult(`${name} strategy bot apply`, payload);
        await refreshAll();
      } catch (e) {
        document.getElementById('lastMessage').textContent = `${name} strategy bot apply failed: ` + e.message;
      }
    }

    window.addEventListener('load', () => {
      initTabs();
      setView(currentView);
      setStrategyJsonEditorVisible();
      syncStrategyJsonFromBeginner();
      const accountSelect = document.getElementById('accountProfileSelect');
      if (accountSelect) {
        accountSelect.addEventListener('change', () => { refreshAccountPnlChart().catch(() => {}); });
      }
      const exchangeSelect = document.getElementById('exchangeProfileSelect');
      if (exchangeSelect) {
        exchangeSelect.addEventListener('change', () => { refreshExchangeTab(); });
      }
      refreshAll();
      setInterval(refreshAll, POLL_MS);
    });
  </script>
</body>
</html>
"""

    @app.get("/api/status")
    def get_status() -> dict[str, Any]:
        return manager.get_status()

    @app.post("/api/start")
    def start_all(payload: dict[str, Any] = Body(default_factory=dict)) -> dict[str, Any]:
        interval = payload.get("interval_seconds") if isinstance(payload, dict) else None
        token = payload.get("live_confirm_token") if isinstance(payload, dict) else ""
        interval_seconds = None
        if interval is not None:
            try:
                interval_seconds = int(interval)
            except Exception as exc:
                raise HTTPException(status_code=400, detail="interval_seconds must be integer") from exc
        return manager.start_all(interval_override=interval_seconds, live_confirm_token=str(token or ""))

    @app.post("/api/stop")
    def stop_all() -> dict[str, Any]:
        return manager.stop_all()

    @app.post("/api/run-once")
    def run_once_all() -> dict[str, Any]:
        return manager.run_once_all()

    @app.post("/api/profile/{name}/start")
    def start_profile(name: str, payload: dict[str, Any] = Body(default_factory=dict)) -> dict[str, Any]:
        interval = payload.get("interval_seconds") if isinstance(payload, dict) else None
        token = payload.get("live_confirm_token") if isinstance(payload, dict) else ""
        interval_seconds = None
        if interval is not None:
            try:
                interval_seconds = int(interval)
            except Exception as exc:
                raise HTTPException(status_code=400, detail="interval_seconds must be integer") from exc
        try:
            return manager.start_profile(name=name, interval_seconds=interval_seconds, live_confirm_token=str(token or ""))
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc))

    @app.post("/api/profile/{name}/stop")
    def stop_profile(name: str) -> dict[str, Any]:
        try:
            return manager.stop_profile(name=name)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc))

    @app.post("/api/profile/{name}/run-once")
    def run_once_profile(name: str) -> dict[str, Any]:
        try:
            return manager.run_once_profile(name=name)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc))

    @app.post("/api/profile/{name}/risk/clear")
    def clear_profile_risk(name: str, payload: dict[str, Any] = Body(default_factory=dict)) -> dict[str, Any]:
        confirm_token = ""
        if isinstance(payload, dict):
            confirm_token = str(payload.get("confirm_token") or "")
        try:
            return manager.clear_profile_risk(name=name, confirm_token=confirm_token)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc))

    @app.get("/api/profile/{name}/live/readiness")
    def profile_live_readiness(name: str) -> dict[str, Any]:
        try:
            return manager.run_profile_live_readiness(name=name)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc))

    @app.post("/api/profile/{name}/live/readiness/report")
    def profile_live_readiness_report(name: str, payload: dict[str, Any] = Body(default_factory=dict)) -> dict[str, Any]:
        output_path = None
        if isinstance(payload, dict):
            output_path = payload.get("output_path")
        try:
            return manager.save_profile_live_readiness_report(name=name, output_path=output_path)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc))

    @app.post("/api/profile/{name}/llm/test")
    def profile_llm_test(name: str, payload: dict[str, Any] = Body(default_factory=dict)) -> dict[str, Any]:
        sample_symbol = "BTCUSDT"
        if isinstance(payload, dict):
            sample_symbol = str(payload.get("sample_symbol") or sample_symbol)
        try:
            return manager.test_profile_llm(name=name, sample_symbol=sample_symbol)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc))

    @app.get("/api/profile/{name}/exchange/probe")
    def profile_exchange_probe(name: str, symbols: str = "") -> dict[str, Any]:
        symbol_list = _parse_symbols(symbols)
        try:
            return manager.run_profile_exchange_probe(name=name, symbols=symbol_list or None)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc))

    @app.post("/api/profile/{name}/exchange/probe/report")
    def profile_exchange_probe_report(name: str, payload: dict[str, Any] = Body(default_factory=dict)) -> dict[str, Any]:
        output_path = None
        symbols = None
        if isinstance(payload, dict):
            output_path = payload.get("output_path")
            raw_symbols = payload.get("symbols")
            if isinstance(raw_symbols, list):
                symbols = [str(x).strip() for x in raw_symbols if str(x).strip()]
        try:
            return manager.save_profile_exchange_probe_report(name=name, output_path=output_path, symbols=symbols)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc))

    @app.get("/api/profile/{name}/reject-metrics")
    def profile_reject_metrics(name: str, limit: int = 200) -> dict[str, Any]:
        safe_limit = max(10, min(int(limit or 200), 5000))
        try:
            return manager.get_profile_reject_metrics(name=name, limit=safe_limit)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc))

    @app.get("/api/profile/{name}/executions")
    def profile_executions(
        name: str,
        limit: int = 30,
        status: str = "",
        reject_reason: str = "",
        is_partial: str = "",
    ) -> list[dict[str, Any]]:
        safe_limit = max(1, min(int(limit or 30), 200))
        partial: bool | None = None
        partial_raw = str(is_partial or "").strip().lower()
        if partial_raw in {"true", "1", "yes"}:
            partial = True
        elif partial_raw in {"false", "0", "no"}:
            partial = False
        try:
            return manager.get_profile_executions(
                name=name,
                limit=safe_limit,
                status=str(status or "").strip() or None,
                reject_reason=str(reject_reason or "").strip() or None,
                is_partial=partial,
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc))

    @app.post("/api/profile/{name}/alert/config")
    def profile_alert_config(name: str, payload: dict[str, Any] = Body(default_factory=dict)) -> dict[str, Any]:
        try:
            return manager.patch_profile_alert_config(name=name, payload=payload if isinstance(payload, dict) else {})
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc))

    @app.post("/api/profile/{name}/alert/validation-test")
    def profile_alert_validation_test(name: str, payload: dict[str, Any] = Body(default_factory=dict)) -> dict[str, Any]:
        level = "warn"
        if isinstance(payload, dict):
            level = str(payload.get("level") or "warn").strip().lower()
        try:
            return manager.test_profile_validation_alert(name=name, level=level)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc))

    @app.get("/api/profile/{name}/learning/status")
    def profile_learning_status(name: str) -> dict[str, Any]:
        try:
            return manager.get_profile_learning_status(name=name)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc))

    @app.get("/api/profile/{name}/validation/history")
    def profile_validation_history(name: str, limit: int = 30) -> dict[str, Any]:
        safe_limit = max(1, min(int(limit or 30), 2000))
        try:
            return manager.get_profile_validation_history(name=name, limit=safe_limit)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc))

    @app.post("/api/profile/{name}/learning/config")
    def profile_learning_config(name: str, payload: dict[str, Any] = Body(default_factory=dict)) -> dict[str, Any]:
        body = payload if isinstance(payload, dict) else {}
        try:
            return manager.patch_profile_auto_learning_config(name=name, payload=body)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc))

    @app.get("/api/profile/{name}/strategy-bot")
    def profile_strategy_bot_get(name: str, strategy_id: str = "") -> dict[str, Any]:
        sid = str(strategy_id or "").strip()
        try:
            return manager.get_profile_strategy_bot_config(name=name, strategy_id=sid)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc))

    @app.post("/api/profile/{name}/strategy-bot")
    def profile_strategy_bot_patch(name: str, payload: dict[str, Any] = Body(default_factory=dict)) -> dict[str, Any]:
        body = payload if isinstance(payload, dict) else {}
        sid = str(body.get("strategy_id") or "").strip()
        if not sid:
            raise HTTPException(status_code=400, detail="strategy_id is required")
        patch = {
            "bot_type": body.get("bot_type"),
            "bot_profile": body.get("bot_profile"),
            "bot_profile_by_regime": body.get("bot_profile_by_regime"),
        }
        try:
            return manager.patch_profile_strategy_bot_config(name=name, strategy_id=sid, payload=patch)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc))

    return app
