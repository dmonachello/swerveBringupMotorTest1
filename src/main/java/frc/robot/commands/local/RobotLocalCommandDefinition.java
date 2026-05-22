package frc.robot.commands.local;

/**
 * NAME
 *   RobotLocalCommandDefinition - Canonical command registry row.
 */
public final class RobotLocalCommandDefinition {
  private final String wireName;
  private final RobotLocalCommandGroup group;
  private final RobotLocalInvocationKind invocationKind;
  private final boolean controllerAllowed;
  private final boolean hostUiAllowed;
  private final boolean queueable;
  private final boolean autoStopOnSourceLoss;
  private final boolean showInHostUi;
  private final String uiSection;
  private final String uiLabel;
  private final String uiDescription;
  private final String uiArgsJson;
  private final RobotLocalCommand command;

  public RobotLocalCommandDefinition(
      String wireName,
      RobotLocalCommandGroup group,
      RobotLocalInvocationKind invocationKind,
      boolean controllerAllowed,
      boolean hostUiAllowed,
      boolean queueable,
      boolean autoStopOnSourceLoss,
      boolean showInHostUi,
      String uiSection,
      String uiLabel,
      String uiDescription,
      String uiArgsJson,
      RobotLocalCommand command) {
    this.wireName = wireName;
    this.group = group;
    this.invocationKind = invocationKind;
    this.controllerAllowed = controllerAllowed;
    this.hostUiAllowed = hostUiAllowed;
    this.queueable = queueable;
    this.autoStopOnSourceLoss = autoStopOnSourceLoss;
    this.showInHostUi = showInHostUi;
    this.uiSection = uiSection;
    this.uiLabel = uiLabel;
    this.uiDescription = uiDescription;
    this.uiArgsJson = uiArgsJson;
    this.command = command;
  }

  public String wireName() {
    return wireName;
  }

  public RobotLocalCommandGroup group() {
    return group;
  }

  public RobotLocalInvocationKind invocationKind() {
    return invocationKind;
  }

  public boolean controllerAllowed() {
    return controllerAllowed;
  }

  public boolean hostUiAllowed() {
    return hostUiAllowed;
  }

  public boolean queueable() {
    return queueable;
  }

  public boolean autoStopOnSourceLoss() {
    return autoStopOnSourceLoss;
  }

  public boolean showInHostUi() {
    return showInHostUi;
  }

  public String uiSection() {
    return uiSection;
  }

  public String uiLabel() {
    return uiLabel;
  }

  public String uiDescription() {
    return uiDescription;
  }

  public String uiArgsJson() {
    return uiArgsJson;
  }

  public RobotLocalCommand command() {
    return command;
  }

  public boolean isAllowedFor(RobotLocalCommandSource source) {
    return switch (source) {
      case CONTROLLER -> controllerAllowed;
      case HOST_UI -> hostUiAllowed;
    };
  }
}
