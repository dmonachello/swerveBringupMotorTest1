package frc.robot.devices;

/**
 * NAME
 *   DeviceLifecycleOwnership - Shared ownership model for bringup devices.
 *
 * DESCRIPTION
 *   Distinguishes devices whose vendor resources belong to the active runtime
 *   from devices that are backed by app-level singleton services that may
 *   survive runtime teardown and later be reattached by new wrappers.
 */
public enum DeviceLifecycleOwnership {
  RUNTIME_OWNED_RECREATABLE,
  APP_OWNED_SINGLETON_SERVICE
}
