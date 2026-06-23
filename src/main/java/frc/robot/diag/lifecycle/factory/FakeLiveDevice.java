package frc.robot.diag.lifecycle.factory;

import java.util.Objects;

/**
 * NAME
 *     FakeLiveDevice - lightweight test double for lifecycle activation tests.
 */
public final class FakeLiveDevice implements LiveDevice {
    private final String label;
    private final Runnable closeCallback;
    private boolean closed;

    FakeLiveDevice(String label, Runnable closeCallback) {
        this.label = Objects.requireNonNull(label, "label");
        this.closeCallback = Objects.requireNonNull(closeCallback, "closeCallback");
        this.closed = false;
    }

    @Override
    public String label() {
        return label;
    }

    @Override
    public boolean isClosed() {
        return closed;
    }

    @Override
    public void close() {
        if (closed) {
            return;
        }
        closed = true;
        closeCallback.run();
    }
}
