from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass
class KalmanTrendTracker:
    process_var: float = 1e-2
    measurement_var: float = 1.0

    def __post_init__(self) -> None:
        self.initialized = False
        self.x = 0.0
        self.v = 0.0
        self.p00 = 10.0
        self.p01 = 0.0
        self.p10 = 0.0
        self.p11 = 10.0
        self._innovation_var = max(float(self.measurement_var), 1e-9)

    @staticmethod
    def _clamp(value: float, lo: float, hi: float) -> float:
        return max(lo, min(hi, value))

    def update(self, measurement: float, dt: float = 1.0, measurement_var: float | None = None) -> dict[str, float]:
        z = float(measurement)
        if not self.initialized:
            self.x = z
            self.v = 0.0
            self.p00 = 4.0
            self.p01 = 0.0
            self.p10 = 0.0
            self.p11 = 4.0
            self.initialized = True
            return {
                "price": self.x,
                "velocity": self.v,
                "velocity_ratio": 0.0,
                "trend_score": 0.0,
                "innovation": 0.0,
                "innovation_z": 0.0,
                "uncertainty": 0.0,
            }

        dt = max(1e-6, float(dt))
        q = max(1e-12, float(self.process_var))
        r = max(1e-9, float(measurement_var if measurement_var is not None else self.measurement_var))
        self.measurement_var = r

        x_pred = self.x + self.v * dt
        v_pred = self.v

        dt2 = dt * dt
        dt3 = dt2 * dt
        dt4 = dt2 * dt2

        p00_pred = self.p00 + dt * (self.p10 + self.p01) + dt2 * self.p11 + 0.25 * dt4 * q
        p01_pred = self.p01 + dt * self.p11 + 0.5 * dt3 * q
        p10_pred = self.p10 + dt * self.p11 + 0.5 * dt3 * q
        p11_pred = self.p11 + dt2 * q

        innovation = z - x_pred
        s = max(p00_pred + r, 1e-9)
        k0 = p00_pred / s
        k1 = p10_pred / s

        self.x = x_pred + k0 * innovation
        self.v = v_pred + k1 * innovation

        self.p00 = (1.0 - k0) * p00_pred
        self.p01 = (1.0 - k0) * p01_pred
        self.p10 = p10_pred - k1 * p00_pred
        self.p11 = p11_pred - k1 * p01_pred

        self._innovation_var = max(1e-9, 0.92 * self._innovation_var + 0.08 * (innovation * innovation))
        innovation_z = innovation / max(math.sqrt(s), 1e-9)

        velocity_ratio = self.v / max(abs(self.x), 1e-9)
        trend_score = math.tanh(velocity_ratio * 280.0)
        uncertainty = math.sqrt(max(self.p00, 1e-9)) / max(abs(self.x), 1e-9)

        return {
            "price": float(self.x),
            "velocity": float(self.v),
            "velocity_ratio": float(velocity_ratio),
            "trend_score": float(self._clamp(trend_score, -1.0, 1.0)),
            "innovation": float(innovation),
            "innovation_z": float(innovation_z),
            "uncertainty": float(max(0.0, uncertainty)),
        }

