package frc.robot.diag.lifecycle.factory;

/**
 * NAME
 *     FakeDeviceConstructionException - inject fake device-construction failures in lifecycle tests.
 */
public final class FakeDeviceConstructionException extends RuntimeException {
    private static final String MESSAGE_PREFIX = "Configured fake construction failure for label: ";

    public FakeDeviceConstructionException(String label) {
        super(MESSAGE_PREFIX + label);
    }
}
