package frc.robot;

/**
 * NAME
 *   BuildInfo - Build metadata captured from git.
 */
public final class BuildInfo {
  private BuildInfo() {}

  public static final String BUILD_GIT_DESCRIBE = "ui-dsl-test-workflow-hardening-2026-05-31-dirty";
  public static final String BUILD_GIT_SHA = "29d64b5";
  public static final String BUILD_GIT_BRANCH = "main";
  public static final String BUILD_GIT_DIRTY = "dirty";
  public static final String BUILD_TIMESTAMP = "2026-05-31T16:39:11-04:00";

  public static final String BUILD_LABEL_GIT = "git";
  public static final String BUILD_LABEL_SHA = "git-sha";
  public static final String BUILD_LABEL_BRANCH = "git-branch";
  public static final String BUILD_LABEL_DIRTY = "git-dirty";
  public static final String BUILD_LABEL_TIME = "build-time";

  public static final String BUILD_SEPARATOR = ": ";
  public static final String TEXT_NEWLINE = "\n";

  /**
   * NAME
   *   formatBuildLine - Build a standard build-info line.
   *
   * PARAMETERS
   *   label - Label to display (e.g., "git").
   *   value - Build metadata value.
   *
   * RETURNS
   *   A formatted build-info line.
   */
  public static String formatBuildLine(String label, String value) {
    return label + BUILD_SEPARATOR + value;
  }
}
