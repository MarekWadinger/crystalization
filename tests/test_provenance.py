"""Every value in the camera config must say where it comes from."""

import re
from pathlib import Path

CONFIG = Path(__file__).resolve().parents[1] / "configs" / "camera_100.toml"
CLASSES = (
    "MEASURED|PHOTO|DATASHEET|PLANT|ESTIMATE|ASSUMED|CHOICE|DERIVED|UNSOURCED"
)
VALUE = re.compile(r"^\s*\w+\s*=")
TAG = re.compile(rf"#\s*({CLASSES}):\s*\S")


def test_every_config_value_has_a_source_class() -> None:
    # Arrange
    lines = CONFIG.read_text().splitlines()
    # Act
    untagged = [ln for ln in lines if VALUE.match(ln) and not TAG.search(ln)]
    # Assert
    assert not untagged, "values without '# CLASS: source':\n" + "\n".join(
        untagged
    )
