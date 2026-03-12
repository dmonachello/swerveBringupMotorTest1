package frc.robot;

/**
 * NAME
 *   ReportTextUtil - Shared console report formatting helpers.
 *
 * DESCRIPTION
 *   Provides reusable formatting helpers for text-based reports to keep
 *   fixed-width, dot-padded, right-justified alignment consistent across diagnostics outputs.
 */
public final class ReportTextUtil {
  private ReportTextUtil() {}

  /**
   * NAME
   *   appendLine - Append a line with newline termination.
   *
   * PARAMETERS
   *   sb - Target StringBuilder.
   *   line - Line content to append.
   */
  public static void appendLine(StringBuilder sb, String line) {
    // Centralized line append to keep formatting uniform.
    sb.append(line).append('\n');
  }

  /**
   * NAME
   *   appendWrappedHeaders - Append header rows with wrapping.
   *
   * PARAMETERS
   *   sb - Target StringBuilder.
   *   headerShort - Primary header labels.
   *   headerLong - Optional secondary header labels.
   *   widths - Column widths in order of the header array.
   *   maxLineWidth - Maximum line width for truncation.
   */
  public static void appendWrappedHeaders(
      StringBuilder sb,
      String[] headerShort,
      String[] headerLong,
      int[] widths,
      int maxLineWidth) {
    appendLine(sb, buildHeaderLine(headerShort, widths, maxLineWidth));
    if (headerLong != null) {
      appendLine(sb, buildHeaderLine(headerLong, widths, maxLineWidth));
    }
    appendLine(sb, "-".repeat(maxLineWidth));
  }

  /**
   * NAME
   *   appendWrappedRow - Append one or more wrapped table rows.
   *
   * PARAMETERS
   *   sb - Target StringBuilder.
   *   values - Column values to wrap.
   *   widths - Column widths in order of the values array.
   *   maxLineWidth - Maximum line width for truncation.
   */
  public static void appendWrappedRow(
      StringBuilder sb,
      String[] values,
      int[] widths,
      int maxLineWidth) {
    String[][] columns = new String[values.length][];
    int maxLines = 1;
    for (int i = 0; i < values.length; i++) {
      columns[i] = wrapToLines(values[i], widths[i], 4);
      maxLines = Math.max(maxLines, columns[i].length);
    }

    for (int line = 0; line < maxLines; line++) {
      StringBuilder row = new StringBuilder(maxLineWidth);
      for (int col = 0; col < columns.length; col++) {
        String[] colLines = columns[col];
        String value = line < colLines.length ? colLines[line] : "";
        row.append(padRight(value, widths[col], '.'));
      }
      String rowText = row.toString();
      if (rowText.length() > maxLineWidth) {
        rowText = rowText.substring(0, maxLineWidth);
      }
      appendLine(sb, rowText);
    }
  }

  /**
   * NAME
   *   wrapLongLine - Wrap a long string at fixed width.
   *
   * PARAMETERS
   *   value - Source string.
   *   width - Maximum line width.
   *
   * RETURNS
   *   Wrapped string with newline separators.
   */
  public static String wrapLongLine(String value, int width) {
    // Wrap a single long line (like JSON) for console-friendly output.
    if (value == null) {
      return "";
    }
    if (width <= 0 || value.length() <= width) {
      return value;
    }
    StringBuilder sb = new StringBuilder(value.length() + (value.length() / width) + 2);
    for (int i = 0; i < value.length(); i += width) {
      int end = Math.min(i + width, value.length());
      sb.append(value, i, end).append('\n');
    }
    return sb.toString();
  }

  /**
   * NAME
   *   buildHeaderLine - Build a single header line with padding.
   */
  private static String buildHeaderLine(
      String[] values,
      int[] widths,
      int maxLineWidth) {
    StringBuilder row = new StringBuilder(maxLineWidth);
    for (int col = 0; col < values.length; col++) {
      String value = values[col] == null ? "" : values[col];
      row.append(padRight(value, widths[col], '.'));
    }
    String rowText = row.toString();
    if (rowText.length() > maxLineWidth) {
      rowText = rowText.substring(0, maxLineWidth);
    }
    return rowText;
  }

  /**
   * NAME
   *   padRight - Pad a value to a fixed width.
   */
  private static String padRight(String value, int width, char fill) {
    // Right-justify a column to a fixed width using the provided fill character.
    if (value == null) {
      value = "";
    }
    if (width <= 0) {
      return "";
    }
    if (value.length() > width) {
      return value.substring(0, width);
    }
    int missing = width - value.length();
    if (missing <= 0) {
      return value;
    }
    return repeatChar(fill, missing) + value;
  }

  /**
   * NAME
   *   repeatChar - Produce a repeated character string.
   */
  private static String repeatChar(char fill, int count) {
    // Simple helper to avoid string builder noise at callsites.
    if (count <= 0) {
      return "";
    }
    return String.valueOf(fill).repeat(count);
  }

  /**
   * NAME
   *   truncate - Truncate a value for column display.
   */
  private static String truncate(String value, int width) {
    // Truncate long values to fit a column.
    if (value == null || width <= 0) {
      return "";
    }
    if (value.length() <= width) {
      return value;
    }
    return value.substring(0, width);
  }

  /**
   * NAME
   *   wrapToLines - Wrap a value into fixed-width column lines.
   */
  private static String[] wrapToLines(String value, int width, int maxLines) {
    // Wrap a string into fixed-width columns for table output.
    if (value == null) {
      value = "";
    }
    if (width <= 0) {
      return new String[] { "" };
    }
    int maxChars = width * maxLines;
    String trimmed = value.length() > maxChars
        ? value.substring(0, maxChars)
        : value;
    int lines = (int) Math.ceil(trimmed.length() / (double) width);
    lines = Math.min(lines, maxLines);
    String[] result = new String[lines == 0 ? 1 : lines];
    if (trimmed.isEmpty()) {
      result[0] = "";
      return result;
    }
    for (int i = 0; i < lines; i++) {
      int start = i * width;
      int end = Math.min(start + width, trimmed.length());
      result[i] = trimmed.substring(start, end);
    }
    return result;
  }
}
