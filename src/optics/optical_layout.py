"""Camera 100 optical-layout schematic (Figure 5b / 18_optical_layout*.png).

Reads ``configs/camera_100.toml`` and draws the sensor → slurry chain to
scale, in English (derived values annotated) and Slovak (measured values).

    uv run python -m optics.optical_layout
"""

from __future__ import annotations

import tomllib
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

from optics.config import SOURCE_RANK, load_camera, source_classes

FIG_DIR = Path(__file__).resolve().parents[2] / "docs" / "optics" / "figures"
# Arrow colour = how well the length is sourced (tags in configs/camera_100.toml).
SOURCE_COLOR = {
    **dict.fromkeys(("MEASURED", "PHOTO", "DATASHEET", "CHOICE"), "black"),
    **dict.fromkeys(("DERIVED", "PLANT", "ESTIMATE"), "#c05800"),
    **dict.fromkeys(("ASSUMED", "UNSOURCED"), "red"),
}
SOURCE_LEGEND = {
    "en": "black = photo / datasheet   ·   orange = plant statement (≈) "
    "or estimate   ·   red = assumed or unsourced   (configs/camera_100.toml)",
    "sk": "čierna = foto / katalóg   ·   oranžová = údaj z cukrovaru (≈) "
    "alebo odhad   ·   červená = predpoklad alebo bez zdroja",
}


def _weakest(cls: dict[str, str], *keys: str) -> str:
    """Weakest provenance class among the config keys a quantity uses."""
    return max((cls[k] for k in keys), key=lambda c: SOURCE_RANK.index(c))


def _sources() -> dict[str, str]:
    """Provenance class of each drawn length, from the config tags."""
    c = source_classes()
    return {
        "body": c["camera.body_length_mm"],
        "sensor": c["camera.flange_distance_mm"],
        "e": c["lens.extension_tube_mm"],
        "lens": _weakest(c, "lens.body_length_mm", "lens.focus_travel_mm"),
        "a": c["lens.air_gap_mm"],
        "t": c["sight_glass.thickness_mm"],
        "i": _weakest(
            c,
            "lens.focal_length_mm",
            "lens.extension_tube_mm",
            "lens.focus_travel_mm",
        ),
        "real": _weakest(
            c,
            "lens.focal_length_mm",
            "lens.extension_tube_mm",
            "lens.focus_travel_mm",
            "lens.air_gap_mm",
            "sight_glass.thickness_mm",
            "sight_glass.refractive_index",
        ),
        "model": c["camera.model"],
        "pitch": _weakest(
            c, "camera.sensor_width_mm", "camera.native_width_px"
        ),
    }


def _geometry() -> dict[str, float]:
    cfg = load_camera()
    f, e, t, n = (
        cfg.focal_length_mm,
        cfg.extension_tube_mm,
        cfg.sight_glass_thickness_mm,
        cfg.sight_glass_index,
    )
    i = f + e + cfg.focus_travel_mm
    d_focus = f * i / (i - f)
    delta = t * (1 - 1 / n)
    return {
        "f": f,
        "e": e,
        "t": t,
        "n": n,
        "i": i,
        "d_focus": d_focus,
        "delta": delta,
        "t_app": t - delta,
        "body": cfg.lens_body_length_mm + cfg.focus_travel_mm,
        "air": cfg.air_gap_mm,
        "um_px": cfg.native_pixel_pitch_um * (d_focus - f) / f,
        # Front principal plane H: d_focus back from the inner glass face in
        # apparent coordinates, i.e. this far behind the lens front element.
        "h_offset": d_focus - (t - delta) - cfg.air_gap_mm,
        # Rear principal plane H': i in front of the sensor, measured from
        # the lens front element. H != H' because the lens is thick.
        "flange": cfg.flange_distance_mm,
        "camera": cfg.body_length_mm,
        "slurry": tomllib.loads(cfg.source_path.read_text())["figures"][
            "slurry_depth_mm"
        ],
        "h2_offset": cfg.flange_distance_mm
        + e
        + cfg.lens_body_length_mm
        + cfg.focus_travel_mm
        - i,
    }


def _draw(
    labels: dict[str, str], out: Path, g: dict[str, float], src: dict[str, str]
) -> None:
    segs = [
        ("body", g["camera"], "#333333", "white"),
        ("ext", g["e"], "#7f7f7f", "black"),
        ("lens", g["body"], "#3b76b5", "black"),
        ("air", g["air"], "#efefef", "black"),
        ("glass", g["t"], "#c6e2fb", "black"),
        ("slurry", g["slurry"], "#c9a05a", "black"),
    ]
    fig, ax = plt.subplots(figsize=(16, 5))
    x = 0.0
    edges: dict[str, float] = {}
    for key, w, fc, tc in segs:
        ax.add_patch(Rectangle((x, 0), w, 1, fc=fc, ec="black"))
        ax.text(
            x + w / 2, 0.5, labels[key], ha="center", va="center", color=tc
        )
        edges[key] = x
        x += w
    sensor = edges["ext"] - g["flange"]
    ax.plot([sensor] * 2, [0, 1], color="red", lw=3)
    ax.text(sensor, 1.05, labels["sensor"], color="red", ha="center")
    ax.plot([edges["slurry"]] * 2, [0, 1], color="green", lw=3)
    ax.text(edges["slurry"], 1.05, labels["inner"], color="green", ha="center")

    def dim(
        x0: float, x1: float, y: float, text: str, color: str = "black"
    ) -> None:
        ax.annotate(
            "",
            (x0, y),
            (x1, y),
            arrowprops={"arrowstyle": "<->", "color": color},
        )
        ax.text(
            (x0 + x1) / 2, y - 0.04, text, ha="center", va="top", color=color
        )

    col = {k: SOURCE_COLOR[v] for k, v in src.items()}
    dim(edges["body"], edges["ext"], -0.15, labels["dim_cam"], col["body"])
    dim(edges["ext"], edges["lens"], -0.15, labels["dim_e"], col["e"])
    dim(edges["lens"], edges["air"], -0.15, labels["dim_body"], col["lens"])
    dim(edges["air"], edges["glass"], -0.15, labels["dim_a"], col["a"])
    dim(edges["glass"], edges["slurry"], -0.15, labels["dim_t"], col["t"])
    if "dim_real" in labels:
        h = edges["air"] - g["h_offset"]
        h2 = sensor + g["i"]
        for xx, name in ((h, labels["H"]), (h2, labels["H2"])):
            ax.plot([xx] * 2, [0, 1], color="navy", ls="--")
            ax.text(xx, 1.05, name, color="navy", ha="center")
        dim(sensor, h2, -0.6, labels["dim_i"], col["i"])
        dim(h, edges["slurry"], -1.05, labels["dim_real"], col["real"])
    ax.set_xlim(-2, x + 2)
    ax.set_ylim(-1.55, 1.4)
    ax.axis("off")
    ax.set_title(
        labels["title"],
        color=col["pitch"] if "dim_real" in labels else "black",
    )
    ax.text((x - 2) / 2, -1.5, labels["legend"], ha="center", fontsize=9)
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)


def main() -> None:
    g = _geometry()
    src = _sources()
    tag = {k: v.lower() for k, v in src.items()}
    model = load_camera().name
    en = {
        "title": (
            "Camera 100 — how far the camera looks into the sugar slurry "
            f"(drawn to scale; 1 px on the sensor = {g['um_px']:.2f} µm in the "
            f"slurry, pixel pitch {tag['pitch']})"
        ),
        "legend": SOURCE_LEGEND["en"],
        "body": f"camera body\n{model}?\n(model {tag['model']})",
        "dim_cam": f"{g['camera']:.0f} mm\n({tag['body']})",
        "ext": "spacer ring\n(moves lens away from sensor\nso it can focus close)",
        "lens": "\n\n\nlens",
        "air": "air",
        "glass": "sight glass",
        "slurry": "sugar slurry\n(inside the vessel)",
        "sensor": "image sensor\n(the chip that records the picture)",
        "inner": "SHARP-FOCUS PLANE\n= inner face of the glass",
        "H": "H",
        "H2": "H'",
        "dim_e": f"spacer e = {g['e']:.0f} mm\n({tag['e']})",
        "dim_body": f"lens body {g['body']:.1f} mm\n({tag['lens']})",
        "dim_a": f"air gap a = {g['air']:.0f} mm\n({tag['a']})",
        "dim_t": f"glass t = {g['t']:.0f} mm\n({tag['t']})",
        "dim_i": (
            f"sensor → H' = f + e + focus travel = {g['i']:.0f} mm ({tag['i']})"
        ),
        "dim_real": (
            f"H → sharp-focus plane = {g['d_focus'] + g['delta']:.1f} mm "
            f"({tag['real']})"
        ),
    }
    sk = {
        "title": "Optická sústava — kamera 100 (v mierke)",
        "legend": SOURCE_LEGEND["sk"],
        "body": f"telo kamery\n{model}?",
        "dim_cam": f"{g['camera']:.0f} mm",
        "ext": "medzikrúžok",
        "lens": f"objektív Fujinon\nHF35HA-1B\n(dĺžka {g['body']:.1f} mm)",
        "air": "vzduchová\nmedzera",
        "glass": "priezor",
        "slurry": "cukrovina",
        "sensor": "snímač",
        "H": "H",
        "H2": "H'",
        "inner": "vnútorná strana skla\n(rovina, kde kamera ostrí)",
        "dim_e": f"(A) medzikrúžok\n{g['e']:.0f} mm",
        "dim_a": f"(B) objektív → sklo\n{g['air']:.0f} mm",
        "dim_t": f"(C) hrúbka skla\n{g['t']:.0f} mm",
        "dim_body": f"objektív\n{g['body']:.1f} mm",
    }
    _draw(en, FIG_DIR / "18_optical_layout.png", g, src)
    _draw(sk, FIG_DIR / "18_optical_layout_sk_variables.png", g, src)
    for k, v in g.items():
        print(f"{k:>8} = {v:.3f}")


if __name__ == "__main__":
    main()
