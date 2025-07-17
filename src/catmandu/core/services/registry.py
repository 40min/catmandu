import pathlib
from typing import Dict, List

import structlog
import toml
from pydantic import ValidationError

from catmandu.core.models import CattackleConfig

log = structlog.get_logger()


class CattackleRegistry:
    def __init__(self, cattackles_dir: str | None = None):
        self._cattackles_dir = pathlib.Path(
            cattackles_dir if cattackles_dir is not None else "cattackles"
        )
        self._registry: Dict[str, CattackleConfig] = {}
        self._command_map: Dict[str, str] = {}

    def scan(self) -> int:
        log.info("Scanning for cattackles", directory=str(self._cattackles_dir))
        self._registry.clear()
        self._command_map.clear()

        if not self._cattackles_dir.exists():
            log.warning(
                "Cattackles directory not found", directory=str(self._cattackles_dir)
            )
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
                    log.warning(
                        "Duplicate cattackle found, overwriting", name=cattackle_name
                    )

                self._registry[cattackle_name] = config
                for command in config.cattackle.commands:
                    if command in self._command_map:
                        log.warning(
                            "Duplicate command found, overwriting",
                            command=command,
                            new_cattackle=cattackle_name,
                            old_cattackle=self._command_map[command],
                        )
                    self._command_map[command] = cattackle_name
                log.info(
                    "Registered cattackle", name=cattackle_name, path=str(manifest_path)
                )
            except (toml.TomlDecodeError, ValidationError) as e:
                log.error(
                    "Failed to load cattackle manifest",
                    path=str(manifest_path),
                    error=e,
                )

        log.info("Cattackle scan complete", found=len(self._registry))
        return len(self._registry)

    def get_all(self) -> List[CattackleConfig]:
        return list(self._registry.values())
