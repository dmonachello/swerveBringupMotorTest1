package frc.robot;

import java.io.OutputStream;
import java.io.PrintStream;
import java.nio.charset.StandardCharsets;

/**
 * NAME
 *   ConsoleCapture - Intercept process stdout/stderr and route lines into bringup sinks.
 *
 * DESCRIPTION
 *   Replaces the JVM stdout/stderr streams with line-buffering capture streams so
 *   vendor, HAL, and library console output can be retained for REST/UI evidence
 *   without spamming the visible roboRIO console.
 *
 * NOTES
 *   This capture is best-effort at the JVM stream level. Native logging that
 *   bypasses System.out/System.err is outside its scope.
 */
public final class ConsoleCapture {
  private static final Object INSTALL_LOCK = new Object();
  private static final String CHARSET_UTF8 = StandardCharsets.UTF_8.name();
  private static final char NEWLINE = '\n';
  private static final char CARRIAGE_RETURN = '\r';
  private static final PrintStream PROCESS_STDOUT = System.out;
  private static final PrintStream PROCESS_STDERR = System.err;
  private static volatile boolean installed = false;
  private static PrintStream originalOut = System.out;
  private static PrintStream originalErr = System.err;

  private ConsoleCapture() {}

  /**
   * NAME
   *   install - Replace stdout/stderr with capture streams.
   *
   * PARAMETERS
   *   sink - Consumer for completed console lines.
   *
   * SIDE EFFECTS
   *   Calls System.setOut/System.setErr once per process.
   */
  public static void install(ConsoleLineSink sink) {
    if (sink == null || installed) {
      return;
    }
    synchronized (INSTALL_LOCK) {
      if (sink == null || installed) {
        return;
      }
      originalOut = System.out;
      originalErr = System.err;
      System.setOut(createCapturePrintStream(sink));
      System.setErr(createCapturePrintStream(sink));
      installed = true;
    }
  }

  /**
   * NAME
   *   restoreOriginalStreamsForTests - Restore original stdout/stderr streams.
   *
   * SIDE EFFECTS
   *   Resets the installed state for isolated unit tests.
   */
  static void restoreOriginalStreamsForTests() {
    synchronized (INSTALL_LOCK) {
      System.setOut(PROCESS_STDOUT);
      System.setErr(PROCESS_STDERR);
      originalOut = PROCESS_STDOUT;
      originalErr = PROCESS_STDERR;
      installed = false;
    }
  }

  static boolean isInstalledForTests() {
    return installed;
  }

  /**
   * NAME
   *   ConsoleLineSink - Consumer for intercepted console lines.
   */
  public interface ConsoleLineSink {
    void onConsoleLine(String text);
  }

  private static PrintStream createCapturePrintStream(ConsoleLineSink sink) {
    try {
      return new PrintStream(new CaptureOutputStream(sink), true, CHARSET_UTF8);
    } catch (java.io.UnsupportedEncodingException ex) {
      throw new IllegalStateException(ex);
    }
  }

  private static final class CaptureOutputStream extends OutputStream {
    private final ConsoleLineSink sink;
    private final StringBuilder buffer = new StringBuilder();

    private CaptureOutputStream(ConsoleLineSink sink) {
      this.sink = sink;
    }

    @Override
    public synchronized void write(int value) {
      char next = (char) (value & 0xff);
      if (next == CARRIAGE_RETURN) {
        return;
      }
      if (next == NEWLINE) {
        flushBufferLocked();
        return;
      }
      buffer.append(next);
    }

    @Override
    public synchronized void flush() {
      flushBufferLocked();
    }

    private void flushBufferLocked() {
      if (buffer.length() <= 0) {
        return;
      }
      String text = buffer.toString();
      buffer.setLength(0);
      sink.onConsoleLine(text);
    }
  }
}
