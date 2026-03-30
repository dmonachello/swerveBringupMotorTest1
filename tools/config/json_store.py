from __future__ import annotations

"""
NAME
    json_store.py - Generic JSON document store with import/export.

SYNOPSIS
    store = JsonStore()
    warnings = store.load_document(doc_id, root_path, deploy_path, merge_fn)
    payload = store.get_payload(doc_id)

DESCRIPTION
    Provides a generic JSON document store that tracks payloads, dirty flags,
    and file paths. The store is schema-agnostic and relies on caller-supplied
    merge functions for domain-specific behavior.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

from tools.common.json_io import read_json, write_json

BOOL_TRUE = True
BOOL_FALSE = False

EMPTY_STRING = ""


@dataclass
class JsonDocument:
    """
    NAME
        JsonDocument - Stored JSON document metadata.
    """

    doc_id: str
    payload: Dict[str, object]
    dirty: bool
    root_path: Optional[Path]
    deploy_path: Optional[Path]


class JsonStore:
    """
    NAME
        JsonStore - Generic JSON import/export and dirty tracking.

    DESCRIPTION
        Stores JSON documents keyed by caller-provided identifiers. The
        store does not enforce schema rules and does not emit output.
    """

    def __init__(self) -> None:
        """
        NAME
            __init__ - Initialize empty document store.
        """

        self._docs: Dict[str, JsonDocument] = dict()

    def load_document(
        self,
        doc_id: str,
        root_path: Optional[Path],
        deploy_path: Optional[Path],
        merge_fn: Optional[Callable[[Dict[str, object], Dict[str, object]], Tuple[Dict[str, object], List[str]]]],
    ) -> List[str]:
        """
        NAME
            load_document - Load JSON from disk with merge support.

        RETURNS
            List of warnings from the merge function.
        """

        root_payload: Dict[str, object] = dict()
        deploy_payload: Dict[str, object] = dict()
        if root_path is not None and root_path.exists():
            root_payload = read_json(root_path)
        if deploy_path is not None and deploy_path.exists():
            deploy_payload = read_json(deploy_path)
        if not isinstance(root_payload, dict):
            root_payload = dict()
        if not isinstance(deploy_payload, dict):
            deploy_payload = dict()
        warnings: List[str] = list()
        if merge_fn is None:
            merged = dict(deploy_payload)
            merged.update(root_payload)
        else:
            merged, warnings = merge_fn(root_payload, deploy_payload)
        self._docs[doc_id] = JsonDocument(
            doc_id=doc_id,
            payload=merged if isinstance(merged, dict) else dict(),
            dirty=BOOL_FALSE,
            root_path=root_path,
            deploy_path=deploy_path,
        )
        return list(warnings)

    def get_payload(self, doc_id: str) -> Dict[str, object]:
        """
        NAME
            get_payload - Return document payload or empty dict.
        """

        doc = self._docs.get(doc_id)
        if doc is None:
            return dict()
        return doc.payload

    def set_payload(self, doc_id: str, payload: Dict[str, object], dirty: bool = BOOL_FALSE) -> None:
        """
        NAME
            set_payload - Replace payload for a document.
        """

        doc = self._docs.get(doc_id)
        if doc is None:
            self._docs[doc_id] = JsonDocument(
                doc_id=doc_id,
                payload=payload,
                dirty=bool(dirty),
                root_path=None,
                deploy_path=None,
            )
            return
        doc.payload = payload
        doc.dirty = bool(dirty)

    def mark_dirty(self, doc_id: str, dirty: bool = BOOL_TRUE) -> None:
        """
        NAME
            mark_dirty - Set dirty flag for a document.
        """

        doc = self._docs.get(doc_id)
        if doc is None:
            return
        doc.dirty = bool(dirty)

    def dirty_flags(self) -> Dict[str, bool]:
        """
        NAME
            dirty_flags - Return dirty flags by document id.
        """

        flags: Dict[str, bool] = dict()
        for doc_id, doc in self._docs.items():
            flags[doc_id] = bool(doc.dirty)
        return flags

    def save_document(self, doc_id: str, path: Path) -> None:
        """
        NAME
            save_document - Write payload to JSON file.
        """

        payload = self.get_payload(doc_id)
        write_json(path, payload)
