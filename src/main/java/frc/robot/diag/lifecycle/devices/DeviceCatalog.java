package frc.robot.diag.lifecycle.devices;

import frc.robot.diag.lifecycle.labels.GlobalLabelRegistry;
import frc.robot.diag.lifecycle.runtime.DeviceRuntimeState;
import java.util.Collection;
import java.util.LinkedHashMap;
import java.util.Map;

/**
 * NAME
 *     DeviceCatalog - load and expose declared lifecycle device records and runtime states.
 *
 * DESCRIPTION
 *     Loading the catalog registers device labels and creates runtime state slots, but it does
 *     not create live vendor objects.
 */
public final class DeviceCatalog {
    private static final String ERROR_UNKNOWN_DEVICE_PREFIX = "Unknown device label: ";
    private static final int NO_LIVE_DEVICES = 0;

    private final GlobalLabelRegistry labelRegistry;
    private final Map<String, DeviceRecord> deviceRecordsByLabel;
    private final Map<String, DeviceRuntimeState> runtimeStatesByLabel;

    private DeviceCatalog(
            GlobalLabelRegistry labelRegistry,
            Map<String, DeviceRecord> deviceRecordsByLabel,
            Map<String, DeviceRuntimeState> runtimeStatesByLabel) {
        this.labelRegistry = labelRegistry;
        this.deviceRecordsByLabel = deviceRecordsByLabel;
        this.runtimeStatesByLabel = runtimeStatesByLabel;
    }

    /**
     * NAME
     *     load - build a device catalog from declarations.
     *
     * PARAMETERS
     *     declarations - declared device inputs.
     *
     * RETURNS
     *     A catalog containing immutable device records and runtime state objects.
     */
    public static DeviceCatalog load(Iterable<DeviceDeclaration> declarations) {
        GlobalLabelRegistry labelRegistry = new GlobalLabelRegistry();
        Map<String, DeviceRecord> deviceRecordsByLabel = new LinkedHashMap<>();
        Map<String, DeviceRuntimeState> runtimeStatesByLabel = new LinkedHashMap<>();

        for (DeviceDeclaration declaration : declarations) {
            DeviceRecord record = declaration.toRecord();
            labelRegistry.registerDeviceLabel(record.label());
            deviceRecordsByLabel.put(record.label(), record);
            runtimeStatesByLabel.put(record.label(), new DeviceRuntimeState());
        }

        return new DeviceCatalog(labelRegistry, deviceRecordsByLabel, runtimeStatesByLabel);
    }

    public GlobalLabelRegistry labelRegistry() {
        return labelRegistry;
    }

    public DeviceRecord deviceRecord(String label) {
        DeviceRecord record = deviceRecordsByLabel.get(label);
        if (record == null) {
            throw new IllegalArgumentException(ERROR_UNKNOWN_DEVICE_PREFIX + label);
        }
        return record;
    }

    public DeviceRuntimeState runtimeState(String label) {
        DeviceRuntimeState runtimeState = runtimeStatesByLabel.get(label);
        if (runtimeState == null) {
            throw new IllegalArgumentException(ERROR_UNKNOWN_DEVICE_PREFIX + label);
        }
        return runtimeState;
    }

    public Collection<DeviceRecord> deviceRecords() {
        return deviceRecordsByLabel.values();
    }

    public Collection<DeviceRuntimeState> runtimeStates() {
        return runtimeStatesByLabel.values();
    }

    /**
     * NAME
     *     liveDeviceCount - report the number of live vendor objects created during load.
     *
     * RETURNS
     *     Always zero for this model-layer slice.
     */
    public int liveDeviceCount() {
        return NO_LIVE_DEVICES;
    }
}
