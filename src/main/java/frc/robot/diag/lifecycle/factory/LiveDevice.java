package frc.robot.diag.lifecycle.factory;

/**
 * NAME
 *     LiveDevice - minimal live-device lifecycle contract used by the activation manager.
 */
public interface LiveDevice extends AutoCloseable {
    String label();

    boolean isClosed();

    @Override
    void close();
}
