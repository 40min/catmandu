import pathlib
from typing import Dict, List

import structlog
import toml
from pydantic import ValidationError

from catmandu.core.config import Settings
from catmandu.core.models import CattackleConfig


class CattackleRegistry:
    def __init__(self, config: Settings):
        self._cattackles_dir = pathlib.Path(config.cattackles_dir)
        self._registry: Dict[str, CattackleConfig] = {}

        self.log = structlog.get_logger(self.__class__.__name__)

    def scan(self) -> int:
        self.log.info("Scanning for cattackles", directory=str(self._cattackles_dir))
        self._registry.clear()

        if not self._cattackles_dir.exists():
            self.log.warning("Cattackles directory not found", directory=str(self._cattackles_dir))
            return 0

        files_to_check = []
        if self._cattackles_dir.is_dir():
            files_to_check.extend(self._cattackles_dir.iterdir())
        elif self._cattackles_dir.is_file():
            files_to_check.append(self._cattackles_dir)

        for item in files_to_check:
            manifest_path = None
            if item.is_dir():
                manifest_path = item / "cattackle.toml"
            elif item.is_file() and item.name == "cattackle.toml":
                manifest_path = item

            if not manifest_path or not manifest_path.is_file():
                continue

            try:
                manifest_data = toml.load(manifest_path)
                config = CattackleConfig.model_validate(manifest_data)
                cattackle_name = config.cattackle.name
                if cattackle_name in self._registry:
                    self.log.warning("Duplicate cattackle found, overwriting", name=cattackle_name)

                self._registry[cattackle_name] = config

                self.log.info("Registered cattackle", name=cattackle_name, path=str(manifest_path))
            except (toml.TomlDecodeError, ValidationError) as e:
                self.log.error(
                    "Failed to load cattackle manifest",
                    path=str(manifest_path),
                    error=e,
                )

        self.log.info("Cattackle scan complete", found=len(self._registry))
        return len(self._registry)

    def get_all(self) -> List[CattackleConfig]:
        return list(self._registry.values())

    def find_by_command(self, command: str) -> CattackleConfig | None:
        """Finds a cattackle that provides a given command."""
        for config in self._registry.values():
            if command in config.cattackle.commands:
                return config
        return None
