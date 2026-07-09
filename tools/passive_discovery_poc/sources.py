from __future__ import annotations

"""
NAME
    sources.py - Source-plugin interfaces and built-in registry for passive discovery.

DESCRIPTION
    Defines the common plugin contract used by recorded/live frame sources and
    recorded enrichment sources. Built-in plugins cover the current PoC input
    sources so callers can use one registry-driven model instead of hardcoded
    branches.
"""

from abc import ABC, abstractmethod
from typing import Dict, Iterable, Iterator, List, Mapping, Optional

from tools.passive_discovery_poc.constants import (
    AUTO_PORT_SENTINEL,
    DEFAULT_AUTO_MATCH,
    DEFAULT_CAN_BITRATE,
    DEFAULT_REV_AUTO_MATCH,
    DEFAULT_REV_SERIAL_BAUD,
    DEFAULT_SLCAN_INTERFACE,
    SOURCE_CLASS_ENRICHMENT,
    SOURCE_CLASS_FRAME,
    SOURCE_KIND_CANDUMP,
    SOURCE_KIND_CAPTURE_AUTO,
    SOURCE_KIND_CTRE_HTTP,
    SOURCE_KIND_LIVE_REV_SERIAL,
    SOURCE_KIND_LIVE_SLCAN,
    SOURCE_KIND_PCAPNG,
    SOURCE_KIND_PROFILE,
    SOURCE_KIND_RIO_CONSOLE_LOG,
    SOURCE_KIND_TOPOLOGY,
    SOURCE_MODE_LIVE,
    SOURCE_MODE_RECORDED,
    DEFAULT_CONSOLE_RULES_PATH,
)
from tools.passive_discovery_poc.console_support import parse_console_log
from tools.passive_discovery_poc.enrich_ctre import collect_ctre_enrichment
from tools.passive_discovery_poc.live_sources import (
    iter_live_rev_serial_frames,
    iter_live_slcan_frames,
    resolve_rev_serial_port,
    resolve_slcan_channel,
)
from tools.passive_discovery_poc.models import EnrichmentRecord, NormalizedFrame, SourcePluginInfo
from tools.passive_discovery_poc.profile_support import load_profile_expectations
from tools.passive_discovery_poc.topology_support import load_topology_rows
from tools.passive_discovery_poc.readers import read_candump_text, read_frames, read_socketcan_pcapng


class SourcePluginBase(ABC):
    """
    NAME
        SourcePluginBase - Shared metadata and validation surface for all source plugins.
    """

    @abstractmethod
    def plugin_info(self) -> SourcePluginInfo:
        """
        NAME
            plugin_info - Return stable public metadata for this plugin.
        """

    @abstractmethod
    def validate_config(self, config: Mapping[str, object]) -> Dict[str, object]:
        """
        NAME
            validate_config - Normalize and validate caller configuration.
        """


class RecordedFrameSourcePlugin(SourcePluginBase):
    """
    NAME
        RecordedFrameSourcePlugin - Contract for recorded frame sources.
    """

    @abstractmethod
    def read_frames(self, config: Mapping[str, object]) -> Iterable[NormalizedFrame]:
        """
        NAME
            read_frames - Yield normalized recorded frames.
        """


class LiveFrameSourcePlugin(SourcePluginBase):
    """
    NAME
        LiveFrameSourcePlugin - Contract for live frame sources.
    """

    @abstractmethod
    def iter_live_frames(self, config: Mapping[str, object], stop_event) -> Iterator[NormalizedFrame]:
        """
        NAME
            iter_live_frames - Yield normalized live frames until completion or stop.
        """


class RecordedEnrichmentSourcePlugin(SourcePluginBase):
    """
    NAME
        RecordedEnrichmentSourcePlugin - Contract for bounded enrichment sources.
    """

    @abstractmethod
    def collect(self, config: Mapping[str, object]) -> EnrichmentRecord:
        """
        NAME
            collect - Collect one normalized enrichment record.
        """


class LiveEnrichmentSourcePlugin(SourcePluginBase):
    """
    NAME
        LiveEnrichmentSourcePlugin - Contract for live enrichment streams.
    """

    @abstractmethod
    def iter_enrichment_records(self, config: Mapping[str, object], stop_event) -> Iterator[EnrichmentRecord]:
        """
        NAME
            iter_enrichment_records - Yield enrichment records until completion or stop.
        """


class SourceRegistry:
    """
    NAME
        SourceRegistry - Registry for source plugins keyed by stable plugin id.
    """

    def __init__(self) -> None:
        self._plugins: Dict[str, SourcePluginBase] = {}

    def register(self, plugin: SourcePluginBase) -> None:
        """
        NAME
            register - Add or replace one source plugin by id.
        """
        info = plugin.plugin_info()
        self._plugins[info.plugin_id] = plugin

    def get(self, plugin_id: str) -> SourcePluginBase:
        """
        NAME
            get - Resolve one registered source plugin.
        """
        try:
            return self._plugins[plugin_id]
        except KeyError as exc:
            raise ValueError(f"unknown passive discovery source plugin: {plugin_id}") from exc

    def list_plugins(
        self,
        *,
        source_class: str = "",
        source_mode: str = "",
    ) -> List[SourcePluginInfo]:
        """
        NAME
            list_plugins - List registered plugins, optionally filtered by class or mode.
        """
        result: List[SourcePluginInfo] = []
        for plugin in self._plugins.values():
            info = plugin.plugin_info()
            if source_class and info.source_class != source_class:
                continue
            if source_mode and info.source_mode != source_mode:
                continue
            result.append(info)
        return sorted(result, key=lambda item: item.plugin_id)


class _BasePlugin(SourcePluginBase):
    """
    NAME
        _BasePlugin - Small helper for stable plugin metadata.
    """

    def __init__(self, *, info: SourcePluginInfo) -> None:
        self._info = info

    def plugin_info(self) -> SourcePluginInfo:
        return self._info


class _RecordedPcapngPlugin(_BasePlugin, RecordedFrameSourcePlugin):
    def __init__(self) -> None:
        super().__init__(
            info=SourcePluginInfo(
                plugin_id=SOURCE_KIND_PCAPNG,
                display_name="SocketCAN PCAPNG",
                source_class=SOURCE_CLASS_FRAME,
                source_mode=SOURCE_MODE_RECORDED,
                description="Recorded SocketCAN PCAPNG capture.",
            )
        )

    def validate_config(self, config: Mapping[str, object]) -> Dict[str, object]:
        path = str(config.get("path", "")).strip()
        if not path:
            raise ValueError("pcapng source requires path")
        return {"path": path}

    def read_frames(self, config: Mapping[str, object]) -> Iterable[NormalizedFrame]:
        resolved = self.validate_config(config)
        return read_socketcan_pcapng(str(resolved["path"]))


class _RecordedCandumpPlugin(_BasePlugin, RecordedFrameSourcePlugin):
    def __init__(self) -> None:
        super().__init__(
            info=SourcePluginInfo(
                plugin_id=SOURCE_KIND_CANDUMP,
                display_name="candump/text",
                source_class=SOURCE_CLASS_FRAME,
                source_mode=SOURCE_MODE_RECORDED,
                description="Recorded candump or simple text capture.",
            )
        )

    def validate_config(self, config: Mapping[str, object]) -> Dict[str, object]:
        path = str(config.get("path", "")).strip()
        if not path:
            raise ValueError("candump source requires path")
        return {"path": path}

    def read_frames(self, config: Mapping[str, object]) -> Iterable[NormalizedFrame]:
        resolved = self.validate_config(config)
        return read_candump_text(str(resolved["path"]))


class _RecordedAutoCapturePlugin(_BasePlugin, RecordedFrameSourcePlugin):
    def __init__(self) -> None:
        super().__init__(
            info=SourcePluginInfo(
                plugin_id=SOURCE_KIND_CAPTURE_AUTO,
                display_name="Auto capture reader",
                source_class=SOURCE_CLASS_FRAME,
                source_mode=SOURCE_MODE_RECORDED,
                description="Recorded capture reader that dispatches by suffix.",
            )
        )

    def validate_config(self, config: Mapping[str, object]) -> Dict[str, object]:
        path = str(config.get("path", "")).strip()
        if not path:
            raise ValueError("capture_auto source requires path")
        return {"path": path}

    def read_frames(self, config: Mapping[str, object]) -> Iterable[NormalizedFrame]:
        resolved = self.validate_config(config)
        return read_frames(str(resolved["path"]))


class _LiveSlcanPlugin(_BasePlugin, LiveFrameSourcePlugin):
    def __init__(self) -> None:
        super().__init__(
            info=SourcePluginInfo(
                plugin_id=SOURCE_KIND_LIVE_SLCAN,
                display_name="Live slcan",
                source_class=SOURCE_CLASS_FRAME,
                source_mode=SOURCE_MODE_LIVE,
                description="Live passive slcan or CANable frame source.",
            )
        )

    def validate_config(self, config: Mapping[str, object]) -> Dict[str, object]:
        channel = str(config.get("channel", "")).strip()
        auto_match = str(config.get("auto_match", DEFAULT_AUTO_MATCH)).strip() or DEFAULT_AUTO_MATCH
        bitrate = int(config.get("bitrate", DEFAULT_CAN_BITRATE))
        interface = str(config.get("interface", DEFAULT_SLCAN_INTERFACE)).strip() or DEFAULT_SLCAN_INTERFACE
        duration_sec = config.get("duration_sec")
        diagnostics = config.get("diagnostics")
        resolved_channel = channel or resolve_slcan_channel(explicit_channel="", auto_match=auto_match)
        return {
            "channel": resolved_channel,
            "auto_match": auto_match,
            "bitrate": bitrate,
            "interface": interface,
            "duration_sec": duration_sec,
            "diagnostics": diagnostics,
        }

    def iter_live_frames(self, config: Mapping[str, object], stop_event) -> Iterator[NormalizedFrame]:
        resolved = self.validate_config(config)
        return iter_live_slcan_frames(
            channel=str(resolved["channel"]),
            bitrate=int(resolved["bitrate"]),
            duration_sec=resolved.get("duration_sec"),
            interface=str(resolved["interface"]),
            stop_event=stop_event,
            diagnostics=resolved.get("diagnostics"),
        )


class _LiveRevSerialPlugin(_BasePlugin, LiveFrameSourcePlugin):
    def __init__(self) -> None:
        super().__init__(
            info=SourcePluginInfo(
                plugin_id=SOURCE_KIND_LIVE_REV_SERIAL,
                display_name="Live REV serial bridge",
                source_class=SOURCE_CLASS_FRAME,
                source_mode=SOURCE_MODE_LIVE,
                description="Live passive REV USB bridge frame source.",
            )
        )

    def validate_config(self, config: Mapping[str, object]) -> Dict[str, object]:
        port = str(config.get("port", "")).strip()
        auto_match = str(config.get("auto_match", DEFAULT_REV_AUTO_MATCH)).strip() or DEFAULT_REV_AUTO_MATCH
        resolved_port = resolve_rev_serial_port(explicit_port=port or AUTO_PORT_SENTINEL, auto_match=auto_match)
        baudrate = int(config.get("baudrate", DEFAULT_REV_SERIAL_BAUD))
        duration_sec = config.get("duration_sec")
        diagnostics = config.get("diagnostics")
        return {
            "port": resolved_port,
            "auto_match": auto_match,
            "baudrate": baudrate,
            "duration_sec": duration_sec,
            "diagnostics": diagnostics,
        }

    def iter_live_frames(self, config: Mapping[str, object], stop_event) -> Iterator[NormalizedFrame]:
        resolved = self.validate_config(config)
        return iter_live_rev_serial_frames(
            port=str(resolved["port"]),
            baudrate=int(resolved["baudrate"]),
            duration_sec=resolved.get("duration_sec"),
            stop_event=stop_event,
            diagnostics=resolved.get("diagnostics"),
        )


class _RecordedCtreHttpPlugin(_BasePlugin, RecordedEnrichmentSourcePlugin):
    def __init__(self) -> None:
        super().__init__(
            info=SourcePluginInfo(
                plugin_id=SOURCE_KIND_CTRE_HTTP,
                display_name="CTRE HTTP enrichment",
                source_class=SOURCE_CLASS_ENRICHMENT,
                source_mode=SOURCE_MODE_RECORDED,
                description="Point-in-time CTRE diagnostic HTTP inventory and self-test enrichment.",
            )
        )

    def validate_config(self, config: Mapping[str, object]) -> Dict[str, object]:
        base_url = str(config.get("base_url", "")).strip()
        if not base_url:
            raise ValueError("ctre_http source requires base_url")
        return {"base_url": base_url}

    def collect(self, config: Mapping[str, object]) -> EnrichmentRecord:
        resolved = self.validate_config(config)
        device_enrichment, warnings = collect_ctre_enrichment(str(resolved["base_url"]))
        return EnrichmentRecord(
            plugin_id=self.plugin_info().plugin_id,
            source_class=self.plugin_info().source_class,
            source_mode=self.plugin_info().source_mode,
            metadata={"baseUrl": str(resolved["base_url"])},
            device_enrichment=dict(device_enrichment),
            warnings=tuple(warnings),
        )


class _RecordedProfilePlugin(_BasePlugin, RecordedEnrichmentSourcePlugin):
    def __init__(self) -> None:
        super().__init__(
            info=SourcePluginInfo(
                plugin_id=SOURCE_KIND_PROFILE,
                display_name="Bringup profile",
                source_class=SOURCE_CLASS_ENRICHMENT,
                source_mode=SOURCE_MODE_RECORDED,
                description="Bringup profile and expected inventory enrichment.",
            )
        )

    def validate_config(self, config: Mapping[str, object]) -> Dict[str, object]:
        profile_path = str(config.get("profile_path", "")).strip()
        if not profile_path:
            raise ValueError("profile source requires profile_path")
        profile_name = str(config.get("profile_name", "")).strip()
        return {"profile_path": profile_path, "profile_name": profile_name}

    def collect(self, config: Mapping[str, object]) -> EnrichmentRecord:
        resolved = self.validate_config(config)
        profile_name, expected_rows = load_profile_expectations(
            profile_path=str(resolved["profile_path"]),
            profile_name=str(resolved["profile_name"]),
        )
        return EnrichmentRecord(
            plugin_id=self.plugin_info().plugin_id,
            source_class=self.plugin_info().source_class,
            source_mode=self.plugin_info().source_mode,
            metadata={
                "profilePath": str(resolved["profile_path"]),
                "profileName": profile_name,
            },
            expected_rows=dict(expected_rows),
        )


class _RecordedTopologyPlugin(_BasePlugin, RecordedEnrichmentSourcePlugin):
    def __init__(self) -> None:
        super().__init__(
            info=SourcePluginInfo(
                plugin_id=SOURCE_KIND_TOPOLOGY,
                display_name="Bringup topology",
                source_class=SOURCE_CLASS_ENRICHMENT,
                source_mode=SOURCE_MODE_RECORDED,
                description="Bringup profile topology and device-layout enrichment.",
            )
        )

    def validate_config(self, config: Mapping[str, object]) -> Dict[str, object]:
        profile_path = str(config.get("profile_path", "")).strip()
        if not profile_path:
            raise ValueError("topology source requires profile_path")
        profile_name = str(config.get("profile_name", "")).strip()
        return {"profile_path": profile_path, "profile_name": profile_name}

    def collect(self, config: Mapping[str, object]) -> EnrichmentRecord:
        resolved = self.validate_config(config)
        profile_name, device_enrichment, evidence_records, metadata = load_topology_rows(
            profile_path=str(resolved["profile_path"]),
            profile_name=str(resolved["profile_name"]),
        )
        return EnrichmentRecord(
            plugin_id=self.plugin_info().plugin_id,
            source_class=self.plugin_info().source_class,
            source_mode=self.plugin_info().source_mode,
            metadata={**metadata, "profileName": profile_name},
            device_enrichment=dict(device_enrichment),
            evidence_records=tuple(dict(row) for row in evidence_records),
        )


class _RecordedRioConsoleLogPlugin(_BasePlugin, RecordedEnrichmentSourcePlugin):
    def __init__(self) -> None:
        super().__init__(
            info=SourcePluginInfo(
                plugin_id=SOURCE_KIND_RIO_CONSOLE_LOG,
                display_name="roboRIO console log",
                source_class=SOURCE_CLASS_ENRICHMENT,
                source_mode=SOURCE_MODE_RECORDED,
                description="Saved roboRIO console log parsed into structured CAN-device evidence.",
            )
        )

    def validate_config(self, config: Mapping[str, object]) -> Dict[str, object]:
        log_path = str(config.get("log_path", "")).strip()
        if not log_path:
            raise ValueError("rio_console_log source requires log_path")
        profile_path = str(config.get("profile_path", "")).strip()
        profile_name = str(config.get("profile_name", "")).strip()
        rules_path = str(config.get("rules_path", DEFAULT_CONSOLE_RULES_PATH)).strip() or DEFAULT_CONSOLE_RULES_PATH
        return {
            "log_path": log_path,
            "profile_path": profile_path,
            "profile_name": profile_name,
            "rules_path": rules_path,
        }

    def collect(self, config: Mapping[str, object]) -> EnrichmentRecord:
        resolved = self.validate_config(config)
        evidence_records, metadata, warnings = parse_console_log(
            log_path=str(resolved["log_path"]),
            profile_path=str(resolved["profile_path"]),
            profile_name=str(resolved["profile_name"]),
            rules_path=str(resolved["rules_path"]),
        )
        return EnrichmentRecord(
            plugin_id=self.plugin_info().plugin_id,
            source_class=self.plugin_info().source_class,
            source_mode=self.plugin_info().source_mode,
            metadata=dict(metadata),
            evidence_records=tuple(dict(row) for row in evidence_records),
            warnings=tuple(warnings),
        )


_DEFAULT_SOURCE_REGISTRY: Optional[SourceRegistry] = None


def default_source_registry() -> SourceRegistry:
    """
    NAME
        default_source_registry - Return the process-wide registry with built-in plugins.
    """
    global _DEFAULT_SOURCE_REGISTRY
    if _DEFAULT_SOURCE_REGISTRY is None:
        registry = SourceRegistry()
        registry.register(_RecordedPcapngPlugin())
        registry.register(_RecordedCandumpPlugin())
        registry.register(_RecordedAutoCapturePlugin())
        registry.register(_LiveSlcanPlugin())
        registry.register(_LiveRevSerialPlugin())
        registry.register(_RecordedCtreHttpPlugin())
        registry.register(_RecordedProfilePlugin())
        registry.register(_RecordedTopologyPlugin())
        registry.register(_RecordedRioConsoleLogPlugin())
        _DEFAULT_SOURCE_REGISTRY = registry
    return _DEFAULT_SOURCE_REGISTRY
