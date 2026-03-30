"""Core mrDMD fitting, reconstruction, and prediction."""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray
from pydmd import DMD, MrDMD

from predictor.types import DMDConfig, DMDResult


def fit_mrdmd(
    X: NDArray[np.float64],
    config: DMDConfig,
    frame_shape: tuple[int, int],
    n_pixels: int,
    dt: float = 1.0,
) -> DMDResult:
    """Fit multi-resolution DMD to a snapshot matrix.

    Args:
        X: snapshot matrix (n_features x n_frames). May be Hankel-embedded,
           so n_features >= n_pixels.
        config: DMD hyperparameters.
        frame_shape: (H, W) of the original (pre-Hankel) frames.
        n_pixels: H * W, the number of pixels per frame.
        dt: time step between snapshots.
    """
    dmd = DMD(svd_rank=config.svd_rank)
    mrdmd = MrDMD(dmd, max_level=config.max_level, max_cycles=config.max_cycles)
    mrdmd.fit(X)

    # Collect modes and level info across all resolution levels
    all_modes = []
    all_eigs = []
    mode_levels: list[int] = []
    for level in range(config.max_level + 1):
        try:
            pm = mrdmd.partial_modes(level=level)
            pe = mrdmd.partial_eigs(level=level)
        except (IndexError, ValueError):
            break
        n_modes_at_level = pm.shape[1]
        all_modes.append(pm)
        all_eigs.append(pe)
        mode_levels.extend([level] * n_modes_at_level)

    modes = np.hstack(all_modes) if all_modes else mrdmd.modes
    eigs = np.concatenate(all_eigs) if all_eigs else mrdmd.eigs

    return DMDResult(
        modes=modes,
        dynamics=mrdmd.dynamics,
        eigs=eigs,
        n_frames_train=X.shape[1],
        frame_shape=frame_shape,
        n_pixels=n_pixels,
        mrdmd=mrdmd,
        mode_levels=mode_levels,
    )


def reconstruct_modes(
    result: DMDResult,
    selected_indices: list[int],
    mean: NDArray[np.float64] | None = None,
) -> NDArray[np.float64]:
    """Reconstruct snapshots from a subset of DMD modes.

    Args:
        mean: temporal mean (n_pixels, 1) to add back. Pass the mean
            returned by load_video_snapshots to get viewable images.

    Returns:
        Reconstructed matrix of shape (n_pixels, n_frames), real, clipped to [0, 1].
    """
    if not selected_indices:
        n_cols = result.n_frames_train
        if mean is not None:
            return np.clip(
                np.broadcast_to(mean, (mean.shape[0], n_cols)),
                0.0, 1.0,
            )
        return np.zeros(
            (result.n_pixels, n_cols), dtype=np.float64
        )
    modes = result.modes[: result.n_pixels, selected_indices]
    dynamics = result.dynamics[selected_indices, :]
    recon = (modes @ dynamics).real
    if mean is not None:
        recon = recon + mean
    return np.clip(recon, 0.0, 1.0)


def predict_frames(
    result: DMDResult,
    n_predict: int,
    selected_indices: list[int],
    mean: NDArray[np.float64] | None = None,
    *,
    stabilize: bool = True,
) -> NDArray[np.float64]:
    """Predict future frames by extrapolating DMD dynamics.

    Args:
        mean: temporal mean (n_pixels, 1) to add back for viewable images.
        stabilize: Project eigenvalues onto the unit circle so
            predictions don't decay to zero or blow up.

    Returns:
        Predicted matrix of shape (n_pixels, n_predict), real, clipped to [0, 1].
    """
    if not selected_indices or n_predict <= 0:
        n = max(n_predict, 1)
        if mean is not None:
            return np.clip(
                np.broadcast_to(mean, (mean.shape[0], n)),
                0.0, 1.0,
            )
        return np.zeros(
            (result.n_pixels, n), dtype=np.float64
        )
    modes = result.modes[: result.n_pixels, selected_indices]
    eigs = result.eigs[selected_indices]
    dynamics = result.dynamics[selected_indices, :]

    if stabilize:
        eigs = eigs / np.abs(eigs)  # project onto unit circle

    # Extrapolate dynamics: last training column scaled by eig^step
    last_col = dynamics[:, -1]  # (n_selected,)
    predicted_cols = []
    for step in range(1, n_predict + 1):
        future_dyn = last_col * (eigs ** step)
        col = modes @ future_dyn
        predicted_cols.append(col.real)

    pred = np.column_stack(predicted_cols)
    if mean is not None:
        pred = pred + mean
    return np.clip(pred, 0.0, 1.0)


def snapshot_to_image(
    col: NDArray[np.float64],
    frame_shape: tuple[int, int],
) -> NDArray[np.uint8]:
    """Reshape a snapshot column vector to a grayscale image."""
    img = col.reshape(frame_shape)
    return (img * 255).astype(np.uint8)


def visualize_mode(
    result: DMDResult,
    mode_idx: int,
) -> NDArray[np.uint8]:
    """Visualize the spatial pattern of a single DMD mode."""
    mode = result.modes[: result.n_pixels, mode_idx]
    mag = np.abs(mode).reshape(result.frame_shape)
    if mag.max() > 0:
        mag = mag / mag.max()
    return (mag * 255).astype(np.uint8)


def get_mode_info(result: DMDResult) -> list[dict]:
    """Return metadata for each DMD mode."""
    n_modes = result.modes.shape[1]
    info = []
    for i in range(n_modes):
        eig = result.eigs[i]
        freq = np.abs(np.angle(eig)) / (2 * np.pi)
        growth = np.log(np.abs(eig)) if np.abs(eig) > 0 else 0.0
        level = result.mode_levels[i] if i < len(result.mode_levels) else -1
        info.append({
            "index": i,
            "level": level,
            "frequency": float(freq),
            "growth_rate": float(growth),
            "eigenvalue_abs": float(np.abs(eig)),
        })
    return info
