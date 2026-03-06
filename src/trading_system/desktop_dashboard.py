from __future__ import annotations

import json
from collections import deque
from datetime import datetime
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk
from typing import Any

from .runtime import TradingRuntime


def _safe(v: Any, default: str = "-") -> str:
    if v is None:
        return default
    if isinstance(v, float):
        if v == int(v):
            return f"{int(v)}"
        return f"{v:,.2f}"
    if isinstance(v, int):
        return f"{v}"
    return str(v)


def _pct(v: Any) -> str:
    if isinstance(v, (int, float)):
        return f"{v * 100:.2f}%"
    return "-"


class TradingDashboardWindow:
    def __init__(self, config_path: str) -> None:
        self.config_path = config_path
        self.runtime = TradingRuntime(config_path)

        self.root = tk.Tk()
        self.root.title("보스 AI 트레이딩 대시보드")
        self.root.geometry("1260x860")
        self.root.minsize(1020, 740)

        self.refresh_ms = 2500
        self.poll_ms = tk.IntVar(value=3)
        self.status_message = tk.StringVar(value="준비됨")
        self.is_running = tk.StringVar(value="정지")
        self.mode = tk.StringVar(value="-")
        self.interval = tk.StringVar(value="5")
        self.cycle_count = tk.StringVar(value="0")
        self.exchange = tk.StringVar(value="-")
        self.live_staging_status = tk.StringVar(value="-")
        self.risk_halt = tk.StringVar(value="-")
        self.reject_rate = tk.StringVar(value="-")
        self.reject_samples = tk.StringVar(value="-")

        self.alert_profile = tk.StringVar(value="auto")
        self.alert_warn = tk.StringVar(value="")
        self.alert_critical = tk.StringVar(value="")
        self.alert_reason_warn = tk.StringVar(value="")
        self.alert_reason_critical = tk.StringVar(value="")
        self.alert_reason_min_samples = tk.StringVar(value="")

        self.notify_enabled = tk.BooleanVar(value=False)
        self.notify_cooldown = tk.StringVar(value="900")
        self.notify_hour_limit = tk.StringVar(value="0")
        self.validation_alert_enabled = tk.BooleanVar(value=True)
        self.validation_alert_min_samples = tk.StringVar(value="5")
        self.validation_alert_pass_warn = tk.StringVar(value="0.6")
        self.validation_alert_pass_critical = tk.StringVar(value="0.4")
        self.validation_alert_dd_warn = tk.StringVar(value="0.25")
        self.validation_alert_dd_critical = tk.StringVar(value="0.35")

        self.config_json = tk.StringVar(value="")
        self.last_error = tk.StringVar(value="-")
        self.learning_status = tk.StringVar(value="")
        self.auto_learning_status = tk.StringVar(value="자동학습: -")
        self.auto_learning_enabled = tk.BooleanVar(value=False)
        self.auto_learning_paper_only = tk.BooleanVar(value=True)
        self.auto_learning_allow_pause = tk.BooleanVar(value=False)
        self.auto_learning_interval = tk.StringVar(value="20")
        self.auto_learning_window_days = tk.StringVar(value="14")
        self.auto_learning_min_trades = tk.StringVar(value="8")
        self.auto_learning_min_confidence = tk.StringVar(value="0.62")
        self.auto_learning_max_step = tk.StringVar(value="0.2")
        self.auto_learning_max_changes = tk.StringVar(value="3")
        self.auto_learning_max_daily = tk.StringVar(value="8")
        self.validation_history_status = tk.StringVar(value="검증 이력: -")
        self._validation_alert_signature = ""
        self._ui_events = deque(maxlen=120)

        self._build_layout()
        self._wire()
        self._configure_style()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self._poll_cycle()

    def run(self) -> None:
        self.root.mainloop()

    def _configure_style(self) -> None:
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("Metric.TLabel", font=("Malgun Gothic", 10))
        style.configure("Title.TLabel", font=("Malgun Gothic", 10, "bold"))

    def _build_layout(self) -> None:
        top = ttk.Frame(self.root)
        top.pack(fill="x", padx=10, pady=10)

        ctrl = ttk.LabelFrame(top, text="실행 제어")
        ctrl.pack(side="left", fill="x", expand=True)

        ttk.Button(ctrl, text="1회 실행", command=self._run_once).pack(side="left", padx=6, pady=6)
        ttk.Button(ctrl, text="자동 실행 시작", command=self._start_loop).pack(side="left", padx=6, pady=6)
        ttk.Button(ctrl, text="중지", command=self._stop_loop).pack(side="left", padx=6, pady=6)
        ttk.Button(ctrl, text="실거래 준비 점검", command=self._run_live_readiness).pack(side="left", padx=6, pady=6)
        ttk.Button(ctrl, text="점검 리포트 저장", command=self._save_live_readiness_report).pack(side="left", padx=6, pady=6)
        ttk.Button(ctrl, text="거래소 파라미터 점검", command=self._run_exchange_probe).pack(side="left", padx=6, pady=6)
        ttk.Button(ctrl, text="거래소 점검 리포트 저장", command=self._save_exchange_probe_report).pack(side="left", padx=6, pady=6)
        ttk.Button(ctrl, text="AI 연결 테스트", command=self._test_llm_connection).pack(side="left", padx=6, pady=6)
        ttk.Label(ctrl, text="실행 주기(초)").pack(side="left", padx=(12, 4))
        ttk.Entry(ctrl, width=8, textvariable=self.poll_ms).pack(side="left")
        ttk.Button(ctrl, text="초기화/새로고침", command=self._manual_refresh).pack(side="left", padx=6)
        ttk.Button(ctrl, text="리스크 해제", command=self._clear_risk).pack(side="left", padx=6)

        status = ttk.LabelFrame(top, text="현재 상태")
        status.pack(side="right", fill="x", padx=(10, 0))
        ttk.Label(status, text="상태:", style="Title.TLabel").grid(row=0, column=0, sticky="w", padx=8, pady=4)
        ttk.Label(status, textvariable=self.is_running).grid(row=0, column=1, sticky="w", padx=4, pady=4)
        ttk.Label(status, text="모드:", style="Title.TLabel").grid(row=1, column=0, sticky="w", padx=8, pady=4)
        ttk.Label(status, textvariable=self.mode).grid(row=1, column=1, sticky="w", padx=4, pady=4)
        ttk.Label(status, text="거래소:", style="Title.TLabel").grid(row=2, column=0, sticky="w", padx=8, pady=4)
        ttk.Label(status, textvariable=self.exchange).grid(row=2, column=1, sticky="w", padx=4, pady=4)
        ttk.Label(status, text="리스크:", style="Title.TLabel").grid(row=3, column=0, sticky="w", padx=8, pady=4)
        ttk.Label(status, textvariable=self.risk_halt).grid(row=3, column=1, sticky="w", padx=4, pady=4)
        ttk.Label(status, text="Live staging:", style="Title.TLabel").grid(row=4, column=0, sticky="w", padx=8, pady=4)
        ttk.Label(status, textvariable=self.live_staging_status).grid(row=4, column=1, sticky="w", padx=4, pady=4)
        ttk.Label(status, text="마지막 메시지:", style="Title.TLabel").grid(row=5, column=0, sticky="w", padx=8, pady=4)
        ttk.Label(status, textvariable=self.status_message, foreground="#6a6a6a", width=50).grid(
            row=5, column=1, sticky="w", padx=4, pady=4
        )

        for child in status.winfo_children():
            child.grid_configure(sticky="w")

        body = ttk.Frame(self.root)
        body.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        left = ttk.Frame(body)
        left.pack(side="left", fill="both", expand=True)
        right = ttk.Frame(body)
        right.pack(side="right", fill="both", expand=True)

        # Overview
        ov = ttk.LabelFrame(left, text="운영 지표")
        ov.pack(fill="x", padx=6, pady=6)
        self._add_metric_row(ov, 0, "실행 주기", self.interval)
        self._add_metric_row(ov, 1, "사이클", self.cycle_count)
        self._add_metric_row(ov, 2, "잔고(USDT)", self.last_error)
        self._add_metric_row(ov, 3, "평균 거부율", self.reject_rate)
        self._add_metric_row(ov, 4, "샘플", self.reject_samples)

        # Account & positions
        acct = ttk.LabelFrame(left, text="계정/포지션")
        acct.pack(fill="both", expand=True, padx=6, pady=6)
        self.acct_tv = ttk.Treeview(acct, columns=("항목", "값"), show="headings", height=6)
        self.acct_tv.heading("항목", text="항목")
        self.acct_tv.heading("값", text="값")
        self.acct_tv.column("항목", width=120, anchor="w")
        self.acct_tv.column("값", width=220, anchor="w")
        self.acct_tv.pack(fill="both", expand=True, padx=8, pady=8)

        pos = ttk.LabelFrame(left, text="열린 포지션")
        pos.pack(fill="both", expand=True, padx=6, pady=6)
        self.pos_tv = ttk.Treeview(
            pos,
            columns=("심볼", "명목금액"),
            show="headings",
            height=8,
        )
        self.pos_tv.heading("심볼", text="심볼")
        self.pos_tv.heading("명목금액", text="명목금액")
        self.pos_tv.column("심볼", width=120)
        self.pos_tv.column("명목금액", width=140, anchor="e")
        self.pos_tv.pack(fill="both", expand=True, padx=8, pady=8)

        # Reject panel
        rej = ttk.LabelFrame(right, text="거부사유 운영 대시보드")
        rej.pack(fill="both", expand=True, padx=6, pady=6)

        self.reject_summary_lbl = tk.StringVar(value="샘플: - / 거부율: -")
        ttk.Label(rej, textvariable=self.reject_summary_lbl).pack(anchor="w", padx=8, pady=5)

        self.reject_tv = ttk.Treeview(
            rej,
            columns=("사유", "건수", "비율", "상태"),
            show="headings",
            height=7,
        )
        self.reject_tv.heading("사유", text="사유")
        self.reject_tv.heading("건수", text="건수")
        self.reject_tv.heading("비율", text="비율")
        self.reject_tv.heading("상태", text="상태")
        self.reject_tv.column("사유", width=220, anchor="w")
        self.reject_tv.column("건수", width=70, anchor="e")
        self.reject_tv.column("비율", width=90, anchor="e")
        self.reject_tv.column("상태", width=90, anchor="center")
        self.reject_tv.pack(fill="both", expand=True, padx=8, pady=5)

        alert_box = ttk.LabelFrame(rej, text="알람 임계치 / 알림")
        alert_box.pack(fill="x", padx=8, pady=8)
        grid = ttk.Frame(alert_box)
        grid.pack(fill="x", padx=8, pady=8)
        self._alert_form(grid, 0, "프로파일", self.alert_profile)
        self._alert_form(grid, 1, "거부율 경고", self.alert_warn)
        self._alert_form(grid, 2, "거부율 critical", self.alert_critical)
        self._alert_form(grid, 3, "거부사유 경고", self.alert_reason_warn)
        self._alert_form(grid, 4, "거부사유 critical", self.alert_reason_critical)
        self._alert_form(grid, 5, "최소샘플", self.alert_reason_min_samples)
        self._alert_form(grid, 6, "알림쿨다운(초)", self.notify_cooldown)
        self._alert_form(grid, 7, "시간당발송(0=무제한)", self.notify_hour_limit)
        self._alert_form(grid, 8, "검증알람 최소샘플", self.validation_alert_min_samples)
        self._alert_form(grid, 9, "검증통과율 경고 이하", self.validation_alert_pass_warn)
        self._alert_form(grid, 10, "검증통과율 critical 이하", self.validation_alert_pass_critical)
        self._alert_form(grid, 11, "검증 MDD 경고 이상", self.validation_alert_dd_warn)
        self._alert_form(grid, 12, "검증 MDD critical 이상", self.validation_alert_dd_critical)
        ttk.Checkbutton(alert_box, text="알림 사용", variable=self.notify_enabled).pack(anchor="w", padx=8, pady=(0, 6))
        ttk.Checkbutton(alert_box, text="검증 알람 사용", variable=self.validation_alert_enabled).pack(anchor="w", padx=8, pady=(0, 6))
        ttk.Button(alert_box, text="임계치/알림 저장", command=self._save_thresholds).pack(anchor="w", padx=8, pady=(0, 8))

        # Strategy + execution
        strategy = ttk.LabelFrame(left, text="레짐 기반 추천")
        strategy.pack(fill="both", expand=True, padx=6, pady=6)
        self.strategy_tv = ttk.Treeview(
            strategy,
            columns=("종목", "레짐", "전략", "방향", "점수", "신뢰도", "이유"),
            show="headings",
            height=8,
        )
        for col in self.strategy_tv["columns"]:
            self.strategy_tv.heading(col, text=col)
        self.strategy_tv.column("종목", width=90)
        self.strategy_tv.column("레짐", width=80)
        self.strategy_tv.column("전략", width=130)
        self.strategy_tv.column("방향", width=70)
        self.strategy_tv.column("점수", width=70, anchor="e")
        self.strategy_tv.column("신뢰도", width=70, anchor="e")
        self.strategy_tv.column("이유", width=360)
        self.strategy_tv.pack(fill="both", expand=True, padx=8, pady=8)

        exec_frame = ttk.LabelFrame(right, text="실행 내역")
        exec_frame.pack(fill="both", expand=True, padx=6, pady=6)
        self.exec_tv = ttk.Treeview(
            exec_frame,
            columns=("시간", "종목", "전략", "방향", "상태", "요청", "체결", "슬리피지", "사유", "Fee", "Gross", "PnL"),
            show="headings",
            height=10,
        )
        for col in self.exec_tv["columns"]:
            self.exec_tv.heading(col, text=col)
            self.exec_tv.column(col, width=85)
        self.exec_tv.column("시간", width=150)
        self.exec_tv.column("이유", width=130)
        self.exec_tv.pack(fill="both", expand=True, padx=8, pady=8)

        log_frame = ttk.LabelFrame(right, text="운영 로그")
        log_frame.pack(fill="both", expand=True, padx=6, pady=6)
        log_wrap = ttk.Frame(log_frame)
        log_wrap.pack(fill="both", expand=True, padx=8, pady=8)
        self.log_tv = ttk.Treeview(
            log_wrap,
            columns=("시간", "레벨", "메시지"),
            show="headings",
            height=8,
        )
        self.log_tv.heading("시간", text="시간")
        self.log_tv.heading("레벨", text="레벨")
        self.log_tv.heading("메시지", text="메시지")
        self.log_tv.column("시간", width=150)
        self.log_tv.column("레벨", width=60, anchor="center")
        self.log_tv.column("메시지", width=360)
        self.log_tv.pack(side="left", fill="both", expand=True)
        log_scroll = ttk.Scrollbar(log_wrap, orient="vertical", command=self.log_tv.yview)
        log_scroll.pack(side="right", fill="y")
        self.log_tv.configure(yscrollcommand=log_scroll.set)

        # Learning & config
        learn = ttk.LabelFrame(left, text="AI 복기/튜닝")
        learn.pack(fill="both", expand=True, padx=6, pady=6)
        toolbar = ttk.Frame(learn)
        toolbar.pack(fill="x", padx=8, pady=(8, 4))
        ttk.Label(toolbar, text="분석 기간(일)").pack(side="left")
        self.learning_days = tk.StringVar(value="14")
        ttk.Entry(toolbar, width=6, textvariable=self.learning_days).pack(side="left", padx=4)
        ttk.Button(toolbar, text="분석 조회", command=self._load_learning).pack(side="left", padx=4)
        ttk.Button(toolbar, text="선택 적용", command=self._apply_learning_selected).pack(side="left", padx=4)
        ttk.Button(toolbar, text="전체 적용", command=self._apply_learning_all).pack(side="left", padx=4)
        ttk.Label(learn, textvariable=self.learning_status, foreground="#555").pack(anchor="w", padx=8)

        auto_box = ttk.LabelFrame(learn, text="자동학습 설정")
        auto_box.pack(fill="x", padx=8, pady=(4, 6))
        auto_flags = ttk.Frame(auto_box)
        auto_flags.pack(fill="x", padx=8, pady=(6, 4))
        ttk.Checkbutton(auto_flags, text="자동학습 사용", variable=self.auto_learning_enabled).pack(side="left", padx=(0, 8))
        ttk.Checkbutton(auto_flags, text="dry/paper만 허용", variable=self.auto_learning_paper_only).pack(side="left", padx=(0, 8))
        ttk.Checkbutton(auto_flags, text="pause 허용", variable=self.auto_learning_allow_pause).pack(side="left")

        auto_grid = ttk.Frame(auto_box)
        auto_grid.pack(fill="x", padx=8, pady=(0, 4))
        self._alert_form(auto_grid, 0, "적용주기(cycle)", self.auto_learning_interval)
        self._alert_form(auto_grid, 1, "학습기간(일)", self.auto_learning_window_days)
        self._alert_form(auto_grid, 2, "전략당 최소체결", self.auto_learning_min_trades)
        self._alert_form(auto_grid, 3, "최소신뢰도(0~1)", self.auto_learning_min_confidence)
        self._alert_form(auto_grid, 4, "최대가중치변경(비율)", self.auto_learning_max_step)
        self._alert_form(auto_grid, 5, "회당 최대변경전략", self.auto_learning_max_changes)
        self._alert_form(auto_grid, 6, "일일 최대적용횟수(0=무제한)", self.auto_learning_max_daily)
        ttk.Button(auto_box, text="자동학습 설정 저장", command=self._save_auto_learning).pack(anchor="w", padx=8, pady=(0, 6))
        ttk.Label(auto_box, textvariable=self.auto_learning_status, foreground="#555").pack(anchor="w", padx=8, pady=(0, 6))

        self.learn_tv = ttk.Treeview(
            learn,
            columns=("전략", "제안", "현재", "제안값", "신뢰도", "사유"),
            show="headings",
            selectmode="extended",
            height=6,
        )
        for col in self.learn_tv["columns"]:
            self.learn_tv.heading(col, text=col)
        self.learn_tv.column("전략", width=120)
        self.learn_tv.column("제안", width=90)
        self.learn_tv.column("현재", width=90, anchor="e")
        self.learn_tv.column("제안값", width=90, anchor="e")
        self.learn_tv.column("신뢰도", width=70, anchor="e")
        self.learn_tv.column("사유", width=420)
        self.learn_tv.pack(fill="both", expand=True, padx=8, pady=8)

        learn_hist = ttk.LabelFrame(left, text="자동학습 적용 이력")
        learn_hist.pack(fill="both", expand=True, padx=6, pady=6)
        self.learn_event_tv = ttk.Treeview(
            learn_hist,
            columns=("시간", "출처", "모드", "사이클", "전략", "액션", "가중치", "신뢰도", "사유"),
            show="headings",
            height=6,
        )
        for col in self.learn_event_tv["columns"]:
            self.learn_event_tv.heading(col, text=col)
        self.learn_event_tv.column("시간", width=150)
        self.learn_event_tv.column("출처", width=70, anchor="center")
        self.learn_event_tv.column("모드", width=60, anchor="center")
        self.learn_event_tv.column("사이클", width=70, anchor="e")
        self.learn_event_tv.column("전략", width=100)
        self.learn_event_tv.column("액션", width=70, anchor="center")
        self.learn_event_tv.column("가중치", width=120, anchor="e")
        self.learn_event_tv.column("신뢰도", width=70, anchor="e")
        self.learn_event_tv.column("사유", width=260)
        self.learn_event_tv.pack(fill="both", expand=True, padx=8, pady=8)

        val_hist = ttk.LabelFrame(left, text="검증 리포트 비교")
        val_hist.pack(fill="both", expand=True, padx=6, pady=6)
        ttk.Label(val_hist, textvariable=self.validation_history_status, foreground="#555").pack(anchor="w", padx=8, pady=(6, 2))
        val_test_bar = ttk.Frame(val_hist)
        val_test_bar.pack(fill="x", padx=8, pady=(0, 4))
        ttk.Button(
            val_test_bar,
            text="검증 알람 테스트(경고)",
            command=lambda: self._trigger_validation_alert_test("warn"),
        ).pack(side="left", padx=(0, 6))
        ttk.Button(
            val_test_bar,
            text="검증 알람 테스트(치명)",
            command=lambda: self._trigger_validation_alert_test("critical"),
        ).pack(side="left")
        self.validation_tv = ttk.Treeview(
            val_hist,
            columns=("시각", "전체", "Backtest", "WalkFwd", "PnL", "승률", "MDD"),
            show="headings",
            height=6,
        )
        for col in self.validation_tv["columns"]:
            self.validation_tv.heading(col, text=col)
        self.validation_tv.column("시각", width=150)
        self.validation_tv.column("전체", width=60, anchor="center")
        self.validation_tv.column("Backtest", width=75, anchor="center")
        self.validation_tv.column("WalkFwd", width=75, anchor="center")
        self.validation_tv.column("PnL", width=100, anchor="e")
        self.validation_tv.column("승률", width=70, anchor="e")
        self.validation_tv.column("MDD", width=70, anchor="e")
        self.validation_tv.pack(fill="both", expand=True, padx=8, pady=8)

        conf = ttk.LabelFrame(left, text="설정(JSON)")
        conf.pack(fill="both", expand=True, padx=6, pady=6)
        self.config_text = tk.Text(conf, height=10, font=("Consolas", 10))
        self.config_text.pack(fill="both", expand=True, padx=8, pady=8)
        btn = ttk.Frame(conf)
        btn.pack(fill="x", padx=8, pady=(0, 8))
        ttk.Button(btn, text="설정 다시 읽기", command=self._load_config).pack(side="left")
        ttk.Button(btn, text="설정 저장", command=self._save_config).pack(side="left", padx=4)

    def _add_metric_row(self, parent: ttk.LabelFrame, row: int, title: str, value: tk.StringVar) -> None:
        ttk.Label(parent, text=title).grid(row=row, column=0, sticky="w", padx=8, pady=2)
        ttk.Label(parent, textvariable=value, style="Metric.TLabel").grid(row=row, column=1, sticky="w", padx=4, pady=2)
        parent.grid_rowconfigure(row, weight=1)
        if row == 0:
            parent.grid_columnconfigure(1, weight=1)

    def _alert_form(self, parent: ttk.Frame, row: int, label: str, value: tk.StringVar) -> None:
        ttk.Label(parent, text=label, width=24).grid(row=row, column=0, sticky="w", padx=4, pady=2)
        ttk.Entry(parent, width=26, textvariable=value).grid(row=row, column=1, sticky="w", padx=4, pady=2)

    def _wire(self) -> None:
        self._manual_refresh()
        self._load_config()
        self._load_learning()

    def _append_log(self, message: str, level: str = "INFO") -> None:
        self._ui_events.appendleft((datetime.now().strftime("%Y-%m-%d %H:%M:%S"), level.upper(), str(message)))
        self._refresh_operation_log()

    def _manual_refresh(self) -> None:
        try:
            self._refresh()
            self._append_log("수동 새로고침 완료", "INFO")
            self.status_message.set("수동 새로고침 완료")
        except Exception as exc:
            self._append_log(f"수동 새로고침 실패: {exc}", "ERROR")
            self.status_message.set(f"새로고침 실패: {exc}")

    def _poll_cycle(self) -> None:
        try:
            self._refresh()
        except Exception as exc:
            self._append_log(f"자동 갱신 중 오류: {exc}", "WARN")
            self.status_message.set(f"자동 갱신 오류: {exc}")
        self.root.after(self.refresh_ms, self._poll_cycle)

    def _refresh(self) -> None:
        status = self.runtime.get_status()
        validation_alert = status.get("validation_alert", {}) or {}
        critical_or_warn = [
            item for item in (validation_alert.get("alerts", []) or [])
            if str(item.get("level", "")).lower() in {"critical", "warn"}
        ]
        signature = json.dumps(critical_or_warn, ensure_ascii=False, sort_keys=True) if critical_or_warn else ""
        if signature and signature != self._validation_alert_signature:
            is_critical = any(str(item.get("level", "")).lower() == "critical" for item in critical_or_warn)
            message = " / ".join([str(item.get("message", "")) for item in critical_or_warn[:2]]) or "검증 경보 발생"
            self._append_log(f"검증 경보: {message}", "ERROR" if is_critical else "WARN")
        self._validation_alert_signature = signature

        self.is_running.set("동작중" if status.get("running") else "정지")
        self.mode.set(str(status.get("mode", "-")))
        self.interval.set(str(status.get("interval_seconds", "-")))
        self.cycle_count.set(str(status.get("cycle_count", 0)))
        self.exchange.set(str(status.get("exchange", "-")))
        risk_guard = status.get("risk_guard", {})
        self.risk_halt.set("해제됨" if not risk_guard.get("halted") else f"중단: {risk_guard.get('reason')}")
        live_staging = status.get("live_staging", {}) or {}
        stage_text = "OFF"
        if bool(live_staging.get("enabled")):
            if bool(live_staging.get("active")):
                stage_num = int(live_staging.get("stage", 0) or 0)
                cap = float(live_staging.get("max_order_usdt", 0.0) or 0.0)
                stage_text = f"stage {stage_num} / cap {cap:.2f} USDT"
            else:
                stage_text = "대기"
        if bool(live_staging.get("blocked")):
            stage_text += " / BLOCK"
        self.live_staging_status.set(stage_text)

        balance = status.get("balance", {}) or {}
        positions = status.get("positions", {}) or {}
        self.last_error.set(f"USDT={_safe(balance.get('USDT', '-'))} / Equity={_safe(balance.get('equity_usdt', '-'))}")

        self.acct_tv.delete(*self.acct_tv.get_children())
        self.acct_tv.insert("", "end", values=("USDT", _safe(balance.get("USDT", 0))))
        self.acct_tv.insert("", "end", values=("Equity", _safe(balance.get("equity_usdt", 0))))
        self.acct_tv.insert("", "end", values=("Open Notional", _safe(balance.get("notional_exposure", 0))))
        self.acct_tv.insert("", "end", values=("포지션 수", _safe(len(positions))))

        self.pos_tv.delete(*self.pos_tv.get_children())
        for symbol, value in positions.items():
            self.pos_tv.insert("", "end", values=(symbol, _safe(value)))

        reject_metrics = self.runtime.get_reject_reason_metrics(limit=200)
        total_executions = reject_metrics.get("total_executions", 0)
        rejected = reject_metrics.get("rejected_executions", 0)
        reject_rate = float(reject_metrics.get("reject_rate", 0.0) or 0.0)
        self.reject_summary_lbl.set(f"샘플: {total_executions} / 거부: {rejected} ({_pct(reject_rate)})")
        self.reject_rate.set(_pct(reject_rate))
        self.reject_samples.set(str(total_executions))

        self.reject_tv.delete(*self.reject_tv.get_children())
        for row in reject_metrics.get("reasons", []):
            self.reject_tv.insert(
                "",
                "end",
                values=(
                    row.get("reason", "-"),
                    _safe(row.get("count", 0)),
                    _pct(row.get("ratio", 0.0)),
                    row.get("status", "ok"),
                ),
            )

        alert = status.get("reject_alert", {})
        thresholds = alert.get("thresholds", {}) or {}
        self.alert_profile.set(str(alert.get("profile", "auto")))
        self.alert_warn.set(str(thresholds.get("warn", "")))
        self.alert_critical.set(str(thresholds.get("critical", "")))
        self.alert_reason_warn.set(str(thresholds.get("reason_warn", "")))
        self.alert_reason_critical.set(str(thresholds.get("reason_critical", "")))
        self.alert_reason_min_samples.set(str(thresholds.get("min_samples", "")))
        notify = status.get("config", {}).get("notifications", {})
        self.notify_enabled.set(bool(notify.get("enabled", False)))
        self.notify_cooldown.set(str(notify.get("cooldown_seconds", 900)))
        self.notify_hour_limit.set(str(notify.get("max_per_hour", 0)))
        validation_gate_cfg = status.get("config", {}).get("validation_gate", {}) or {}
        self.validation_alert_enabled.set(bool(validation_gate_cfg.get("alert_enabled", True)))
        self.validation_alert_min_samples.set(str(validation_gate_cfg.get("alert_min_samples", 5)))
        self.validation_alert_pass_warn.set(str(validation_gate_cfg.get("alert_pass_rate_warn", 0.6)))
        self.validation_alert_pass_critical.set(str(validation_gate_cfg.get("alert_pass_rate_critical", 0.4)))
        self.validation_alert_dd_warn.set(str(validation_gate_cfg.get("alert_max_drawdown_warn", 0.25)))
        self.validation_alert_dd_critical.set(str(validation_gate_cfg.get("alert_max_drawdown_critical", 0.35)))

        auto_cfg = status.get("config", {}).get("auto_learning", {}) or {}
        self.auto_learning_enabled.set(bool(auto_cfg.get("enabled", False)))
        self.auto_learning_paper_only.set(bool(auto_cfg.get("paper_only", True)))
        self.auto_learning_allow_pause.set(bool(auto_cfg.get("allow_pause", False)))
        self.auto_learning_interval.set(str(auto_cfg.get("apply_interval_cycles", 20)))
        self.auto_learning_window_days.set(str(auto_cfg.get("window_days", 14)))
        self.auto_learning_min_trades.set(str(auto_cfg.get("min_trades_per_strategy", 8)))
        self.auto_learning_min_confidence.set(str(auto_cfg.get("min_confidence", 0.62)))
        self.auto_learning_max_step.set(str(auto_cfg.get("max_weight_step_pct", 0.2)))
        self.auto_learning_max_changes.set(str(auto_cfg.get("max_strategy_changes_per_apply", 3)))
        self.auto_learning_max_daily.set(str(auto_cfg.get("max_applies_per_day", 8)))

        auto_state = status.get("auto_learning", {}) or {}
        auto_last = auto_state.get("last_result", {}) or {}
        auto_result_status = auto_last.get("status", "idle")
        auto_remaining = auto_state.get("remaining_cycles_to_next_apply", "-")
        auto_applied_today = auto_state.get("applied_today", "-")
        self.auto_learning_status.set(
            f"자동학습: {auto_result_status} / 다음 적용까지 {auto_remaining} cycle / 금일 적용 {auto_applied_today}회"
        )

        last_cycle = status.get("last_cycle") or {}
        strategy_plan = last_cycle.get("strategy_plan", {}) or {}
        selected_plan = strategy_plan.get("selected_plan", []) or []
        self.strategy_tv.delete(*self.strategy_tv.get_children())
        for row in selected_plan:
            score = row.get("score", 0)
            confidence = row.get("confidence", 0)
            if isinstance(score, (int, float)):
                score_text = f"{score:.2f}"
            else:
                score_text = "-"
            if isinstance(confidence, (int, float)):
                confidence_text = f"{confidence * 100:.2f}"
            else:
                confidence_text = "-"
            self.strategy_tv.insert(
                "",
                "end",
                values=(
                    row.get("symbol", "-"),
                    row.get("regime", "-"),
                    row.get("strategy", "-"),
                    row.get("direction", "-"),
                    score_text,
                    confidence_text,
                    row.get("comment", "-"),
                ),
            )

        executions = self.runtime.get_executions(limit=60)
        self.exec_tv.delete(*self.exec_tv.get_children())
        for item in executions:
            requested_size = item.get("requested_size_usdt", 0)
            size_usdt = item.get("size_usdt", 0)
            slippage = item.get("slippage_bps", 0)
            fee = item.get("fee_usdt", 0)
            gross = item.get("gross_realized_pnl", 0)
            pnl = item.get("realized_pnl", 0)
            self.exec_tv.insert(
                "",
                "end",
                values=(
                    item.get("ts", "-"),
                    item.get("symbol", "-"),
                    item.get("strategy", "-"),
                    item.get("side", "-"),
                    item.get("order_status", "-"),
                    _safe(round(requested_size, 2)),
                    _safe(round(size_usdt, 2)),
                    _safe(round(slippage, 2)),
                    item.get("reject_reason", "-"),
                    _safe(round(fee, 4)),
                    _safe(round(gross, 2)),
                    _safe(round(pnl, 2)),
                ),
            )

        self._refresh_learning_events()
        self._refresh_validation_history()
        self._refresh_operation_log()

    def _refresh_operation_log(self) -> None:
        entries: list[tuple[str, str, str]] = []

        risk_events = self.runtime.get_risk_events(limit=25)
        for event in risk_events:
            action = event.get("action", "-")
            prev = event.get("previous_reason") or "-"
            curr = event.get("current_reason") or "-"
            note = (event.get("note") or "").strip()
            message = f"{action} | prev={prev} -> curr={curr}"
            if note:
                message += f" | {note}"
            entries.append((str(event.get("ts", "-")), "RISK", message))

        executions = self.runtime.get_executions(limit=20)
        for item in executions:
            status = item.get("order_status", "-")
            reason = (item.get("reject_reason") or "").strip()
            symbol = item.get("symbol", "-")
            side = item.get("side", "-")
            strategy = item.get("strategy")
            message = f"{symbol} {side} {status}"
            if strategy:
                message = f"[{strategy}] " + message
            if reason:
                message += f" | {reason}"
            entries.append((str(item.get("ts", "-")), "EXEC", message))

        learning_events = self.runtime.get_auto_learning_events(limit=15)
        for event in learning_events:
            source = str(event.get("source", "-"))
            strategy = str(event.get("strategy", "-"))
            action = str(event.get("action", "-"))
            before = event.get("weight_before")
            after = event.get("weight_after")
            confidence = event.get("confidence")
            reason = str(event.get("reason") or "").strip()
            msg = f"{source} | {strategy} {action}"
            if isinstance(before, (int, float)) and isinstance(after, (int, float)):
                msg += f" | w:{before:.3f}->{after:.3f}"
            if isinstance(confidence, (int, float)):
                msg += f" | c:{confidence * 100:.1f}%"
            if reason:
                msg += f" | {reason}"
            entries.append((str(event.get("ts", "-")), "LEARN", msg))

        for ts, level, message in self._ui_events:
            entries.append((ts, level, message))

        self.log_tv.delete(*self.log_tv.get_children())
        if not entries:
            return

        normalized: list[tuple[float, str, str, str]] = []
        for ts, level, message in entries:
            try:
                parsed = datetime.fromisoformat(ts.replace("Z", ""))
                sort_key = parsed.timestamp()
            except Exception:
                sort_key = 0.0
            normalized.append((sort_key, ts, level, message))

        for _, ts, level, message in sorted(normalized, key=lambda item: item[0], reverse=True)[:35]:
            self.log_tv.insert("", "end", values=(ts[:19], level, message))

    def _run_once(self) -> None:
        try:
            result = self.runtime.run_once()
            auto_halt = result.get("auto_halt", {})
            msg = f"1회 실행 완료 (executed={result.get('executed', 0)}, rejected={result.get('rejected', 0)})"
            if auto_halt.get("reason"):
                msg += f" / halt: {auto_halt.get('reason')}"
            self._append_log(msg, "INFO")
            self.status_message.set(msg)
            self._refresh()
        except Exception as exc:
            self._append_log(f"1회 실행 실패: {exc}", "ERROR")
            messagebox.showerror("실행 실패", str(exc))
            self.status_message.set(f"1회 실행 실패: {exc}")

    def _run_live_readiness(self) -> None:
        try:
            result = self.runtime.run_live_readiness()
            checks = result.get("checks", []) if isinstance(result, dict) else []
            failed = [x for x in checks if bool(x.get("required")) and not bool(x.get("passed"))]
            if result.get("overall_passed", False):
                msg = "실거래 준비 점검 통과"
                self._append_log(msg, "INFO")
                self.status_message.set(msg)
                messagebox.showinfo("실거래 준비 점검", msg)
            else:
                detail = " / ".join([str(x.get("detail", "")) for x in failed[:3]]) or "필수 항목 실패"
                msg = f"실거래 준비 점검 실패 ({len(failed)}개): {detail}"
                self._append_log(msg, "WARN")
                self.status_message.set(msg)
                messagebox.showwarning("실거래 준비 점검", msg)
        except Exception as exc:
            self._append_log(f"실거래 준비 점검 실패: {exc}", "ERROR")
            self.status_message.set(f"실거래 준비 점검 실패: {exc}")
            messagebox.showerror("실거래 준비 점검 실패", str(exc))

    def _save_live_readiness_report(self) -> None:
        try:
            default_path = ""
            output_path = simpledialog.askstring(
                "점검 리포트 저장",
                "저장 경로를 입력하세요. 비우면 자동 경로를 사용합니다.",
                parent=self.root,
                initialvalue=default_path,
            )
            payload_path = output_path if output_path is not None else ""
            result = self.runtime.save_live_readiness_report(output_path=payload_path)
            path = str(result.get("report_path", "-"))
            msg = f"실거래 점검 리포트 저장 완료: {path}"
            self._append_log(msg, "INFO")
            self.status_message.set(msg)
            messagebox.showinfo("점검 리포트 저장", msg)
        except Exception as exc:
            self._append_log(f"실거래 점검 리포트 저장 실패: {exc}", "ERROR")
            self.status_message.set(f"실거래 점검 리포트 저장 실패: {exc}")
            messagebox.showerror("점검 리포트 저장 실패", str(exc))

    def _run_exchange_probe(self) -> None:
        try:
            result = self.runtime.run_exchange_probe()
            critical = int(result.get("critical_failures", 0) or 0)
            msg = f"거래소 파라미터 점검 {'PASS' if result.get('overall_passed') else 'CHECK'} (critical={critical})"
            self._append_log(msg, "INFO" if result.get("overall_passed") else "WARN")
            self.status_message.set(msg)
            if result.get("overall_passed"):
                messagebox.showinfo("거래소 파라미터 점검", msg)
            else:
                messagebox.showwarning("거래소 파라미터 점검", msg)
        except Exception as exc:
            self._append_log(f"거래소 파라미터 점검 실패: {exc}", "ERROR")
            self.status_message.set(f"거래소 파라미터 점검 실패: {exc}")
            messagebox.showerror("거래소 파라미터 점검 실패", str(exc))

    def _save_exchange_probe_report(self) -> None:
        try:
            default_path = ""
            output_path = simpledialog.askstring(
                "거래소 점검 리포트 저장",
                "저장 경로를 입력하세요. 비우면 자동 경로를 사용합니다.",
                parent=self.root,
                initialvalue=default_path,
            )
            payload_path = output_path if output_path is not None else ""
            result = self.runtime.save_exchange_probe_report(output_path=payload_path)
            path = str(result.get("report_path", "-"))
            msg = f"거래소 점검 리포트 저장 완료: {path}"
            self._append_log(msg, "INFO")
            self.status_message.set(msg)
            messagebox.showinfo("거래소 점검 리포트 저장", msg)
        except Exception as exc:
            self._append_log(f"거래소 점검 리포트 저장 실패: {exc}", "ERROR")
            self.status_message.set(f"거래소 점검 리포트 저장 실패: {exc}")
            messagebox.showerror("거래소 점검 리포트 저장 실패", str(exc))

    def _test_llm_connection(self) -> None:
        try:
            result = self.runtime.test_llm_connection()
            status = str(result.get("status", "-"))
            provider = str(result.get("provider", "-"))
            passed = bool(result.get("passed", False))
            scored = int(result.get("scored_count", 0) or 0)
            msg = f"AI 연결 테스트 {'PASS' if passed else 'CHECK'} ({provider}/{status}, scored={scored})"
            self._append_log(msg, "INFO" if passed else "WARN")
            self.status_message.set(msg)
            if passed:
                messagebox.showinfo("AI 연결 테스트", msg)
            else:
                messagebox.showwarning("AI 연결 테스트", msg)
        except Exception as exc:
            self._append_log(f"AI 연결 테스트 실패: {exc}", "ERROR")
            self.status_message.set(f"AI 연결 테스트 실패: {exc}")
            messagebox.showerror("AI 연결 테스트 실패", str(exc))

    def _start_loop(self) -> None:
        interval = self.poll_ms.get()
        try:
            interval_int = int(interval)
            if interval_int < 1:
                raise ValueError("interval must be at least 1")
            live_token = None
            mode = str(self.mode.get() or "").strip().lower()
            if mode == "live":
                live_token = simpledialog.askstring("Live 확인", "LIVE 시작 토큰을 입력하세요.", parent=self.root)
                if live_token is None:
                    self.status_message.set("자동 실행 시작 취소")
                    return

            result = self.runtime.start(interval_seconds=interval_int, live_confirm_token=live_token)
            status = str(result.get("status", ""))
            if status == "reject_preflight":
                preflight = result.get("preflight", {}) if isinstance(result, dict) else {}
                reason = " / ".join(preflight.get("errors", [])[:3]) if isinstance(preflight, dict) else "preflight fail"
                self._append_log(f"자동 실행 차단(preflight): {reason}", "WARN")
                self.status_message.set(f"자동 실행 차단(preflight): {reason}")
                return
            if status == "reject_validation_gate":
                gate = result.get("validation_gate", {}) if isinstance(result, dict) else {}
                reason = " / ".join(gate.get("errors", [])[:3]) if isinstance(gate, dict) else "validation gate fail"
                self._append_log(f"자동 실행 차단(validation): {reason}", "WARN")
                self.status_message.set(f"자동 실행 차단(validation): {reason}")
                return
            if status == "reject_live_ack":
                self._append_log("자동 실행 차단: live 토큰 불일치", "WARN")
                self.status_message.set("자동 실행 차단: live 토큰 불일치")
                return
            self._append_log(f"자동 실행 시작: {interval_int}초", "INFO")
            self.status_message.set(f"자동 실행 시작: {result.get('status')}")
        except Exception as exc:
            self._append_log(f"시작 실패: {exc}", "ERROR")
            messagebox.showerror("시작 실패", str(exc))
            self.status_message.set(f"시작 실패: {exc}")

    def _stop_loop(self) -> None:
        try:
            result = self.runtime.stop()
            self._append_log(f"자동 실행 중지: {result.get('status')}", "WARN")
            self.status_message.set(f"자동 실행 중지: {result.get('status')}")
            self._refresh()
        except Exception as exc:
            self._append_log(f"중지 실패: {exc}", "ERROR")
            messagebox.showerror("중지 실패", str(exc))
            self.status_message.set(f"중지 실패: {exc}")

    def _clear_risk(self) -> None:
        confirm = simpledialog.askstring("리스크 해제", "리스크 해제 토큰을 입력하세요.", parent=self.root)
        if confirm is None:
            return
        try:
            result = self.runtime.clear_risk_halt(confirm_token=confirm)
            self._append_log(f"리스크 해제 응답: {result.get('status')}", "INFO")
            self.status_message.set(f"리스크 해제 응답: {result.get('status')}")
            if result.get("status") == "reject":
                reason = result.get("reason", "-")
                messagebox.showwarning("리스크 해제 거부", reason)
                self._append_log(f"리스크 해제 거부: {reason}", "WARN")
            self._refresh()
        except Exception as exc:
            self._append_log(f"리스크 해제 실패: {exc}", "ERROR")
            messagebox.showerror("리스크 해제 실패", str(exc))
            self.status_message.set(f"리스크 해제 실패: {exc}")

    def _save_thresholds(self) -> None:
        try:
            notify_payload = {
                "notifications": {
                    "enabled": bool(self.notify_enabled.get()),
                    "cooldown_seconds": float(self.notify_cooldown.get() or 0),
                    "max_per_hour": int(self.notify_hour_limit.get() or 0),
                },
                "risk_limits": {
                    "reject_alert_profile": self.alert_profile.get() or "auto",
                    "reject_rate_warn": float(self.alert_warn.get() or 0),
                    "reject_rate_critical": float(self.alert_critical.get() or 0),
                    "reject_reason_rate_warn": float(self.alert_reason_warn.get() or 0),
                    "reject_reason_rate_critical": float(self.alert_reason_critical.get() or 0),
                    "reject_reason_min_samples": int(self.alert_reason_min_samples.get() or 20),
                },
                "validation_gate": {
                    "alert_enabled": bool(self.validation_alert_enabled.get()),
                    "alert_min_samples": int(self.validation_alert_min_samples.get() or 5),
                    "alert_pass_rate_warn": float(self.validation_alert_pass_warn.get() or 0.6),
                    "alert_pass_rate_critical": float(self.validation_alert_pass_critical.get() or 0.4),
                    "alert_max_drawdown_warn": float(self.validation_alert_dd_warn.get() or 0.25),
                    "alert_max_drawdown_critical": float(self.validation_alert_dd_critical.get() or 0.35),
                },
            }
        except ValueError as exc:
            self._append_log(f"임계치 입력 오류: {exc}", "ERROR")
            messagebox.showerror("입력 오류", f"숫자 형식이 올바르지 않습니다. {exc}")
            return

        try:
            self.runtime.patch_config(notify_payload)
            self._append_log("알림/임계치 저장 완료", "INFO")
            self.status_message.set("임계치 및 알림 설정 저장 완료")
            self._refresh()
            messagebox.showinfo("완료", "임계치/알림이 저장되었습니다.")
        except Exception as exc:
            self._append_log(f"임계치 저장 실패: {exc}", "ERROR")
            messagebox.showerror("저장 실패", str(exc))

    def _load_learning(self) -> None:
        try:
            days = int(self.learning_days.get() or 14)
            data = self.runtime.get_learning(window_days=days)
            tunings = data.get("tuning", [])
            self.learn_tv.delete(*self.learn_tv.get_children())
            for item in tunings:
                confidence = item.get("confidence", 0.0)
                if isinstance(confidence, (int, float)):
                    confidence_text = f"{confidence * 100:.2f}"
                else:
                    confidence_text = "-"
                self.learn_tv.insert(
                    "",
                    "end",
                    values=(
                        item.get("strategy", "-"),
                        item.get("action", "-"),
                        _safe(item.get("current_weight", 0)),
                        _safe(item.get("suggested_weight", 0)),
                        confidence_text,
                        item.get("reason", "-"),
                    ),
                )
            auto = data.get("auto_learning", {}) or {}
            auto_last = auto.get("last_result", {}) or {}
            auto_state = auto_last.get("status", "idle")
            auto_remain = auto.get("remaining_cycles_to_next_apply", "-")
            self.learning_status.set(f"제안 개수: {len(tunings)} | 자동학습: {auto_state} (다음 {auto_remain} cycle)")
        except Exception as exc:
            self._append_log(f"학습 조회 실패: {exc}", "WARN")
            self.learning_status.set(f"학습 조회 실패: {exc}")

    def _save_auto_learning(self) -> None:
        try:
            payload = {
                "auto_learning": {
                    "enabled": bool(self.auto_learning_enabled.get()),
                    "paper_only": bool(self.auto_learning_paper_only.get()),
                    "allow_pause": bool(self.auto_learning_allow_pause.get()),
                    "apply_interval_cycles": int(self.auto_learning_interval.get() or 20),
                    "window_days": int(self.auto_learning_window_days.get() or 14),
                    "min_trades_per_strategy": int(self.auto_learning_min_trades.get() or 8),
                    "min_confidence": float(self.auto_learning_min_confidence.get() or 0.62),
                    "max_weight_step_pct": float(self.auto_learning_max_step.get() or 0.2),
                    "max_strategy_changes_per_apply": int(self.auto_learning_max_changes.get() or 3),
                    "max_applies_per_day": int(self.auto_learning_max_daily.get() or 8),
                }
            }
        except ValueError as exc:
            self._append_log(f"자동학습 입력 오류: {exc}", "ERROR")
            messagebox.showerror("입력 오류", f"자동학습 값 형식이 올바르지 않습니다. {exc}")
            return

        try:
            self.runtime.patch_config(payload)
            self._append_log("자동학습 설정 저장 완료", "INFO")
            self.status_message.set("자동학습 설정 저장 완료")
            self._refresh()
            self._load_learning()
            self._load_config()
            messagebox.showinfo("완료", "자동학습 설정이 저장되었습니다.")
        except Exception as exc:
            self._append_log(f"자동학습 설정 저장 실패: {exc}", "ERROR")
            messagebox.showerror("저장 실패", str(exc))

    def _apply_learning_selected(self) -> None:
        selected = self.learn_tv.selection()
        if not selected:
            messagebox.showinfo("선택 필요", "적용할 전략을 먼저 선택해 주세요.")
            return
        strategy_filter = []
        for item_id in selected:
            values = self.learn_tv.item(item_id, "values")
            if values:
                strategy_filter.append(values[0])
        self._apply_learning(strategy_filter)

    def _apply_learning_all(self) -> None:
        self._apply_learning(None)

    def _apply_learning(self, strategy_filter: list[str] | None) -> None:
        try:
            days = int(self.learning_days.get() or 14)
            result = self.runtime.apply_learning(
                window_days=days,
                strategy_filter=strategy_filter,
            )
            self._append_log(f"복기 튜닝 적용 완료: {result.get('applied_count', 0)}개", "INFO")
            self.learning_status.set(f"적용 완료: {result.get('applied_count', 0)}개")
            self._load_learning()
            self._load_config()
            self._refresh_learning_events()
        except Exception as exc:
            self._append_log(f"복기 적용 실패: {exc}", "ERROR")
            messagebox.showerror("적용 실패", str(exc))
            self.learning_status.set(f"적용 실패: {exc}")

    def _refresh_learning_events(self) -> None:
        try:
            rows = self.runtime.get_auto_learning_events(limit=80)
        except Exception as exc:
            self._append_log(f"자동학습 이력 조회 실패: {exc}", "WARN")
            return

        self.learn_event_tv.delete(*self.learn_event_tv.get_children())
        for item in rows:
            before = item.get("weight_before")
            after = item.get("weight_after")
            if isinstance(before, (int, float)) and isinstance(after, (int, float)):
                weight_text = f"{before:.3f} -> {after:.3f}"
            elif isinstance(after, (int, float)):
                weight_text = f"- -> {after:.3f}"
            else:
                weight_text = "-"

            confidence = item.get("confidence")
            if isinstance(confidence, (int, float)):
                confidence_text = f"{confidence * 100:.1f}%"
            else:
                confidence_text = "-"

            self.learn_event_tv.insert(
                "",
                "end",
                values=(
                    str(item.get("ts", "-"))[:19],
                    item.get("source", "-"),
                    item.get("mode", "-"),
                    item.get("cycle", "-"),
                    item.get("strategy", "-"),
                    item.get("action", "-"),
                    weight_text,
                    confidence_text,
                    item.get("reason", "-"),
                ),
            )

    def _refresh_validation_history(self) -> None:
        try:
            payload = self.runtime.get_validation_history(limit=40)
        except Exception as exc:
            self._append_log(f"검증 이력 조회 실패: {exc}", "WARN")
            return

        total = int(payload.get("total_runs", 0) or 0)
        pass_rate = float(payload.get("pass_rate", 0.0) or 0.0)
        avg_pnl = float(payload.get("avg_pnl_total_usdt", 0.0) or 0.0)
        avg_win = float(payload.get("avg_win_rate", 0.0) or 0.0)
        avg_dd = float(payload.get("avg_max_drawdown_pct", 0.0) or 0.0)
        latest = payload.get("latest") or {}
        latest_state = "PASS" if bool(latest.get("overall_passed", False)) else "FAIL"
        self.validation_history_status.set(
            f"최근 {total}회 | 통과율 {_pct(pass_rate)} | 평균PnL {_safe(avg_pnl)} | 평균승률 {_pct(avg_win)} | 평균MDD {_pct(avg_dd)} | 최신 {latest_state}"
        )

        rows = payload.get("recent_runs", []) or []
        self.validation_tv.delete(*self.validation_tv.get_children())
        for item in rows:
            overall = "PASS" if bool(item.get("overall_passed", False)) else "FAIL"
            bt = item.get("backtest_passed")
            wf = item.get("walk_forward_passed")
            bt_text = "-" if bt is None else ("PASS" if bool(bt) else "FAIL")
            wf_text = "-" if wf is None else ("PASS" if bool(wf) else "FAIL")
            self.validation_tv.insert(
                "",
                "end",
                values=(
                    str(item.get("timestamp", "-"))[:19],
                    overall,
                    bt_text,
                    wf_text,
                    _safe(round(float(item.get("pnl_total_usdt", 0.0) or 0.0), 2)),
                    _pct(float(item.get("win_rate", 0.0) or 0.0)),
                    _pct(float(item.get("max_drawdown_pct", 0.0) or 0.0)),
                ),
            )

    def _trigger_validation_alert_test(self, level: str) -> None:
        lv = str(level or "warn").strip().lower()
        try:
            result = self.runtime.trigger_validation_alert_test(level=lv)
            status = str(result.get("status", "unknown"))
            if status == "sent":
                msg = f"검증 알람 테스트({lv}) 발송 시도 완료"
                self._append_log(msg, "INFO")
                self.status_message.set(msg)
                messagebox.showinfo("검증 알람 테스트", msg)
            else:
                reason = str(result.get("reason", status))
                msg = f"검증 알람 테스트({lv}) 실패/스킵: {reason}"
                self._append_log(msg, "WARN")
                self.status_message.set(msg)
                messagebox.showwarning("검증 알람 테스트", msg)
            self._refresh()
        except Exception as exc:
            self._append_log(f"검증 알람 테스트 실패: {exc}", "ERROR")
            self.status_message.set(f"검증 알람 테스트 실패: {exc}")
            messagebox.showerror("검증 알람 테스트 실패", str(exc))

    def _load_config(self) -> None:
        cfg = self.runtime.get_config()
        self.config_text.delete("1.0", tk.END)
        self.config_text.insert("1.0", json.dumps(cfg, ensure_ascii=False, indent=2))

    def _save_config(self) -> None:
        raw = self.config_text.get("1.0", tk.END).strip()
        try:
            payload = json.loads(raw or "{}")
        except json.JSONDecodeError as exc:
            self._append_log(f"설정 저장 실패: JSON 오류 - {exc}", "ERROR")
            messagebox.showerror("설정 오류", f"JSON 형식이 올바르지 않습니다. {exc}")
            return

        if "notifications" in payload and not isinstance(payload["notifications"], dict):
            messagebox.showerror("설정 오류", "notifications는 객체여야 합니다.")
            return
        if "risk_limits" in payload and not isinstance(payload["risk_limits"], dict):
            messagebox.showerror("설정 오류", "risk_limits는 객체여야 합니다.")
            return

        try:
            self.runtime.patch_config(payload)
            self._append_log("설정 저장 완료", "INFO")
            self._load_config()
            self._refresh()
            messagebox.showinfo("완료", "설정이 저장되었습니다.")
        except Exception as exc:
            self._append_log(f"설정 저장 실패: {exc}", "ERROR")
            messagebox.showerror("저장 실패", str(exc))

    def _on_close(self) -> None:
        try:
            self.runtime.close()
        except Exception:
            pass
        self.root.destroy()


def main(config_path: str = "configs/default.json") -> None:
    TradingDashboardWindow(config_path).run()


if __name__ == "__main__":
    main()
