package frc.robot;

// Shared text formatting helpers for console reports.
// Keeps report formatting consistent across reporters.
public final class ReportTextUtil {
  private ReportTextUtil() {}

  public static void appendLine(StringBuilder sb, String line) {
    // Centralized line append to keep formatting uniform.
    sb.append(line).append('\n');
  }

  public static void appendWrappedHeaders(
      StringBuilder sb,
      String[] headerShort,
      String[] headerLong,
      int idWidth,
      int labelWidth,
      int mfgIdWidth,
      int typeIdWidth,
      int statusWidth,
      int ageWidth,
      int fpsWidth,
      int msgWidth,
      int maxLineWidth) {
    appendLine(sb, buildHeaderLine(
        headerShort,
        idWidth, labelWidth, mfgIdWidth, typeIdWidth, statusWidth, ageWidth, fpsWidth, msgWidth,
        maxLineWidth));
    if (headerLong != null) {
      appendLine(sb, buildHeaderLine(
          headerLong,
          idWidth, labelWidth, mfgIdWidth, typeIdWidth, statusWidth, ageWidth, fpsWidth, msgWidth,
          maxLineWidth));
    }
    appendLine(sb, "-".repeat(maxLineWidth));
  }

  public static void appendWrappedRow(
      StringBuilder sb,
      String[] values,
      int idWidth,
      int labelWidth,
      int mfgIdWidth,
      int typeIdWidth,
      int statusWidth,
      int ageWidth,
      int fpsWidth,
      int msgWidth,
      int maxLineWidth) {
    int[] widths = new int[] {
        idWidth, labelWidth, mfgIdWidth, typeIdWidth, statusWidth, ageWidth, fpsWidth, msgWidth
    };
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
        String padded = padRight(value, widths[col], '.');
        if (col > 0) {
          row.append(' ');
        }
        row.append(padded);
      }
      String rowText = row.toString();
      if (rowText.length() > maxLineWidth) {
        rowText = rowText.substring(0, maxLineWidth);
      }
      appendLine(sb, rowText);
    }
  }

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

  private static String buildHeaderLine(
      String[] values,
      int idWidth,
      int labelWidth,
      int mfgIdWidth,
      int typeIdWidth,
      int statusWidth,
      int ageWidth,
      int fpsWidth,
      int msgWidth,
      int maxLineWidth) {
    int[] widths = new int[] {
        idWidth, labelWidth, mfgIdWidth, typeIdWidth, statusWidth, ageWidth, fpsWidth, msgWidth
    };
    StringBuilder row = new StringBuilder(maxLineWidth);
    for (int col = 0; col < values.length; col++) {
      String value = values[col] == null ? "" : values[col];
      if (value.length() > widths[col]) {
        value = truncate(value, widths[col]);
      }
      String padded = padRight(value, widths[col], '.');
      if (col > 0) {
        row.append(' ');
      }
      row.append(padded);
    }
    String rowText = row.toString();
    if (rowText.length() > maxLineWidth) {
      rowText = rowText.substring(0, maxLineWidth);
    }
    return rowText;
  }

  private static String padRight(String value, int width, char fill) {
    // Pad a column to a fixed width using the provided fill character.
    if (value == null) {
      value = "";
    }
    int missing = width - value.length();
    if (missing <= 0) {
      return value;
    }
    return value + repeatChar(fill, missing);
  }

  private static String repeatChar(char fill, int count) {
    // Simple helper to avoid string builder noise at callsites.
    if (count <= 0) {
      return "";
    }
    return String.valueOf(fill).repeat(count);
  }

  private static String truncate(String value, int width) {
    // Truncate long values to fit a column while preserving readability.
    if (value == null) {
      return "";
    }
    if (value.length() <= width) {
      return value;
    }
    if (width <= 3) {
      return value.substring(0, width);
    }
    return value.substring(0, width - 3) + "...";
  }

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
        ? truncate(value, maxChars)
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
