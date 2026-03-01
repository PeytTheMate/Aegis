"""Extended Kalman Filter for IMU/GPS sensor fusion.

Implements a 5-state EKF (x, y, vx, vy, aoa) using pure-Python matrix
operations (no numpy dependency). The filter fuses high-rate IMU
measurements with low-rate GPS position fixes, enabling the PID
controller to operate on filtered state estimates rather than raw
(potentially corrupted) sensor readings.
"""

from __future__ import annotations

import math
from typing import Any

# ---------------------------------------------------------------------------
# Minimal matrix algebra (lists-of-lists, adequate for 5x5 systems)
# ---------------------------------------------------------------------------

Matrix = list[list[float]]
Vector = list[float]


def mat_zeros(rows: int, cols: int) -> Matrix:
    return [[0.0] * cols for _ in range(rows)]


def mat_identity(n: int) -> Matrix:
    m = mat_zeros(n, n)
    for i in range(n):
        m[i][i] = 1.0
    return m


def mat_add(a: Matrix, b: Matrix) -> Matrix:
    return [[a[i][j] + b[i][j] for j in range(len(a[0]))] for i in range(len(a))]


def mat_sub(a: Matrix, b: Matrix) -> Matrix:
    return [[a[i][j] - b[i][j] for j in range(len(a[0]))] for i in range(len(a))]


def mat_mul(a: Matrix, b: Matrix) -> Matrix:
    rows_a, cols_a = len(a), len(a[0])
    cols_b = len(b[0])
    result = mat_zeros(rows_a, cols_b)
    for i in range(rows_a):
        for k in range(cols_a):
            if a[i][k] == 0.0:
                continue
            for j in range(cols_b):
                result[i][j] += a[i][k] * b[k][j]
    return result


def mat_transpose(a: Matrix) -> Matrix:
    rows, cols = len(a), len(a[0])
    return [[a[j][i] for j in range(rows)] for i in range(cols)]


def mat_scale(a: Matrix, s: float) -> Matrix:
    return [[a[i][j] * s for j in range(len(a[0]))] for i in range(len(a))]


def mat_vec_mul(a: Matrix, v: Vector) -> Vector:
    return [sum(a[i][j] * v[j] for j in range(len(v))) for i in range(len(a))]


def vec_add(a: Vector, b: Vector) -> Vector:
    return [a[i] + b[i] for i in range(len(a))]


def vec_sub(a: Vector, b: Vector) -> Vector:
    return [a[i] - b[i] for i in range(len(a))]


def mat_inv(a: Matrix) -> Matrix:
    """Matrix inverse via Gauss-Jordan elimination with partial pivoting.

    Works reliably for the small matrices (2x2 to 5x5) used in the EKF.
    """
    n = len(a)
    # Augment with identity
    aug = [list(a[i]) + [1.0 if j == i else 0.0 for j in range(n)] for i in range(n)]

    for col in range(n):
        # Partial pivot
        max_row = col
        max_val = abs(aug[col][col])
        for row in range(col + 1, n):
            if abs(aug[row][col]) > max_val:
                max_val = abs(aug[row][col])
                max_row = row
        aug[col], aug[max_row] = aug[max_row], aug[col]

        pivot = aug[col][col]
        if abs(pivot) < 1e-15:
            # Near-singular: add small regularization
            pivot = 1e-10
            aug[col][col] = pivot

        inv_pivot = 1.0 / pivot
        for j in range(2 * n):
            aug[col][j] *= inv_pivot

        for row in range(n):
            if row == col:
                continue
            factor = aug[row][col]
            for j in range(2 * n):
                aug[row][j] -= factor * aug[col][j]

    return [aug[i][n:] for i in range(n)]


# ---------------------------------------------------------------------------
# Extended Kalman Filter
# ---------------------------------------------------------------------------

class EKF:
    """5-state Extended Kalman Filter for trajectory estimation.

    State vector: [x, y, vx, vy, aoa]
    - x, y: position (m)
    - vx, vy: velocity (m/s)
    - aoa: angle of attack (rad)

    IMU measurement: [vx, vy, aoa] (high rate, noisy)
    GPS measurement: [x, y] (low rate, less noisy)
    """

    N = 5  # state dimension

    def __init__(
        self,
        initial_state: Vector,
        process_noise_diag: Vector,
        imu_noise_diag: Vector,
        gps_noise_diag: Vector,
    ) -> None:
        self.x_hat: Vector = list(initial_state)
        self.P: Matrix = mat_scale(mat_identity(self.N), 0.1)
        self.Q: Matrix = _diag(process_noise_diag)
        self.R_imu: Matrix = _diag(imu_noise_diag)
        self.R_gps: Matrix = _diag(gps_noise_diag)
        self.innovation: Vector = [0.0] * 3

    def predict(self, ax: float, ay: float, aoa_rate: float, dt: float) -> None:
        """Prediction step using linear kinematics."""
        x, y, vx, vy, aoa = self.x_hat
        self.x_hat = [
            x + vx * dt,
            y + vy * dt,
            vx + ax * dt,
            vy + ay * dt,
            aoa + aoa_rate * dt,
        ]

        # State transition Jacobian F
        F = mat_identity(self.N)
        F[0][2] = dt  # dx/dvx
        F[1][3] = dt  # dy/dvy

        # P = F * P * F^T + Q
        FP = mat_mul(F, self.P)
        self.P = mat_add(mat_mul(FP, mat_transpose(F)), self.Q)

    def update_imu(self, z_vx: float, z_vy: float, z_aoa: float) -> None:
        """Update with IMU measurement [vx, vy, aoa]."""
        # Observation matrix H (3x5): picks out vx, vy, aoa
        H = mat_zeros(3, self.N)
        H[0][2] = 1.0  # observe vx
        H[1][3] = 1.0  # observe vy
        H[2][4] = 1.0  # observe aoa

        z = [z_vx, z_vy, z_aoa]
        self._update(H, z, self.R_imu)

    def update_gps(self, z_x: float, z_y: float) -> None:
        """Update with GPS measurement [x, y]."""
        H = mat_zeros(2, self.N)
        H[0][0] = 1.0  # observe x
        H[1][1] = 1.0  # observe y

        z = [z_x, z_y]
        self._update(H, z, self.R_gps)

    def _update(self, H: Matrix, z: Vector, R: Matrix) -> None:
        """Standard Kalman update: innovation, gain, state & covariance."""
        # Innovation y = z - H * x_hat
        predicted = mat_vec_mul(H, self.x_hat)
        y = vec_sub(z, predicted)
        if len(y) <= 3:
            self.innovation = list(y) + [0.0] * (3 - len(y))

        # S = H * P * H^T + R
        HP = mat_mul(H, self.P)
        S = mat_add(mat_mul(HP, mat_transpose(H)), R)

        # K = P * H^T * S^-1
        S_inv = mat_inv(S)
        PHt = mat_mul(self.P, mat_transpose(H))
        K = mat_mul(PHt, S_inv)

        # State update: x_hat += K * y
        Ky = mat_vec_mul(K, y)
        self.x_hat = vec_add(self.x_hat, Ky)

        # Covariance update: P = (I - K*H) * P
        KH = mat_mul(K, H)
        I_KH = mat_sub(mat_identity(self.N), KH)
        self.P = mat_mul(I_KH, self.P)


def _diag(values: Vector) -> Matrix:
    """Create a diagonal matrix from a vector."""
    n = len(values)
    m = mat_zeros(n, n)
    for i in range(n):
        m[i][i] = values[i]
    return m


def create_default_ekf(initial_state: Vector | None = None) -> EKF:
    """Create an EKF with sensible defaults for the 3-DoF trajectory sim."""
    state = initial_state or [0.0, 0.0, 0.0, 0.1, 0.0]
    return EKF(
        initial_state=state,
        process_noise_diag=[1.0, 1.0, 0.5, 0.5, 0.01],
        imu_noise_diag=[0.5, 0.5, 0.005],
        gps_noise_diag=[5.0, 5.0],
    )
