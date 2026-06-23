package frc.robot.diag.lifecycle.labels;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

import org.junit.jupiter.api.Test;

class GlobalLabelRegistryTest {
    private static final String DEVICE_LABEL = "front_left_drive";
    private static final String GROUP_LABEL = "front_left_corner";
    private static final String SHARED_LABEL = "bringup_active";
    private static final String MISSING_LABEL = "missing_label";
    private static final String DRIVE_GROUP_LABEL = "all_drive_motors";

    @Test
    void registerDeviceLabelStoresDeviceKind() {
        GlobalLabelRegistry registry = new GlobalLabelRegistry();

        registry.registerDeviceLabel(DEVICE_LABEL);

        assertEquals(LabelKind.DEVICE, registry.labelKindOf(DEVICE_LABEL));
    }

    @Test
    void registerGroupLabelStoresGroupKind() {
        GlobalLabelRegistry registry = new GlobalLabelRegistry();

        registry.registerGroupLabel(GROUP_LABEL);

        assertEquals(LabelKind.GROUP, registry.labelKindOf(GROUP_LABEL));
    }

    @Test
    void duplicateDeviceLabelFails() {
        GlobalLabelRegistry registry = new GlobalLabelRegistry();
        registry.registerDeviceLabel(DEVICE_LABEL);

        assertThrows(DuplicateLabelException.class, () -> registry.registerDeviceLabel(DEVICE_LABEL));
    }

    @Test
    void duplicateGroupLabelFails() {
        GlobalLabelRegistry registry = new GlobalLabelRegistry();
        registry.registerGroupLabel(GROUP_LABEL);

        assertThrows(DuplicateLabelException.class, () -> registry.registerGroupLabel(GROUP_LABEL));
    }

    @Test
    void deviceAndGroupShareOneGlobalNamespace() {
        GlobalLabelRegistry registry = new GlobalLabelRegistry();
        registry.registerDeviceLabel(SHARED_LABEL);

        assertThrows(DuplicateLabelException.class, () -> registry.registerGroupLabel(SHARED_LABEL));
    }

    @Test
    void unknownLabelLookupFails() {
        GlobalLabelRegistry registry = new GlobalLabelRegistry();

        assertThrows(UnknownLabelException.class, () -> registry.labelKindOf(MISSING_LABEL));
    }

    @Test
    void labelKindLookupWorksForBothKinds() {
        GlobalLabelRegistry registry = new GlobalLabelRegistry();
        registry.registerDeviceLabel(DEVICE_LABEL);
        registry.registerGroupLabel(DRIVE_GROUP_LABEL);

        assertEquals(LabelKind.DEVICE, registry.labelKindOf(DEVICE_LABEL));
        assertEquals(LabelKind.GROUP, registry.labelKindOf(DRIVE_GROUP_LABEL));
    }
}
