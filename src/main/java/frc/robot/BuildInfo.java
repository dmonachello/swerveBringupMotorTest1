package frc.robot;

/**
 * NAME
 *   BuildInfo - Build metadata captured from git.
 */
public final class BuildInfo {
  private BuildInfo() {}

  public static final String BUILD_GIT_DESCRIBE = "can-evidence-prep-and-active-probe-2026-06-03-dirty";
  public static final String BUILD_GIT_SHA = "c7323a2";
  public static final String BUILD_GIT_BRANCH = "main";
  public static final String BUILD_GIT_DIRTY = "dirty";
  public static final String BUILD_TIMESTAMP = "2026-06-03T13:02:41-04:00";

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
