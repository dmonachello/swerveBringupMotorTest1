package frc.robot;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.io.ByteArrayOutputStream;
import java.io.PrintStream;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;

/**
 * NAME
 *   ConsoleCaptureTest - Regression tests for robot-side stdout/stderr interception.
 */
class ConsoleCaptureTest {
  private static final String MESSAGE_EXTERNAL = "HAL timeout line";
  private static final String MESSAGE_BRINGUP = "bringup line";

  @AfterEach
  void tearDown() {
    ConsoleCapture.restoreOriginalStreamsForTests();
    BringupPrinter.resetForTests();
  }

  @Test
  void installCapturesExternalStdoutIntoBringupListenerWithoutVisibleConsoleMirror() {
    List<String> received = new ArrayList<>();
    BringupPrinter.setStdoutMirrorEnabled(false);
    BringupPrinter.setLineListener(received::add);
    ByteArrayOutputStream visibleConsole = new ByteArrayOutputStream();
    System.setOut(new PrintStream(visibleConsole, true, StandardCharsets.UTF_8));
    ConsoleCapture.install(BringupPrinter::captureExternalLine);

    System.out.println(MESSAGE_EXTERNAL);
    System.out.flush();

    assertTrue(ConsoleCapture.isInstalledForTests());
    assertEquals(1, received.size());
    assertEquals(MESSAGE_EXTERNAL, received.get(0));
    assertTrue(BringupPrinter.getRetainedMessagesSnapshot().contains(MESSAGE_EXTERNAL));
    assertEquals("", visibleConsole.toString(StandardCharsets.UTF_8));
  }

  @Test
  void bringupStdoutMirrorWritesToOriginalStreamWithoutInterceptorLoop() {
    List<String> received = new ArrayList<>();
    BringupPrinter.setStdoutMirrorEnabled(true);
    BringupPrinter.setLineListener(received::add);
    ByteArrayOutputStream visibleConsole = new ByteArrayOutputStream();
    System.setOut(new PrintStream(visibleConsole, true, StandardCharsets.UTF_8));
    BringupPrinter.setStdoutMirrorStreamForTests(new PrintStream(visibleConsole, true, StandardCharsets.UTF_8));
    ConsoleCapture.install(BringupPrinter::captureExternalLine);

    BringupPrinter.dispatchMessage(MESSAGE_BRINGUP, MESSAGE_BRINGUP.length());

    assertEquals(1, received.size());
    assertEquals(MESSAGE_BRINGUP, received.get(0));
    assertTrue(visibleConsole.toString(StandardCharsets.UTF_8).contains(MESSAGE_BRINGUP));
    assertFalse(visibleConsole.toString(StandardCharsets.UTF_8).contains(MESSAGE_BRINGUP + MESSAGE_BRINGUP));
  }
}
