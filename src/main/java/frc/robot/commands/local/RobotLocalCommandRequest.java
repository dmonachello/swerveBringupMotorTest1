package frc.robot.commands.local;

import com.google.gson.JsonObject;

/**
 * NAME
 *   RobotLocalCommandRequest - Normalized request submitted to the executor.
 */
public final class RobotLocalCommandRequest {
  private final String name;
  private final RobotLocalCommandSource source;
  private final RobotLocalDispatchMode dispatchMode;
  private final JsonObject args;
  private final RobotLocalValueProvider valueProvider;
  private final String clientId;
  private final double timestampSec;
  private final boolean tcp;

  public RobotLocalCommandRequest(
      String name,
      RobotLocalCommandSource source,
      RobotLocalDispatchMode dispatchMode,
      JsonObject args,
      RobotLocalValueProvider valueProvider,
      String clientId,
      double timestampSec,
      boolean tcp) {
    this.name = name;
    this.source = source;
    this.dispatchMode = dispatchMode;
    this.args = args;
    this.valueProvider = valueProvider != null ? valueProvider : RobotLocalNoopValueProvider.INSTANCE;
    this.clientId = clientId;
    this.timestampSec = timestampSec;
    this.tcp = tcp;
  }

  public String name() {
    return name;
  }

  public RobotLocalCommandSource source() {
    return source;
  }

  public RobotLocalDispatchMode dispatchMode() {
    return dispatchMode;
  }

  public JsonObject args() {
    return args;
  }

  public RobotLocalValueProvider valueProvider() {
    return valueProvider;
  }

  public String clientId() {
    return clientId;
  }

  public double timestampSec() {
    return timestampSec;
  }

  public boolean tcp() {
    return tcp;
  }
}
