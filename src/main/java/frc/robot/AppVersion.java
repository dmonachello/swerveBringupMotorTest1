package frc.robot;

/**
 * NAME
 *   AppVersion - Version constants for the robot bringup app.
 */
public final class AppVersion {
  private AppVersion() {}

  public static final int ROBOT_APP_VERSION_MAJOR = 1;
  public static final int ROBOT_APP_VERSION_MINOR = 0;
  public static final int ROBOT_APP_VERSION_PATCH = 0;
  public static final String ROBOT_APP_VERSION_SUFFIX = "-rc1";
  public static final String ROBOT_APP_VERSION =
      ROBOT_APP_VERSION_MAJOR
          + "."
          + ROBOT_APP_VERSION_MINOR
          + "."
          + ROBOT_APP_VERSION_PATCH
          + ROBOT_APP_VERSION_SUFFIX;
  public static final String VERSION_PREFIX = "Robot version: ";
}
