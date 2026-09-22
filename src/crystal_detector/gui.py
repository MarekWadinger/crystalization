"""Launch the Cellpose GUI for annotating frames and retraining the model.

Thin wrapper over ``python -m cellpose`` that pre-sets ``QT_API=pyqt6`` (avoids
the PyQt5/PyQt6 clash) so the annotate -> train loop is one command:

    uv sync --group crystal-detector-gui   # one-time: installs Qt
    uv run crystal-detector-gui

In the GUI: load a frame, click **run cpsam**, correct masks (Shift+click or
right-click starts an outline, click again to close it; Ctrl+click deletes), then Ctrl+S to save the
``*_seg.npy`` label. Train via **Models -> Train new model** on the folder of
images + ``_seg.npy`` files; the result lands in ``training_data/models/`` and
is usable with ``crystal-detector-analyze --model <path>``.
"""

import os
import subprocess
import sys


def main():
    env = dict(os.environ)
    env.setdefault("QT_API", "pyqt6")
    print(
        "Launching Cellpose GUI — run cpsam, correct masks, Ctrl+S to save "
        "_seg.npy labels, then Models -> Train new model."
    )
    proc = subprocess.run([sys.executable, "-m", "cellpose"], env=env)
    if proc.returncode != 0:
        print(
            "\nGUI failed to launch. Install the GUI deps with:\n"
            "  uv sync --group crystal-detector-gui",
            file=sys.stderr,
        )
    sys.exit(proc.returncode)


if __name__ == "__main__":
    main()
