"""Fine-tune the crystal checkpoint on the team's annotations.

    uv run crystal-detector-finetune                 # ≈ 1–2 h on an Apple-silicon Mac
    make -C src/crystal_detector finetune            # same

Pools every ``annotations/<name>/<stage>/HHMMSS.png`` that has a
``HHMMSS_seg.npy`` label, holds out one frame per person for evaluation,
and continues training from the current checkpoint with the Cellpose GUI
defaults (lr 1e-5, weight decay 0.1, 100 epochs). Output:

* ``training_data/models/cpsam_YYYYMMDD_HHMMSS`` — the new checkpoint
* ``training_data/eval/*.png`` — held-out frames: label | current | new
* a table of AP@0.5 (current vs new) on the held-out frames

Nothing switches to the new model automatically. To adopt it, run
``crystal-detector-analyze --model <path>`` on a few frames, then upload
it and change ``HF_MODEL_FILE`` in ``analyze.py``.
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np

from .analyze import CELLPROB_THRESHOLD, FLOW_THRESHOLD, resolve_model
from .annotate import ANNOTATIONS, _label

TRAINING = Path(__file__).resolve().parent / "training_data"


def _pairs() -> list[tuple[Path, np.ndarray, np.ndarray]]:
    out = []
    for png in sorted(ANNOTATIONS.glob("*/*/*.png")):
        if not _label(png).exists():
            continue
        bgr = cv2.imread(str(png))
        if bgr is None:
            raise SystemExit(f"cannot read {png}")
        img = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        masks = np.load(_label(png), allow_pickle=True).item()["masks"]
        out.append((png, img, masks.astype(np.int32)))
    return out


def _split(pairs):
    """Hold out one frame per person: their middle boiling frame (the main
    growth stage, always has crystals); if unlabelled, their frame with the
    most crystals."""
    test_idx: set[int] = set()
    for who in sorted({p.parents[1].name for p, _, _ in pairs}):
        mine = [
            i for i, (p, _, _) in enumerate(pairs) if p.parents[1].name == who
        ]
        boiling = sorted(
            i for i in mine if pairs[i][0].parent.name == "boiling"
        )
        if boiling:
            test_idx.add(boiling[len(boiling) // 2])
        else:
            test_idx.add(max(mine, key=lambda i: int(pairs[i][2].max())))
    train = [x for i, x in enumerate(pairs) if i not in test_idx]
    test = [x for i, x in enumerate(pairs) if i in test_idx]
    return train, test


def _outline(img: np.ndarray, masks: np.ndarray, color) -> np.ndarray:
    from cellpose import utils

    out = img.copy()
    for o in utils.outlines_list(masks):
        cv2.polylines(out, [o.astype(np.int32)], True, color, 1)
    return out


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=(__doc__ or "").split("\n\n")[1])
    ap.add_argument("--epochs", type=int, default=100)
    ap.add_argument(
        "--max-frames", type=int, help="smoke test: train on N frames only"
    )
    ap.add_argument("--cpu", action="store_true", help="force CPU (slow)")
    a = ap.parse_args(argv)

    from cellpose import io as cp_io
    from cellpose import metrics, models, train

    cp_io.logger_setup()  # per-epoch loss and timing in the terminal
    pairs = _pairs()
    if len(pairs) < 2:
        raise SystemExit(
            f"need labelled frames under {ANNOTATIONS}, found {len(pairs)}"
        )
    train_set, test_set = _split(pairs)
    if a.max_frames:
        train_set = train_set[: a.max_frames]
    print(
        f"{len(train_set)} training frames, {len(test_set)} held out (one per person)"
    )

    base = resolve_model()
    name = "cpsam_" + datetime.now().strftime("%Y%m%d_%H%M%S")
    (TRAINING / "models").mkdir(parents=True, exist_ok=True)
    model = models.CellposeModel(gpu=not a.cpu, pretrained_model=str(base))
    print(f"continuing from {base.name} on {model.device}")
    new_path, *_ = train.train_seg(
        model.net,
        train_data=[img for _, img, _ in train_set],
        train_labels=[m for _, _, m in train_set],
        test_data=[img for _, img, _ in test_set],
        test_labels=[m for _, _, m in test_set],
        min_train_masks=0,  # keep frames with few crystals
        learning_rate=1e-5,
        weight_decay=0.1,
        n_epochs=a.epochs,
        nimg_per_epoch=max(2, len(train_set)),
        save_path=str(TRAINING),  # cellpose writes <save_path>/models/<name>
        model_name=name,
    )
    new_path = Path(new_path)

    # --- evaluation on the held-out frames: current vs new -----------------
    eval_dir = TRAINING / "eval"
    eval_dir.mkdir(exist_ok=True)
    current = models.CellposeModel(gpu=not a.cpu, pretrained_model=str(base))
    fresh = models.CellposeModel(gpu=not a.cpu, pretrained_model=str(new_path))
    rows = []
    for png, img, gt in test_set:
        preds = {}
        for tag, m in (("current", current), ("new", fresh)):
            preds[tag] = m.eval(
                img,
                diameter=None,
                flow_threshold=FLOW_THRESHOLD,
                cellprob_threshold=CELLPROB_THRESHOLD,
            )[0]
        ap_cur = metrics.average_precision(
            [gt], [preds["current"]], threshold=[0.5]
        )[0][0, 0]
        ap_new = metrics.average_precision(
            [gt], [preds["new"]], threshold=[0.5]
        )[0][0, 0]
        who, stage = png.parents[1].name, png.parent.name
        rows.append(
            (
                f"{who}/{stage}/{png.stem}",
                int(gt.max()),
                int(preds["current"].max()),
                int(preds["new"].max()),
                ap_cur,
                ap_new,
            )
        )
        panel = np.hstack(
            [
                _outline(img, gt, (255, 255, 255)),
                _outline(img, preds["current"], (255, 80, 80)),
                _outline(img, preds["new"], (80, 255, 80)),
            ]
        )
        cv2.imwrite(
            str(eval_dir / f"{who}_{stage}_{png.stem}.png"),
            cv2.cvtColor(panel, cv2.COLOR_RGB2BGR),
        )

    print(
        "\nheld-out frame                               label  current  new   AP@0.5 current → new"
    )
    for key, n_gt, n_cur, n_new, ap_cur, ap_new in rows:
        print(
            f"{key:<44} {n_gt:>5} {n_cur:>8} {n_new:>4}   {ap_cur:.2f} → {ap_new:.2f}"
        )
    mean_cur = float(np.mean([r[4] for r in rows]))
    mean_new = float(np.mean([r[5] for r in rows]))
    print(
        f"{'mean':<44} {'':>5} {'':>8} {'':>4}   {mean_cur:.2f} → {mean_new:.2f}"
    )
    print(f"\nnew checkpoint: {new_path}")
    print(f"overlays (label | current | new): {eval_dir}/")
    print(
        "\nto adopt it:  uv run crystal-detector-analyze FRAME.png --model "
        f"{new_path}\n              uv run hf upload MarekWadinger/crystal-detector-cpsam "
        f"{new_path} {new_path.name}\n              then set HF_MODEL_FILE in analyze.py"
    )


if __name__ == "__main__":
    sys.exit(main())
