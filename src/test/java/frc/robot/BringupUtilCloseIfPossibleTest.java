package frc.robot;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import org.junit.jupiter.api.Test;

class BringupUtilCloseIfPossibleTest {

  private static final String WARNING_PREFIX = "test-close-prefix: ";

  @Test
  void closeIfPossibleReturnsTrueForNull() {
    assertTrue(BringupUtil.closeIfPossible(null, WARNING_PREFIX));
  }

  @Test
  void closeIfPossibleReturnsTrueWhenCloseSucceeds() {
    TestCloseable closeable = new TestCloseable(false);

    assertTrue(BringupUtil.closeIfPossible(closeable, WARNING_PREFIX));
    assertTrue(closeable.closed);
  }

  @Test
  void closeIfPossibleReturnsFalseWhenCloseThrows() {
    TestCloseable closeable = new TestCloseable(true);

    assertFalse(BringupUtil.closeIfPossible(closeable, WARNING_PREFIX));
    assertFalse(closeable.closed);
  }

  private static final class TestCloseable implements AutoCloseable {
    private final boolean throwOnClose;
    private boolean closed;

    private TestCloseable(boolean throwOnClose) {
      this.throwOnClose = throwOnClose;
      this.closed = false;
    }

    @Override
    public void close() throws Exception {
      if (throwOnClose) {
        throw new Exception("synthetic close failure");
      }
      closed = true;
    }
  }
}
