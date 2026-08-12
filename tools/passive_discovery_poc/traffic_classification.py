from __future__ import annotations

"""
NAME
    traffic_classification.py - Shared observed-traffic classification helpers.

DESCRIPTION
    Separates canonical device-identity contribution from non-device traffic
    families so host-side consumers can preserve all observed traffic without
    inventing fake physical devices.
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

from tools.can_nt.can_frc_defs import CTRE_J1939_CONTROL_PF
from tools.passive_discovery_poc.constants import (
    CTRE_DEVICE_TYPE_CANCODER_PASSIVE,
    CTRE_DEVICE_TYPE_PIGEON_PASSIVE,
    CTRE_MANUFACTURER,
    CTRE_MOTOR_CONTROLLER_REFERENCE_API_CLASS,
    CTRE_MOTOR_CONTROLLER_REFERENCE_API_INDEX,
    CTRE_MOTOR_CONTROLLER_REFERENCE_API_INDEX_SECONDARY,
    DEVICE_TYPE_BROADCAST,
    ROLE_SHARED_BUS_CONTROL,
    ROLE_UNKNOWN,
    REV_MANUFACTURER,
)
from tools.passive_discovery_poc.models import NormalizedFrame

TRAFFIC_KIND_DEVICE_IDENTITY = "deviceIdentity"
TRAFFIC_KIND_NON_DEVICE_FAMILY = "nonDeviceFamily"
TRAFFIC_KIND_SUPPORTING_REFERENCE = "supportingReference"
TRAFFIC_KIND_UNKNOWN = "unknown"

IDENTITY_DISPOSITION_DEFINITE = "definite"
IDENTITY_DISPOSITION_SUPPORTING = "supporting"
IDENTITY_DISPOSITION_NON_DEVICE = "nonDevice"

NON_DEVICE_REASON_SHARED_BUS_CONTROL = "sharedBusControl"
NON_DEVICE_REASON_BROADCAST_SYSTEM = "broadcastSystem"
NON_DEVICE_REASON_CTRE_PASSIVE_ALIAS_REFERENCE = "ctrePassiveAliasReference"
NON_DEVICE_REASON_CTRE_REFERENCE_FAMILY = "ctreReferenceFamily"
NON_DEVICE_REASON_CTRE_DIAGNOSTIC_ENUMERATION = "ctreDiagnosticEnumeration"
NON_DEVICE_REASON_CTRE_UNVERIFIED_FAMILY = "ctreUnverifiedFamily"
NON_DEVICE_REASON_REV_UNVERIFIED_FAMILY = "revUnverifiedFamily"
NON_DEVICE_REASON_UNKNOWN = "unknown"

KEY_MANUFACTURER = "manufacturer"
KEY_DEVICE_TYPE = "deviceType"
KEY_DEVICE_ID = "deviceId"
KEY_API_CLASS = "apiClass"
KEY_API_INDEX = "apiIndex"
KEY_PF = "pf"
KEY_PS = "ps"
KEY_TRAFFIC_KIND = "trafficKind"
KEY_TRAFFIC_ROLE = "trafficRole"
KEY_REASON = "reason"
KEY_RAW_IDENTITY = "rawIdentity"
KEY_CANONICAL_IDENTITY = "canonicalIdentity"
KEY_FAMILY_KEY = "familyKey"
KEY_IDENTITY_DISPOSITION = "identityDisposition"
KEY_SUPPORTS_EXISTING_DEVICE_IDENTITY = "supportsExistingDeviceIdentity"

INT_SHIFT_PF = 16
INT_SHIFT_PS = 8
BYTE_MASK = 0xFF
CTRE_DIAGNOSTIC_ENUMERATION_API_CLASS = 62
CTRE_PIGEON_PRIMARY_API_CLASS = 11
CTRE_PIGEON_PRIMARY_API_INDEX = 4
CTRE_CANCODER_PRIMARY_API_CLASS = 11
CTRE_CANCODER_PRIMARY_API_INDEX = 3
CTRE_MOTOR_PRIMARY_API_CLASS = 11
CTRE_MOTOR_PRIMARY_API_INDEX = 1
CTRE_MOTOR_SECONDARY_IDENTITY_API_INDEX = 7
CTRE_POWER_STATUS_API_CLASS = 5
CTRE_POWER_STATUS_API_INDEX_BRANCH_CURRENTS_A = 0
CTRE_POWER_STATUS_API_INDEX_BRANCH_CURRENTS_B = 1
CTRE_POWER_STATUS_API_INDEX_BRANCH_CURRENTS_C = 2
CTRE_POWER_STATUS_API_INDEX_STICKY_FAULTS = 9
CTRE_POWER_STATUS_API_INDEX_STATUS = 13
CTRE_IDENTITY_DEVICE_TYPE_MOTOR = 2
CTRE_IDENTITY_DEVICE_TYPE_PIGEON = 4
CTRE_IDENTITY_DEVICE_TYPE_CANCODER = 7
CTRE_IDENTITY_DEVICE_TYPE_POWER = 8
CTRE_MOTOR_DEFINITE_API_INDEXES = (
    CTRE_MOTOR_PRIMARY_API_INDEX,
    CTRE_MOTOR_SECONDARY_IDENTITY_API_INDEX,
)
CTRE_POWER_DEFINITE_API_INDEXES = (
    CTRE_POWER_STATUS_API_INDEX_BRANCH_CURRENTS_A,
    CTRE_POWER_STATUS_API_INDEX_BRANCH_CURRENTS_B,
    CTRE_POWER_STATUS_API_INDEX_BRANCH_CURRENTS_C,
    CTRE_POWER_STATUS_API_INDEX_STICKY_FAULTS,
    CTRE_POWER_STATUS_API_INDEX_STATUS,
)
REV_IDENTITY_DEVICE_TYPE_MOTOR = 2
REV_STATUS_API_CLASS = 46
REV_STATUS_API_INDEX_PRIMARY = 0
REV_STATUS_API_INDEX_SECONDARY = 1
REV_STATUS_API_INDEX_FAULTS = 2
REV_HEARTBEAT_API_CLASS = 47
REV_HEARTBEAT_API_INDEX = 0
REV_STATUS_DEFINITE_API_INDEXES = (
    REV_STATUS_API_INDEX_PRIMARY,
    REV_STATUS_API_INDEX_SECONDARY,
    REV_STATUS_API_INDEX_FAULTS,
)


@dataclass(frozen=True)
class DeviceIdentityRule:
    """
    NAME
        DeviceIdentityRule - Exact observed signature that can define a physical device.
    """

    manufacturer: int
    device_type: int
    api_class: int
    api_indexes: Tuple[int, ...]

    def matches(
        self,
        *,
        manufacturer: int,
        device_type: int,
        api_class: Optional[int],
        api_index: Optional[int],
    ) -> bool:
        """
        NAME
            matches - Return true when an observed frame satisfies this rule.
        """
        return (
            manufacturer == self.manufacturer
            and device_type == self.device_type
            and api_class == self.api_class
            and api_index in self.api_indexes
        )


CTRE_DEVICE_DEFINING_TRAFFIC_RULES = (
    DeviceIdentityRule(
        CTRE_MANUFACTURER,
        CTRE_IDENTITY_DEVICE_TYPE_MOTOR,
        CTRE_MOTOR_PRIMARY_API_CLASS,
        CTRE_MOTOR_DEFINITE_API_INDEXES,
    ),
    DeviceIdentityRule(
        CTRE_MANUFACTURER,
        CTRE_IDENTITY_DEVICE_TYPE_PIGEON,
        CTRE_PIGEON_PRIMARY_API_CLASS,
        (CTRE_PIGEON_PRIMARY_API_INDEX,),
    ),
    DeviceIdentityRule(
        CTRE_MANUFACTURER,
        CTRE_IDENTITY_DEVICE_TYPE_CANCODER,
        CTRE_CANCODER_PRIMARY_API_CLASS,
        (CTRE_CANCODER_PRIMARY_API_INDEX,),
    ),
    DeviceIdentityRule(
        CTRE_MANUFACTURER,
        CTRE_IDENTITY_DEVICE_TYPE_POWER,
        CTRE_POWER_STATUS_API_CLASS,
        CTRE_POWER_DEFINITE_API_INDEXES,
    ),
)

REV_DEVICE_DEFINING_TRAFFIC_RULES = (
    DeviceIdentityRule(
        REV_MANUFACTURER,
        REV_IDENTITY_DEVICE_TYPE_MOTOR,
        REV_STATUS_API_CLASS,
        REV_STATUS_DEFINITE_API_INDEXES,
    ),
    DeviceIdentityRule(
        REV_MANUFACTURER,
        REV_IDENTITY_DEVICE_TYPE_MOTOR,
        REV_HEARTBEAT_API_CLASS,
        (REV_HEARTBEAT_API_INDEX,),
    ),
)


def _build_device_identity_classification(
    *,
    raw_identity: Tuple[int, int, int],
    canonical_identity: Optional[Tuple[int, int, int]],
    api_class: Optional[int],
    api_index: Optional[int],
    pf: int,
    ps: int,
) -> ObservedTrafficClassification:
    """
    NAME
        _build_device_identity_classification - Build one definite device-identity result.
    """
    return ObservedTrafficClassification(
        traffic_kind=TRAFFIC_KIND_DEVICE_IDENTITY,
        traffic_role=ROLE_UNKNOWN,
        contributes_to_device_identity=True,
        supports_existing_device_identity=False,
        identity_disposition=IDENTITY_DISPOSITION_DEFINITE,
        reason=TRAFFIC_KIND_DEVICE_IDENTITY,
        family_key=_build_family_key(
            raw_identity=raw_identity,
            api_class=api_class,
            api_index=api_index,
            traffic_kind=TRAFFIC_KIND_DEVICE_IDENTITY,
            pf=pf,
            ps=ps,
        ),
        raw_identity=raw_identity,
        canonical_identity=canonical_identity,
        api_class=api_class,
        api_index=api_index,
        pf=pf,
        ps=ps,
    )


def _build_supporting_reference_classification(
    *,
    raw_identity: Tuple[int, int, int],
    canonical_identity: Optional[Tuple[int, int, int]],
    api_class: Optional[int],
    api_index: Optional[int],
    pf: int,
    ps: int,
    reason: str,
) -> ObservedTrafficClassification:
    """
    NAME
        _build_supporting_reference_classification - Build one supporting/reference result.
    """
    return ObservedTrafficClassification(
        traffic_kind=TRAFFIC_KIND_SUPPORTING_REFERENCE,
        traffic_role=ROLE_UNKNOWN,
        contributes_to_device_identity=False,
        supports_existing_device_identity=True,
        identity_disposition=IDENTITY_DISPOSITION_SUPPORTING,
        reason=reason,
        family_key=_build_family_key(
            raw_identity=raw_identity,
            api_class=api_class,
            api_index=api_index,
            traffic_kind=TRAFFIC_KIND_SUPPORTING_REFERENCE,
            pf=pf,
            ps=ps,
        ),
        raw_identity=raw_identity,
        canonical_identity=canonical_identity,
        api_class=api_class,
        api_index=api_index,
        pf=pf,
        ps=ps,
    )


def _canonical_identity_matches_rule(
    canonical_identity: Tuple[int, int, int],
    api_class: Optional[int],
    api_index: Optional[int],
    rules: Tuple[DeviceIdentityRule, ...],
) -> bool:
    """
    NAME
        _canonical_identity_matches_rule - Return true when one canonical family is device-defining.
    """
    canonical_manufacturer, canonical_device_type, _device_id = canonical_identity
    return any(
        rule.matches(
            manufacturer=canonical_manufacturer,
            device_type=canonical_device_type,
            api_class=api_class,
            api_index=api_index,
        )
        for rule in rules
    )


def _ctre_canonical_identity_is_definite(
    canonical_identity: Tuple[int, int, int],
    api_class: Optional[int],
    api_index: Optional[int],
) -> bool:
    """
    NAME
        _ctre_canonical_identity_is_definite - Return true for verified CTRE device-defining traffic.
    """
    return _canonical_identity_matches_rule(
        canonical_identity,
        api_class,
        api_index,
        CTRE_DEVICE_DEFINING_TRAFFIC_RULES,
    )


def _rev_canonical_identity_is_definite(
    canonical_identity: Tuple[int, int, int],
    api_class: Optional[int],
    api_index: Optional[int],
) -> bool:
    """
    NAME
        _rev_canonical_identity_is_definite - Return true for verified REV device-defining traffic.
    """
    return _canonical_identity_matches_rule(
        canonical_identity,
        api_class,
        api_index,
        REV_DEVICE_DEFINING_TRAFFIC_RULES,
    )


@dataclass(frozen=True)
class ObservedTrafficClassification:
    """
    NAME
        ObservedTrafficClassification - Shared classification result for one observed frame.
    """

    traffic_kind: str
    traffic_role: str
    contributes_to_device_identity: bool
    supports_existing_device_identity: bool
    identity_disposition: str
    reason: str
    family_key: str
    raw_identity: Tuple[int, int, int]
    canonical_identity: Optional[Tuple[int, int, int]]
    api_class: Optional[int]
    api_index: Optional[int]
    pf: int
    ps: int

    def as_non_device_payload(self) -> Dict[str, Any]:
        """
        NAME
            as_non_device_payload - Return stable JSON-ready non-device traffic metadata.
        """
        payload: Dict[str, Any] = {
            KEY_FAMILY_KEY: self.family_key,
            KEY_MANUFACTURER: int(self.raw_identity[0]),
            KEY_TRAFFIC_KIND: self.traffic_kind,
            KEY_TRAFFIC_ROLE: self.traffic_role,
            KEY_IDENTITY_DISPOSITION: self.identity_disposition,
            KEY_SUPPORTS_EXISTING_DEVICE_IDENTITY: bool(self.supports_existing_device_identity),
            KEY_REASON: self.reason,
            KEY_RAW_IDENTITY: {
                KEY_MANUFACTURER: int(self.raw_identity[0]),
                KEY_DEVICE_TYPE: int(self.raw_identity[1]),
                KEY_DEVICE_ID: int(self.raw_identity[2]),
            },
            KEY_PF: int(self.pf),
            KEY_PS: int(self.ps),
        }
        if self.api_class is not None:
            payload[KEY_API_CLASS] = int(self.api_class)
        if self.api_index is not None:
            payload[KEY_API_INDEX] = int(self.api_index)
        if self.canonical_identity is not None:
            payload[KEY_CANONICAL_IDENTITY] = {
                KEY_MANUFACTURER: int(self.canonical_identity[0]),
                KEY_DEVICE_TYPE: int(self.canonical_identity[1]),
                KEY_DEVICE_ID: int(self.canonical_identity[2]),
            }
        return payload


def classify_observed_frame(
    frame: NormalizedFrame,
    raw_identity: Tuple[int, int, int],
) -> ObservedTrafficClassification:
    """
    NAME
        classify_observed_frame - Classify one observed frame for identity contribution.

    DESCRIPTION
        Uses the normalized frame as the canonical identity candidate, while the
        raw decoded tuple remains evidence. Some traffic families, such as CTRE
        shared-bus control or broadcast traffic, are retained as non-device
        families instead of being promoted into physical device inventory.
    """
    raw_manufacturer, raw_device_type, raw_device_id = raw_identity
    pf = (int(frame.can_id) >> INT_SHIFT_PF) & BYTE_MASK
    ps = (int(frame.can_id) >> INT_SHIFT_PS) & BYTE_MASK

    canonical_identity: Optional[Tuple[int, int, int]] = None
    if (
        frame.manufacturer is not None
        and frame.device_type is not None
        and frame.device_id is not None
    ):
        canonical_identity = (
            int(frame.manufacturer),
            int(frame.device_type),
            int(frame.device_id),
        )

    if raw_manufacturer == CTRE_MANUFACTURER and pf == CTRE_J1939_CONTROL_PF:
        return ObservedTrafficClassification(
            traffic_kind=TRAFFIC_KIND_NON_DEVICE_FAMILY,
            traffic_role=ROLE_SHARED_BUS_CONTROL,
            contributes_to_device_identity=False,
            supports_existing_device_identity=False,
            identity_disposition=IDENTITY_DISPOSITION_NON_DEVICE,
            reason=NON_DEVICE_REASON_SHARED_BUS_CONTROL,
            family_key=_build_family_key(
                raw_identity=raw_identity,
                api_class=frame.api_class,
                api_index=frame.api_index,
                traffic_kind=TRAFFIC_KIND_NON_DEVICE_FAMILY,
                pf=pf,
                ps=ps,
            ),
            raw_identity=raw_identity,
            canonical_identity=canonical_identity,
            api_class=frame.api_class,
            api_index=frame.api_index,
            pf=pf,
            ps=ps,
        )

    if raw_device_type == DEVICE_TYPE_BROADCAST:
        return ObservedTrafficClassification(
            traffic_kind=TRAFFIC_KIND_NON_DEVICE_FAMILY,
            traffic_role=ROLE_SHARED_BUS_CONTROL,
            contributes_to_device_identity=False,
            supports_existing_device_identity=False,
            identity_disposition=IDENTITY_DISPOSITION_NON_DEVICE,
            reason=NON_DEVICE_REASON_BROADCAST_SYSTEM,
            family_key=_build_family_key(
                raw_identity=raw_identity,
                api_class=frame.api_class,
                api_index=frame.api_index,
                traffic_kind=TRAFFIC_KIND_NON_DEVICE_FAMILY,
                pf=pf,
                ps=ps,
            ),
            raw_identity=raw_identity,
            canonical_identity=canonical_identity,
            api_class=frame.api_class,
            api_index=frame.api_index,
            pf=pf,
            ps=ps,
        )

    if (
        raw_manufacturer == CTRE_MANUFACTURER
        and raw_device_type == CTRE_DEVICE_TYPE_PIGEON_PASSIVE
        and frame.api_class == CTRE_PIGEON_PRIMARY_API_CLASS
        and frame.api_index == CTRE_PIGEON_PRIMARY_API_INDEX
        and canonical_identity is not None
    ):
        return _build_device_identity_classification(
            raw_identity=raw_identity,
            canonical_identity=canonical_identity,
            api_class=frame.api_class,
            api_index=frame.api_index,
            pf=pf,
            ps=ps,
        )

    if (
        raw_manufacturer == CTRE_MANUFACTURER
        and raw_device_type == CTRE_DEVICE_TYPE_CANCODER_PASSIVE
        and frame.api_class == CTRE_CANCODER_PRIMARY_API_CLASS
        and frame.api_index == CTRE_CANCODER_PRIMARY_API_INDEX
        and canonical_identity is not None
    ):
        return _build_device_identity_classification(
            raw_identity=raw_identity,
            canonical_identity=canonical_identity,
            api_class=frame.api_class,
            api_index=frame.api_index,
            pf=pf,
            ps=ps,
        )

    if (
        raw_manufacturer == CTRE_MANUFACTURER
        and frame.api_class == CTRE_DIAGNOSTIC_ENUMERATION_API_CLASS
    ):
        return _build_supporting_reference_classification(
            raw_identity=raw_identity,
            canonical_identity=canonical_identity,
            api_class=frame.api_class,
            api_index=frame.api_index,
            pf=pf,
            ps=ps,
            reason=NON_DEVICE_REASON_CTRE_DIAGNOSTIC_ENUMERATION,
        )

    if (
        raw_manufacturer == CTRE_MANUFACTURER
        and raw_device_type in (
            CTRE_DEVICE_TYPE_CANCODER_PASSIVE,
            CTRE_DEVICE_TYPE_PIGEON_PASSIVE,
        )
    ):
        return _build_supporting_reference_classification(
            raw_identity=raw_identity,
            canonical_identity=canonical_identity,
            api_class=frame.api_class,
            api_index=frame.api_index,
            pf=pf,
            ps=ps,
            reason=NON_DEVICE_REASON_CTRE_PASSIVE_ALIAS_REFERENCE,
        )

    if (
        raw_manufacturer == CTRE_MANUFACTURER
        and frame.api_class == CTRE_MOTOR_CONTROLLER_REFERENCE_API_CLASS
        and frame.api_index in (
            CTRE_MOTOR_CONTROLLER_REFERENCE_API_INDEX,
            CTRE_MOTOR_CONTROLLER_REFERENCE_API_INDEX_SECONDARY,
        )
    ):
        return _build_supporting_reference_classification(
            raw_identity=raw_identity,
            canonical_identity=canonical_identity,
            api_class=frame.api_class,
            api_index=frame.api_index,
            pf=pf,
            ps=ps,
            reason=NON_DEVICE_REASON_CTRE_REFERENCE_FAMILY,
        )

    if canonical_identity is not None:
        if raw_manufacturer == CTRE_MANUFACTURER:
            if _ctre_canonical_identity_is_definite(
                canonical_identity,
                frame.api_class,
                frame.api_index,
            ):
                return _build_device_identity_classification(
                    raw_identity=raw_identity,
                    canonical_identity=canonical_identity,
                    api_class=frame.api_class,
                    api_index=frame.api_index,
                    pf=pf,
                    ps=ps,
                )
            return _build_supporting_reference_classification(
                raw_identity=raw_identity,
                canonical_identity=canonical_identity,
                api_class=frame.api_class,
                api_index=frame.api_index,
                pf=pf,
                ps=ps,
                reason=NON_DEVICE_REASON_CTRE_UNVERIFIED_FAMILY,
            )
        if raw_manufacturer == REV_MANUFACTURER:
            if _rev_canonical_identity_is_definite(
                canonical_identity,
                frame.api_class,
                frame.api_index,
            ):
                return _build_device_identity_classification(
                    raw_identity=raw_identity,
                    canonical_identity=canonical_identity,
                    api_class=frame.api_class,
                    api_index=frame.api_index,
                    pf=pf,
                    ps=ps,
                )
            return _build_supporting_reference_classification(
                raw_identity=raw_identity,
                canonical_identity=canonical_identity,
                api_class=frame.api_class,
                api_index=frame.api_index,
                pf=pf,
                ps=ps,
                reason=NON_DEVICE_REASON_REV_UNVERIFIED_FAMILY,
            )
        return _build_device_identity_classification(
            raw_identity=raw_identity,
            canonical_identity=canonical_identity,
            api_class=frame.api_class,
            api_index=frame.api_index,
            pf=pf,
            ps=ps,
        )

    return ObservedTrafficClassification(
        traffic_kind=TRAFFIC_KIND_UNKNOWN,
        traffic_role=ROLE_UNKNOWN,
        contributes_to_device_identity=False,
        supports_existing_device_identity=False,
        identity_disposition=IDENTITY_DISPOSITION_NON_DEVICE,
        reason=NON_DEVICE_REASON_UNKNOWN,
        family_key=_build_family_key(
            raw_identity=raw_identity,
            api_class=frame.api_class,
            api_index=frame.api_index,
            traffic_kind=TRAFFIC_KIND_UNKNOWN,
            pf=pf,
            ps=ps,
        ),
        raw_identity=raw_identity,
        canonical_identity=None,
        api_class=frame.api_class,
        api_index=frame.api_index,
        pf=pf,
        ps=ps,
    )


def _build_family_key(
    raw_identity: Tuple[int, int, int],
    api_class: Optional[int],
    api_index: Optional[int],
    traffic_kind: str,
    pf: int,
    ps: int,
) -> str:
    """
    NAME
        _build_family_key - Build a stable top-level non-device traffic family key.
    """
    raw_manufacturer, raw_device_type, raw_device_id = raw_identity
    api_class_value = int(api_class) if api_class is not None else -1
    api_index_value = int(api_index) if api_index is not None else -1
    return (
        f"mfg-{int(raw_manufacturer)}"
        f"_kind-{traffic_kind}"
        f"_type-{int(raw_device_type)}"
        f"_id-{int(raw_device_id)}"
        f"_api-{api_class_value}-{api_index_value}"
        f"_pf-{int(pf)}"
        f"_ps-{int(ps)}"
    )
