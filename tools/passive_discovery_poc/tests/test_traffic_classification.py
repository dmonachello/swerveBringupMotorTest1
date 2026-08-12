from __future__ import annotations

import unittest

from tools.passive_discovery_poc.constants import CTRE_MANUFACTURER, REV_MANUFACTURER
from tools.passive_discovery_poc.models import NormalizedFrame
from tools.passive_discovery_poc.traffic_classification import (
    IDENTITY_DISPOSITION_DEFINITE,
    IDENTITY_DISPOSITION_NON_DEVICE,
    IDENTITY_DISPOSITION_SUPPORTING,
    KEY_CANONICAL_IDENTITY,
    KEY_DEVICE_ID,
    KEY_DEVICE_TYPE,
    KEY_IDENTITY_DISPOSITION,
    KEY_MANUFACTURER,
    KEY_RAW_IDENTITY,
    NON_DEVICE_REASON_BROADCAST_SYSTEM,
    NON_DEVICE_REASON_CTRE_DIAGNOSTIC_ENUMERATION,
    NON_DEVICE_REASON_CTRE_PASSIVE_ALIAS_REFERENCE,
    NON_DEVICE_REASON_CTRE_REFERENCE_FAMILY,
    NON_DEVICE_REASON_REV_UNVERIFIED_FAMILY,
    NON_DEVICE_REASON_SHARED_BUS_CONTROL,
    TRAFFIC_KIND_DEVICE_IDENTITY,
    TRAFFIC_KIND_NON_DEVICE_FAMILY,
    TRAFFIC_KIND_SUPPORTING_REFERENCE,
    classify_observed_frame,
)

TEST_TIMESTAMP_S = 1.0
TEST_ARBITRATION_ID = 0
TEST_DLC = 8
TEST_DATA_HEX = "0000000000000000"
TEST_OBSERVER_SOURCE = "test"
IDENTITY_INDEX_MANUFACTURER = 0
IDENTITY_INDEX_DEVICE_TYPE = 1
IDENTITY_INDEX_DEVICE_ID = 2

DEVICE_TYPE_CTRE_BROADCAST = 0
DEVICE_TYPE_CTRE_MOTOR = 2
DEVICE_TYPE_CTRE_PIGEON_CANONICAL = 4
DEVICE_TYPE_CTRE_CANCODER_PASSIVE = 5
DEVICE_TYPE_CTRE_CANCODER_CANONICAL = 7
DEVICE_TYPE_CTRE_POWER = 8
DEVICE_TYPE_CTRE_PIGEON_PASSIVE = 21
DEVICE_TYPE_REV_MOTOR = 2

CAN_ID_FALCON = 9
CAN_ID_CANCODER = 18
CAN_ID_PIGEON = 19
CAN_ID_PDP = 20
CAN_ID_SPARK = 25
DIAGNOSTIC_ID_FALCON = 6
DIAGNOSTIC_ID_CANCODER = 7
DIAGNOSTIC_ID_PDP = 8
DIAGNOSTIC_ID_PIGEON = 9

API_CLASS_CTRE_DIAGNOSTIC = 62
API_CLASS_CTRE_MOTOR_STATUS = 11
API_INDEX_CTRE_MOTOR_PRIMARY = 1
API_INDEX_CTRE_MOTOR_SECONDARY_IDENTITY = 7
API_INDEX_CTRE_CANCODER_PRIMARY = 3
API_INDEX_CTRE_PIGEON_PRIMARY = 4
API_CLASS_CTRE_POWER_STATUS = 5
API_INDEX_CTRE_POWER_STATUS_A = 0
API_INDEX_CTRE_POWER_STATUS_B = 1
API_INDEX_CTRE_POWER_STATUS_C = 2
API_INDEX_CTRE_POWER_STICKY_FAULTS = 9
API_INDEX_CTRE_POWER_STATUS = 13
API_INDEX_CTRE_DIAGNOSTIC_QUERY = 4
API_INDEX_CTRE_DIAGNOSTIC_RESPONSE = 5

API_CLASS_REV_STATUS = 46
API_CLASS_REV_HEARTBEAT = 47
API_CLASS_REV_COMMAND = 0
API_INDEX_REV_STATUS_PRIMARY = 0
API_INDEX_REV_STATUS_SECONDARY = 1
API_INDEX_REV_STATUS_FAULTS = 2
API_INDEX_REV_HEARTBEAT = 0
API_INDEX_REV_COMMAND_DUTY = 2


class TrafficClassificationTests(unittest.TestCase):
    """
    NAME
        TrafficClassificationTests - Validate shared device-identity traffic classification.
    """

    def _frame(
        self,
        *,
        manufacturer: int,
        device_type: int,
        device_id: int,
        api_class: int,
        api_index: int,
    ) -> NormalizedFrame:
        return NormalizedFrame(
            timestamp_s=TEST_TIMESTAMP_S,
            can_id=TEST_ARBITRATION_ID,
            dlc=TEST_DLC,
            data_hex=TEST_DATA_HEX,
            is_extended=True,
            is_rtr=False,
            manufacturer=manufacturer,
            device_type=device_type,
            api_class=api_class,
            api_index=api_index,
            device_id=device_id,
            observer_source=TEST_OBSERVER_SOURCE,
        )

    def test_broadcast_type_becomes_non_device_traffic_family(self) -> None:
        frame = NormalizedFrame(
            timestamp_s=1.0,
            can_id=(0x00 << 24) | (CTRE_MANUFACTURER << 16) | (7 << 10) | (3 << 6) | 63,
            dlc=8,
            data_hex="0000000000000000",
            is_extended=True,
            is_rtr=False,
            manufacturer=CTRE_MANUFACTURER,
            device_type=0,
            api_class=7,
            api_index=3,
            device_id=63,
            observer_source="test",
        )

        observed = classify_observed_frame(frame, (CTRE_MANUFACTURER, 0, 63))

        self.assertEqual(TRAFFIC_KIND_NON_DEVICE_FAMILY, observed.traffic_kind)
        self.assertFalse(observed.contributes_to_device_identity)
        self.assertEqual(NON_DEVICE_REASON_BROADCAST_SYSTEM, observed.reason)
        self.assertEqual(IDENTITY_DISPOSITION_NON_DEVICE, observed.identity_disposition)
        payload = observed.as_non_device_payload()
        self.assertEqual(CTRE_MANUFACTURER, payload[KEY_MANUFACTURER])
        self.assertEqual(0, payload[KEY_RAW_IDENTITY][KEY_DEVICE_TYPE])

    def test_ctre_passive_cancoder_alias_resolves_canonical_identity_hint(self) -> None:
        frame = NormalizedFrame(
            timestamp_s=1.0,
            can_id=(0x10 << 24) | (CTRE_MANUFACTURER << 16) | (11 << 10) | (3 << 6) | 18,
            dlc=8,
            data_hex="0000000000000000",
            is_extended=True,
            is_rtr=False,
            manufacturer=CTRE_MANUFACTURER,
            device_type=7,
            api_class=11,
            api_index=3,
            device_id=18,
            observer_source="test",
        )

        observed = classify_observed_frame(frame, (CTRE_MANUFACTURER, 5, 18))

        self.assertEqual(TRAFFIC_KIND_DEVICE_IDENTITY, observed.traffic_kind)
        self.assertTrue(observed.contributes_to_device_identity)
        self.assertFalse(observed.supports_existing_device_identity)
        self.assertEqual((CTRE_MANUFACTURER, 7, 18), observed.canonical_identity)

    def test_non_device_payload_includes_canonical_identity_when_available(self) -> None:
        frame = NormalizedFrame(
            timestamp_s=1.0,
            can_id=(0x00 << 24) | (CTRE_MANUFACTURER << 16) | (7 << 10) | (3 << 6) | 63,
            dlc=8,
            data_hex="0000000000000000",
            is_extended=True,
            is_rtr=False,
            manufacturer=CTRE_MANUFACTURER,
            device_type=0,
            api_class=7,
            api_index=3,
            device_id=63,
            observer_source="test",
        )

        observed = classify_observed_frame(frame, (CTRE_MANUFACTURER, 0, 63))
        payload = observed.as_non_device_payload()

        self.assertEqual(CTRE_MANUFACTURER, payload[KEY_CANONICAL_IDENTITY][KEY_MANUFACTURER])
        self.assertEqual(0, payload[KEY_CANONICAL_IDENTITY][KEY_DEVICE_TYPE])
        self.assertEqual(63, payload[KEY_CANONICAL_IDENTITY][KEY_DEVICE_ID])

    def test_ctre_passive_alias_is_supporting_not_device_defining(self) -> None:
        frame = NormalizedFrame(
            timestamp_s=1.0,
            can_id=(0x05 << 24) | (CTRE_MANUFACTURER << 16) | (13 << 10) | (1 << 6) | 18,
            dlc=8,
            data_hex="0000000000000000",
            is_extended=True,
            is_rtr=False,
            manufacturer=CTRE_MANUFACTURER,
            device_type=7,
            api_class=13,
            api_index=1,
            device_id=18,
            observer_source="test",
        )

        observed = classify_observed_frame(frame, (CTRE_MANUFACTURER, 5, 18))

        self.assertEqual(TRAFFIC_KIND_SUPPORTING_REFERENCE, observed.traffic_kind)
        self.assertFalse(observed.contributes_to_device_identity)
        self.assertTrue(observed.supports_existing_device_identity)
        self.assertEqual(IDENTITY_DISPOSITION_SUPPORTING, observed.identity_disposition)
        self.assertEqual(NON_DEVICE_REASON_CTRE_PASSIVE_ALIAS_REFERENCE, observed.reason)
        self.assertEqual((CTRE_MANUFACTURER, 7, 18), observed.canonical_identity)
        self.assertEqual(
            IDENTITY_DISPOSITION_SUPPORTING,
            observed.as_non_device_payload()[KEY_IDENTITY_DISPOSITION],
        )

    def test_ctre_passive_pigeon_primary_signature_is_device_defining(self) -> None:
        frame = NormalizedFrame(
            timestamp_s=1.0,
            can_id=(0x15 << 24) | (CTRE_MANUFACTURER << 16) | (11 << 10) | (4 << 6) | 19,
            dlc=8,
            data_hex="0000000000000000",
            is_extended=True,
            is_rtr=False,
            manufacturer=CTRE_MANUFACTURER,
            device_type=4,
            api_class=11,
            api_index=4,
            device_id=19,
            observer_source="test",
        )

        observed = classify_observed_frame(frame, (CTRE_MANUFACTURER, 21, 19))

        self.assertEqual(TRAFFIC_KIND_DEVICE_IDENTITY, observed.traffic_kind)
        self.assertTrue(observed.contributes_to_device_identity)
        self.assertFalse(observed.supports_existing_device_identity)
        self.assertEqual((CTRE_MANUFACTURER, 4, 19), observed.canonical_identity)

    def test_ctre_reference_api_family_is_supporting_not_device_defining(self) -> None:
        frame = NormalizedFrame(
            timestamp_s=1.0,
            can_id=(0x02 << 24) | (CTRE_MANUFACTURER << 16) | (7 << 10) | (3 << 6) | 9,
            dlc=8,
            data_hex="0000000000000000",
            is_extended=True,
            is_rtr=False,
            manufacturer=CTRE_MANUFACTURER,
            device_type=2,
            api_class=7,
            api_index=3,
            device_id=9,
            observer_source="test",
        )

        observed = classify_observed_frame(frame, (CTRE_MANUFACTURER, 2, 9))

        self.assertEqual(TRAFFIC_KIND_SUPPORTING_REFERENCE, observed.traffic_kind)
        self.assertFalse(observed.contributes_to_device_identity)
        self.assertTrue(observed.supports_existing_device_identity)
        self.assertEqual(NON_DEVICE_REASON_CTRE_REFERENCE_FAMILY, observed.reason)

    def test_ctre_unverified_motor_family_does_not_create_device_identity(self) -> None:
        frame = NormalizedFrame(
            timestamp_s=1.0,
            can_id=(0x00 << 24) | (CTRE_MANUFACTURER << 16) | (0 << 10) | (10 << 6) | 12,
            dlc=8,
            data_hex="0000000000000000",
            is_extended=True,
            is_rtr=False,
            manufacturer=CTRE_MANUFACTURER,
            device_type=2,
            api_class=0,
            api_index=10,
            device_id=12,
            observer_source="test",
        )

        observed = classify_observed_frame(frame, (CTRE_MANUFACTURER, 2, 12))

        self.assertEqual(TRAFFIC_KIND_SUPPORTING_REFERENCE, observed.traffic_kind)
        self.assertFalse(observed.contributes_to_device_identity)
        self.assertTrue(observed.supports_existing_device_identity)
        self.assertEqual(IDENTITY_DISPOSITION_SUPPORTING, observed.identity_disposition)

    def test_ctre_unverified_cancoder_family_does_not_create_device_identity(self) -> None:
        frame = NormalizedFrame(
            timestamp_s=1.0,
            can_id=(0x00 << 24) | (CTRE_MANUFACTURER << 16) | (0 << 10) | (0 << 6) | 11,
            dlc=8,
            data_hex="0000000000000000",
            is_extended=True,
            is_rtr=False,
            manufacturer=CTRE_MANUFACTURER,
            device_type=7,
            api_class=0,
            api_index=0,
            device_id=11,
            observer_source="test",
        )

        observed = classify_observed_frame(frame, (CTRE_MANUFACTURER, 7, 11))

        self.assertEqual(TRAFFIC_KIND_SUPPORTING_REFERENCE, observed.traffic_kind)
        self.assertFalse(observed.contributes_to_device_identity)
        self.assertTrue(observed.supports_existing_device_identity)
        self.assertEqual(IDENTITY_DISPOSITION_SUPPORTING, observed.identity_disposition)

    def test_ctre_unverified_power_family_does_not_create_device_identity(self) -> None:
        frame = NormalizedFrame(
            timestamp_s=1.0,
            can_id=(0x00 << 24) | (CTRE_MANUFACTURER << 16) | (0 << 10) | (0 << 6) | 10,
            dlc=8,
            data_hex="0000000000000000",
            is_extended=True,
            is_rtr=False,
            manufacturer=CTRE_MANUFACTURER,
            device_type=8,
            api_class=0,
            api_index=0,
            device_id=10,
            observer_source="test",
        )

        observed = classify_observed_frame(frame, (CTRE_MANUFACTURER, 8, 10))

        self.assertEqual(TRAFFIC_KIND_SUPPORTING_REFERENCE, observed.traffic_kind)
        self.assertFalse(observed.contributes_to_device_identity)
        self.assertTrue(observed.supports_existing_device_identity)
        self.assertEqual(IDENTITY_DISPOSITION_SUPPORTING, observed.identity_disposition)

    def test_connect_disconnect_ctre_device_defining_rules(self) -> None:
        cases = (
            (
                (CTRE_MANUFACTURER, DEVICE_TYPE_CTRE_MOTOR, CAN_ID_FALCON),
                (CTRE_MANUFACTURER, DEVICE_TYPE_CTRE_MOTOR, CAN_ID_FALCON),
                API_CLASS_CTRE_MOTOR_STATUS,
                API_INDEX_CTRE_MOTOR_PRIMARY,
            ),
            (
                (CTRE_MANUFACTURER, DEVICE_TYPE_CTRE_MOTOR, CAN_ID_FALCON),
                (CTRE_MANUFACTURER, DEVICE_TYPE_CTRE_MOTOR, CAN_ID_FALCON),
                API_CLASS_CTRE_MOTOR_STATUS,
                API_INDEX_CTRE_MOTOR_SECONDARY_IDENTITY,
            ),
            (
                (CTRE_MANUFACTURER, DEVICE_TYPE_CTRE_CANCODER_PASSIVE, CAN_ID_CANCODER),
                (CTRE_MANUFACTURER, DEVICE_TYPE_CTRE_CANCODER_CANONICAL, CAN_ID_CANCODER),
                API_CLASS_CTRE_MOTOR_STATUS,
                API_INDEX_CTRE_CANCODER_PRIMARY,
            ),
            (
                (CTRE_MANUFACTURER, DEVICE_TYPE_CTRE_PIGEON_PASSIVE, CAN_ID_PIGEON),
                (CTRE_MANUFACTURER, DEVICE_TYPE_CTRE_PIGEON_CANONICAL, CAN_ID_PIGEON),
                API_CLASS_CTRE_MOTOR_STATUS,
                API_INDEX_CTRE_PIGEON_PRIMARY,
            ),
            (
                (CTRE_MANUFACTURER, DEVICE_TYPE_CTRE_POWER, CAN_ID_PDP),
                (CTRE_MANUFACTURER, DEVICE_TYPE_CTRE_POWER, CAN_ID_PDP),
                API_CLASS_CTRE_POWER_STATUS,
                API_INDEX_CTRE_POWER_STATUS_A,
            ),
            (
                (CTRE_MANUFACTURER, DEVICE_TYPE_CTRE_POWER, CAN_ID_PDP),
                (CTRE_MANUFACTURER, DEVICE_TYPE_CTRE_POWER, CAN_ID_PDP),
                API_CLASS_CTRE_POWER_STATUS,
                API_INDEX_CTRE_POWER_STATUS_B,
            ),
            (
                (CTRE_MANUFACTURER, DEVICE_TYPE_CTRE_POWER, CAN_ID_PDP),
                (CTRE_MANUFACTURER, DEVICE_TYPE_CTRE_POWER, CAN_ID_PDP),
                API_CLASS_CTRE_POWER_STATUS,
                API_INDEX_CTRE_POWER_STATUS_C,
            ),
            (
                (CTRE_MANUFACTURER, DEVICE_TYPE_CTRE_POWER, CAN_ID_PDP),
                (CTRE_MANUFACTURER, DEVICE_TYPE_CTRE_POWER, CAN_ID_PDP),
                API_CLASS_CTRE_POWER_STATUS,
                API_INDEX_CTRE_POWER_STICKY_FAULTS,
            ),
            (
                (CTRE_MANUFACTURER, DEVICE_TYPE_CTRE_POWER, CAN_ID_PDP),
                (CTRE_MANUFACTURER, DEVICE_TYPE_CTRE_POWER, CAN_ID_PDP),
                API_CLASS_CTRE_POWER_STATUS,
                API_INDEX_CTRE_POWER_STATUS,
            ),
        )

        for raw_identity, canonical_identity, api_class, api_index in cases:
            with self.subTest(raw_identity=raw_identity, api_class=api_class, api_index=api_index):
                frame = self._frame(
                    manufacturer=canonical_identity[IDENTITY_INDEX_MANUFACTURER],
                    device_type=canonical_identity[IDENTITY_INDEX_DEVICE_TYPE],
                    device_id=canonical_identity[IDENTITY_INDEX_DEVICE_ID],
                    api_class=api_class,
                    api_index=api_index,
                )

                observed = classify_observed_frame(frame, raw_identity)

                self.assertEqual(TRAFFIC_KIND_DEVICE_IDENTITY, observed.traffic_kind)
                self.assertTrue(observed.contributes_to_device_identity)
                self.assertFalse(observed.supports_existing_device_identity)
                self.assertEqual(IDENTITY_DISPOSITION_DEFINITE, observed.identity_disposition)
                self.assertEqual(canonical_identity, observed.canonical_identity)

    def test_connect_disconnect_ctre_diagnostic_pairs_are_supporting_only(self) -> None:
        cases = (
            (
                (CTRE_MANUFACTURER, DEVICE_TYPE_CTRE_MOTOR, DIAGNOSTIC_ID_FALCON),
                (CTRE_MANUFACTURER, DEVICE_TYPE_CTRE_MOTOR, DIAGNOSTIC_ID_FALCON),
                API_INDEX_CTRE_DIAGNOSTIC_RESPONSE,
            ),
            (
                (CTRE_MANUFACTURER, DEVICE_TYPE_CTRE_CANCODER_PASSIVE, DIAGNOSTIC_ID_CANCODER),
                (CTRE_MANUFACTURER, DEVICE_TYPE_CTRE_CANCODER_CANONICAL, DIAGNOSTIC_ID_CANCODER),
                API_INDEX_CTRE_DIAGNOSTIC_RESPONSE,
            ),
            (
                (CTRE_MANUFACTURER, DEVICE_TYPE_CTRE_POWER, DIAGNOSTIC_ID_PDP),
                (CTRE_MANUFACTURER, DEVICE_TYPE_CTRE_POWER, DIAGNOSTIC_ID_PDP),
                API_INDEX_CTRE_DIAGNOSTIC_QUERY,
            ),
            (
                (CTRE_MANUFACTURER, DEVICE_TYPE_CTRE_POWER, DIAGNOSTIC_ID_PDP),
                (CTRE_MANUFACTURER, DEVICE_TYPE_CTRE_POWER, DIAGNOSTIC_ID_PDP),
                API_INDEX_CTRE_DIAGNOSTIC_RESPONSE,
            ),
            (
                (CTRE_MANUFACTURER, DEVICE_TYPE_CTRE_PIGEON_PASSIVE, DIAGNOSTIC_ID_PIGEON),
                (CTRE_MANUFACTURER, DEVICE_TYPE_CTRE_PIGEON_CANONICAL, DIAGNOSTIC_ID_PIGEON),
                API_INDEX_CTRE_DIAGNOSTIC_RESPONSE,
            ),
        )

        for raw_identity, canonical_identity, api_index in cases:
            with self.subTest(raw_identity=raw_identity, api_index=api_index):
                frame = self._frame(
                    manufacturer=canonical_identity[IDENTITY_INDEX_MANUFACTURER],
                    device_type=canonical_identity[IDENTITY_INDEX_DEVICE_TYPE],
                    device_id=canonical_identity[IDENTITY_INDEX_DEVICE_ID],
                    api_class=API_CLASS_CTRE_DIAGNOSTIC,
                    api_index=api_index,
                )

                observed = classify_observed_frame(frame, raw_identity)

                self.assertEqual(TRAFFIC_KIND_SUPPORTING_REFERENCE, observed.traffic_kind)
                self.assertFalse(observed.contributes_to_device_identity)
                self.assertTrue(observed.supports_existing_device_identity)
                self.assertEqual(IDENTITY_DISPOSITION_SUPPORTING, observed.identity_disposition)
                self.assertEqual(NON_DEVICE_REASON_CTRE_DIAGNOSTIC_ENUMERATION, observed.reason)
                self.assertEqual(canonical_identity, observed.canonical_identity)

    def test_connect_disconnect_rev_sparkmax_status_rules_are_device_defining(self) -> None:
        cases = (
            (API_CLASS_REV_STATUS, API_INDEX_REV_STATUS_PRIMARY),
            (API_CLASS_REV_STATUS, API_INDEX_REV_STATUS_SECONDARY),
            (API_CLASS_REV_STATUS, API_INDEX_REV_STATUS_FAULTS),
            (API_CLASS_REV_HEARTBEAT, API_INDEX_REV_HEARTBEAT),
        )
        identity = (REV_MANUFACTURER, DEVICE_TYPE_REV_MOTOR, CAN_ID_SPARK)

        for api_class, api_index in cases:
            with self.subTest(api_class=api_class, api_index=api_index):
                frame = self._frame(
                    manufacturer=identity[IDENTITY_INDEX_MANUFACTURER],
                    device_type=identity[IDENTITY_INDEX_DEVICE_TYPE],
                    device_id=identity[IDENTITY_INDEX_DEVICE_ID],
                    api_class=api_class,
                    api_index=api_index,
                )

                observed = classify_observed_frame(frame, identity)

                self.assertEqual(TRAFFIC_KIND_DEVICE_IDENTITY, observed.traffic_kind)
                self.assertTrue(observed.contributes_to_device_identity)
                self.assertFalse(observed.supports_existing_device_identity)
                self.assertEqual(IDENTITY_DISPOSITION_DEFINITE, observed.identity_disposition)
                self.assertEqual(identity, observed.canonical_identity)

    def test_rev_command_family_does_not_create_device_identity_by_itself(self) -> None:
        identity = (REV_MANUFACTURER, DEVICE_TYPE_REV_MOTOR, CAN_ID_SPARK)
        frame = self._frame(
            manufacturer=identity[IDENTITY_INDEX_MANUFACTURER],
            device_type=identity[IDENTITY_INDEX_DEVICE_TYPE],
            device_id=identity[IDENTITY_INDEX_DEVICE_ID],
            api_class=API_CLASS_REV_COMMAND,
            api_index=API_INDEX_REV_COMMAND_DUTY,
        )

        observed = classify_observed_frame(frame, identity)

        self.assertEqual(TRAFFIC_KIND_SUPPORTING_REFERENCE, observed.traffic_kind)
        self.assertFalse(observed.contributes_to_device_identity)
        self.assertTrue(observed.supports_existing_device_identity)
        self.assertEqual(IDENTITY_DISPOSITION_SUPPORTING, observed.identity_disposition)
        self.assertEqual(NON_DEVICE_REASON_REV_UNVERIFIED_FAMILY, observed.reason)


if __name__ == "__main__":
    unittest.main()
