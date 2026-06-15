"""Application configuration."""

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class AppConfig:
    """Global application configuration."""
    project_name: str = "ShoppingReport"
    page_name: str = "Shopping Dashboard"
    culture: str = "en-US"
    compatibility_level: int = 1567
    default_data_directory: str = field(
        default_factory=lambda: (
            (Path(__file__).resolve().parents[1] / "Dataset").as_posix()
        )
    )
    canvas_width: int = 1280
    canvas_height: int = 2200
    log_level: str = "INFO"
    supported_extensions: list[str] = field(default_factory=lambda: [".twb", ".twbx"])


CONFIG = AppConfig()
