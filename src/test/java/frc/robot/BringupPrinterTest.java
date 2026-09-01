package frc.robot;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.io.ByteArrayOutputStream;
import java.io.PrintStream;
import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.concurrent.atomic.AtomicReference;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;

/**
 * NAME
 *   BringupPrinterTest - Regression tests for queued bringup output delivery.
 */
class BringupPrinterTest {
  private static final String MESSAGE_NO_NEWLINE = "queued message";
  private static final String MESSAGE_WITH_NEWLINE = "queued message\n";

  @AfterEach
  void restorePrinterState() {
    BringupPrinter.resetForTests();
  }

  @Test
  void dispatchMessageDeliversToListenerWithoutStdoutMirror() {
    AtomicReference<String> received = new AtomicReference<>("");
    BringupPrinter.setLineListener(received::set);
    BringupPrinter.setStdoutMirrorEnabled(false);
    ByteArrayOutputStream buffer = new ByteArrayOutputStream();
    PrintStream originalOut = System.out;
    System.setOut(new PrintStream(buffer, true, StandardCharsets.UTF_8));
    try {
      int countedBytes = BringupPrinter.dispatchMessage(MESSAGE_NO_NEWLINE, MESSAGE_NO_NEWLINE.length());

      assertEquals(MESSAGE_NO_NEWLINE.length(), countedBytes);
      assertEquals(MESSAGE_NO_NEWLINE, received.get());
      assertEquals("", buffer.toString(StandardCharsets.UTF_8));
    } finally {
      System.setOut(originalOut);
    }
  }

  @Test
  void dispatchMessageMirrorsToStdoutWhenEnabled() {
    AtomicReference<String> received = new AtomicReference<>("");
    BringupPrinter.setLineListener(received::set);
    BringupPrinter.setStdoutMirrorEnabled(true);
    ByteArrayOutputStream buffer = new ByteArrayOutputStream();
    PrintStream mirror = new PrintStream(buffer, true, StandardCharsets.UTF_8);
    BringupPrinter.setStdoutMirrorStreamForTests(mirror);
    int countedBytes = BringupPrinter.dispatchMessage(MESSAGE_NO_NEWLINE, MESSAGE_NO_NEWLINE.length());

    assertEquals(MESSAGE_NO_NEWLINE.length() + 1, countedBytes);
    assertEquals(MESSAGE_NO_NEWLINE, received.get());
    assertTrue(buffer.toString(StandardCharsets.UTF_8).contains(MESSAGE_NO_NEWLINE));
  }

  @Test
  void dispatchMessageDoesNotDoubleCountExistingNewline() {
    BringupPrinter.setStdoutMirrorEnabled(true);
    ByteArrayOutputStream buffer = new ByteArrayOutputStream();
    PrintStream mirror = new PrintStream(buffer, true, StandardCharsets.UTF_8);
    BringupPrinter.setStdoutMirrorStreamForTests(mirror);
    int countedBytes = BringupPrinter.dispatchMessage(MESSAGE_WITH_NEWLINE, MESSAGE_WITH_NEWLINE.length());

    assertEquals(MESSAGE_WITH_NEWLINE.length(), countedBytes);
    assertFalse(buffer.toString(StandardCharsets.UTF_8).endsWith("\n\n"));
  }

  @Test
  void dispatchMessageRetainsDeliveredMessagesWhenStdoutMirrorDisabled() {
    BringupPrinter.setStdoutMirrorEnabled(false);

    BringupPrinter.dispatchMessage(MESSAGE_NO_NEWLINE, MESSAGE_NO_NEWLINE.length());

    List<String> retained = BringupPrinter.getRetainedMessagesSnapshot();
    assertEquals(1, BringupPrinter.getRetainedMessageCount());
    assertEquals(0L, BringupPrinter.getRetainedDroppedMessages());
    assertEquals(MESSAGE_NO_NEWLINE, retained.get(0));
  }

  @Test
  void retainedMessagesDropOldestWhenBoundedBufferIsFull() {
    BringupPrinter.setRetainedMessageLimitForTests(2);

    BringupPrinter.dispatchMessage("first", "first".length());
    BringupPrinter.dispatchMessage("second", "second".length());
    BringupPrinter.dispatchMessage("third", "third".length());

    List<String> retained = BringupPrinter.getRetainedMessagesSnapshot();
    assertEquals(2, BringupPrinter.getRetainedMessageCount());
    assertEquals(1L, BringupPrinter.getRetainedDroppedMessages());
    assertEquals("second", retained.get(0));
    assertEquals("third", retained.get(1));
  }
}
