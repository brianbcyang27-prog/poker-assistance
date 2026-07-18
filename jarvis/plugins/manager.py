"""PluginManager — discover, load, and execute JARVIS plugins."""

import importlib
import importlib.util
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from .models import Plugin, PluginManifest, PluginType

logger = logging.getLogger(__name__)


class PluginManager:
    """Manages the full lifecycle of JARVIS plugins."""

    def __init__(self) -> None:
        self._plugins: Dict[str, Plugin] = {}
        self._modules: Dict[str, Any] = {}

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    async def discover(self, plugin_dirs: List[str]) -> List[Plugin]:
        """Scan *plugin_dirs* for ``plugin.json`` manifests and return found plugins."""
        found: List[Plugin] = []
        for base in plugin_dirs:
            base_path = Path(base)
            if not base_path.is_dir():
                continue
            for child in sorted(base_path.iterdir()):
                manifest_path = child / "plugin.json"
                if not manifest_path.is_file():
                    continue
                try:
                    manifest = self._load_manifest(manifest_path)
                except Exception as exc:
                    logger.warning("Skipping %s: %s", manifest_path, exc)
                    continue
                if manifest.name in self._plugins:
                    continue
                plugin = Plugin(
                    name=manifest.name,
                    version=manifest.version,
                    author=manifest.author,
                    description=manifest.description,
                    plugin_type=manifest.plugin_type,
                    manifest=manifest,
                )
                self._plugins[manifest.name] = plugin
                found.append(plugin)
                logger.info("Discovered plugin %s v%s", manifest.name, manifest.version)
        return found

    # ------------------------------------------------------------------
    # Load / Unload / Reload
    # ------------------------------------------------------------------

    async def load(self, plugin: Plugin) -> bool:
        """Dynamically load a plugin's entry-point module."""
        if plugin.loaded_at is not None:
            return True
        if plugin.manifest is None or plugin.manifest.entry_point is None:
            logger.error("Plugin %s has no manifest or entry_point", plugin.name)
            return False
        search_path = plugin.manifest.entry_point
        # Resolve entry point relative to a known parent directory by
        # walking up from the manifest location.
        entry_dir = Path(search_path)
        if plugin.manifest is not None:
            # Try sibling of plugin.json first
            candidate = Path(search_path)
            if not candidate.is_file():
                candidate = Path(search_path).parent / plugin.manifest.entry_point
                if candidate.is_file():
                    entry_dir = candidate
        try:
            module_name = f"jarvis_plugin_{plugin.name}"
            spec = importlib.util.spec_from_file_location(module_name, str(entry_dir))
            if spec is None or spec.loader is None:
                logger.error("Cannot create module spec for %s", plugin.name)
                return False
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
        except Exception as exc:
            logger.error("Failed to load plugin %s: %s", plugin.name, exc)
            return False
        plugin.module = module
        plugin.loaded_at = time.time()
        self._modules[plugin.name] = module
        logger.info("Loaded plugin %s", plugin.name)
        return True

    async def unload(self, plugin_name: str) -> bool:
        """Unload a previously loaded plugin."""
        plugin = self._plugins.get(plugin_name)
        if plugin is None or plugin.loaded_at is None:
            return False
        module_name = f"jarvis_plugin_{plugin_name}"
        sys.modules.pop(module_name, None)
        plugin.module = None
        plugin.loaded_at = None
        self._modules.pop(plugin_name, None)
        logger.info("Unloaded plugin %s", plugin_name)
        return True

    async def reload(self, plugin_name: str) -> bool:
        """Unload then re-load a plugin."""
        await self.unload(plugin_name)
        plugin = self._plugins.get(plugin_name)
        if plugin is None:
            return False
        return await self.load(plugin)

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    async def get_plugin(self, name: str) -> Optional[Plugin]:
        return self._plugins.get(name)

    async def list_plugins(self) -> List[Plugin]:
        return list(self._plugins.values())

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    async def execute(self, plugin_name: str, method: str, **kwargs: Any) -> Any:
        """Call *method* on the loaded plugin module with *kwargs*."""
        module = self._modules.get(plugin_name)
        if module is None:
            raise RuntimeError(f"Plugin '{plugin_name}' is not loaded")
        func = getattr(module, method, None)
        if func is None or not callable(func):
            raise AttributeError(
                f"Plugin '{plugin_name}' has no callable method '{method}'"
            )
        return await func(**kwargs)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _load_manifest(path: Path) -> PluginManifest:
        raw = json.loads(path.read_text(encoding="utf-8"))
        return PluginManifest.from_dict(raw)
