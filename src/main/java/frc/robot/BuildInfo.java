package frc.robot;

/**
 * NAME
 *   BuildInfo - Build metadata captured from git.
 */
public final class BuildInfo {
  private BuildInfo() {}

  public static final String BUILD_GIT_DESCRIBE = "reliability-hardening-2026-07-22-dirty";
  public static final String BUILD_REVISION = "265";
  public static final String BUILD_WORKSPACE_REVISION = "331";
  public static final String BUILD_CODE_REVISION = "88deb6f8f571";
  public static final String BUILD_GIT_SHA = "9bfa5b6";
  public static final String BUILD_GIT_BRANCH = "main";
  public static final String BUILD_GIT_DIRTY = "dirty";
  public static final String BUILD_TIMESTAMP = "2026-07-21T20:58:26-04:00";

  public static final String BUILD_LABEL_REVISION = "build-revision";
  public static final String BUILD_LABEL_WORKSPACE_REVISION = "workspace-revision";
  public static final String BUILD_LABEL_CODE_REVISION = "code-revision";
  public static final String BUILD_LABEL_GIT = "git";
  public static final String BUILD_LABEL_SHA = "git-sha";
  public static final String BUILD_LABEL_BRANCH = "git-branch";
  public static final String BUILD_LABEL_DIRTY = "git-dirty";
  public static final String BUILD_LABEL_TIME = "build-time";

  public static final String BUILD_SEPARATOR = ": ";
  public static final String BOOT_PREFIX = "BOOT ";
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

  /**
   * NAME
   *   buildBootRevisionLine - Build the direct boot-console revision line.
   *
   * RETURNS
   *   A single-line boot banner entry for build revision visibility.
   */
  public static String buildBootRevisionLine() {
    return BOOT_PREFIX + formatBuildLine(BUILD_LABEL_REVISION, BUILD_REVISION);
  }

  /**
   * NAME
   *   buildBootWorkspaceRevisionLine - Build the direct boot-console workspace-revision line.
   *
   * RETURNS
   *   A single-line boot banner entry for local workspace ordering visibility.
   */
  public static String buildBootWorkspaceRevisionLine() {
    return BOOT_PREFIX + formatBuildLine(BUILD_LABEL_WORKSPACE_REVISION, BUILD_WORKSPACE_REVISION);
  }

  /**
   * NAME
   *   buildBootCodeRevisionLine - Build the direct boot-console code-revision line.
   *
   * RETURNS
   *   A single-line boot banner entry for local code fingerprint visibility.
   */
  public static String buildBootCodeRevisionLine() {
    return BOOT_PREFIX + formatBuildLine(BUILD_LABEL_CODE_REVISION, BUILD_CODE_REVISION);
  }
}
