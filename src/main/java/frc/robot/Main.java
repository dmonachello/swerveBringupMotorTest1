// Copyright (c) FIRST and other WPILib contributors.
// Open Source Software; you can modify and/or share it under the terms of
// the WPILib BSD license file in the root directory of this project.

package frc.robot;

import edu.wpi.first.wpilibj.RobotBase;

/**
 * NAME
 *   Main - WPILib entry point wrapper.
 *
 * DESCRIPTION
 *   Provides the JVM entry point and selects the active robot class for
 *   WPILib startup.
 *
 * NOTES
 *   Keep this class free of static initialization to avoid early hardware
 *   access before WPILib bootstraps the runtime.
 */
public final class Main {
  private Main() {}

  /**
   * NAME
   *   main - Launch the selected robot class.
   *
   * SYNOPSIS
   *   main(String... args)
   *
   * DESCRIPTION
   *   Delegates to WPILib's RobotBase to start the configured robot program.
   *
   * PARAMETERS
   *   args - Command-line arguments (unused).
   *
   * SIDE EFFECTS
   *   Starts the WPILib robot lifecycle and threads.
   */
  public static void main(String... args) {
    // Entry point selection: RobotV2 is the active bringup harness.
    // Swap to Robot if you need the legacy behavior.
    // RobotBase.startRobot(Robot::new);
    RobotBase.startRobot(RobotV2::new);
  }
}
