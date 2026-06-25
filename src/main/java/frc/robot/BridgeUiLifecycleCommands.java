package frc.robot;

import com.google.gson.JsonArray;
import com.google.gson.JsonObject;
import frc.robot.diag.lifecycle.activation.ActivationMode;
import frc.robot.diag.lifecycle.activation.ActivationResult;
import frc.robot.diag.lifecycle.activation.DeactivateResult;
import java.util.Locale;
import java.util.Set;

/**
 * NAME
 *   BridgeUiLifecycleCommands - Controlled-lifecycle command family executor.
 *
 * DESCRIPTION
 *   Adds additive robot-side lifecycle activation/readback commands onto the
 *   existing UI/REST command path without replacing the legacy runtime path.
 */
final class BridgeUiLifecycleCommands implements BridgeUiCommandDispatcher.CommandFamily {

  private static final String CMD_LIFECYCLE_ACTIVATE = "lifecycleActivate";
  private static final String CMD_LIFECYCLE_DEACTIVATE = "lifecycleDeactivate";
  private static final String CMD_LIFECYCLE_DEACTIVATE_ACTIVE = "lifecycleDeactivateActive";
  private static final String CMD_SHOW_LIFECYCLE_STATE = "showLifecycleState";
  private static final String CMD_ACTIVATE_SELECTED_TEST_DEVICES = "activateSelectedTestDevices";
  private static final String CMD_DEACTIVATE_SELECTED_TEST_DEVICES = "deactivateSelectedTestDevices";

  private static final String ARG_LABEL = "label";
  private static final String ARG_MODE = "mode";
  private static final String ARG_JSON = "json";

  private static final String TEXT_UNKNOWN_COMMAND_PREFIX = "Unknown command: ";
  private static final String TEXT_ACTIVATED_FMT = "Lifecycle activated: %s";
  private static final String TEXT_DEACTIVATED_FMT = "Lifecycle deactivated: %s";
  private static final String TEXT_DEACTIVATED_ACTIVE = "Lifecycle deactivated active session.";
  private static final String TEXT_SELECTED_TEST_SCOPE_ACTIVE =
      "active-group active - ready to run";
  private static final String TEXT_SELECTED_ACTIVE_GROUP_SCOPE_ACTIVE =
      "active-group active - ready to run";
  private static final String TEXT_SCOPE_DEACTIVATED = "group deactivated";
  private static final String TEXT_GROUP_ALREADY_INACTIVE =
      "Group already inactive. Nothing changed.";
  private static final String TEXT_ACTIVE_GROUP_LABEL = "active-group";
  private static final String TEXT_SELECTED_TEST_SCOPE_LABEL_PREFIX = "selected-test:";
  private static final String TEXT_REQUIRED_ACTIVATE_LABEL =
      "lifecycleActivate requires args.label.";
  private static final String TEXT_REQUIRED_DEACTIVATE_LABEL =
      "lifecycleDeactivate requires args.label.";
  private static final String TEXT_INVALID_MODE_PREFIX = "Invalid lifecycle mode: ";
  private static final String TEXT_ACTIVATE_BLOCKED_DISABLED =
      "Lifecycle activate blocked: robot not in enabled teleop. Enable teleop, then activate lifecycle.";

  private static final String JSON_KEY_OPERATION = "operation";
  private static final String JSON_KEY_SUCCESS = "success";
  private static final String JSON_KEY_REQUESTED_LABEL = "requestedLabel";
  private static final String JSON_KEY_SESSION_ID = "sessionId";
  private static final String JSON_KEY_MODE = "mode";
  private static final String JSON_KEY_REQUESTED_DEVICE_LABELS = "requestedDeviceLabels";
  private static final String JSON_KEY_INSTANTIATED_DEVICE_LABELS = "instantiatedDeviceLabels";
  private static final String JSON_KEY_FAILED_DEVICE_LABELS = "failedDeviceLabels";
  private static final String JSON_KEY_DEACTIVATED_DEVICE_LABELS = "deactivatedDeviceLabels";
  private static final String JSON_KEY_STATE = "state";
  private static final String JSON_KEY_ERROR_CODE = "errorCode";
  private static final String JSON_KEY_ERROR_MESSAGE = "errorMessage";
  private static final String JSON_KEY_LIFECYCLE = "lifecycle";

  private static final String OPERATION_ACTIVATE = "activate";
  private static final String OPERATION_DEACTIVATE = "deactivate";
  private static final String OPERATION_DEACTIVATE_ACTIVE = "deactivateActive";

  private static final Set<String> COMMANDS = Set.of(
      CMD_LIFECYCLE_ACTIVATE,
      CMD_LIFECYCLE_DEACTIVATE,
      CMD_LIFECYCLE_DEACTIVATE_ACTIVE,
      CMD_ACTIVATE_SELECTED_TEST_DEVICES,
      CMD_DEACTIVATE_SELECTED_TEST_DEVICES,
      CMD_SHOW_LIFECYCLE_STATE);

  /**
   * NAME
   *   Dependencies - Narrow dependency contract for lifecycle commands.
   */
  interface Dependencies {
    String parseUiArgString(JsonObject args, String key);

    Boolean parseUiArgBoolean(JsonObject args, String key);

    void applyShowResult(BridgeUiCommandResult result, String text, JsonObject json, boolean wantsJson);

    boolean isRuntimeActivationAllowed();

    ActivationResult activateLifecycle(String label, ActivationMode mode);

    ActivationResult activateSelectedTestDevices(ActivationMode mode);

    DeactivateResult deactivateLifecycle(String label);

    DeactivateResult deactivateSelectedTestDevices();

    DeactivateResult deactivateActiveLifecycle();

    String buildLifecycleStateText();

    JsonObject buildLifecycleStateJson();
  }

  private final Dependencies dependencies;

  BridgeUiLifecycleCommands(Dependencies dependencies) {
    this.dependencies = dependencies;
  }

  @Override
  public boolean handles(String commandName) {
    return COMMANDS.contains(commandName);
  }

  @Override
  public BridgeUiCommandResult execute(
      BridgeUiIngressPolicy.Ingress ingress,
      double cmdTs,
      boolean isTcp) {
    BridgeUiCommandResult result = new BridgeUiCommandResult();
    String commandName = ingress.name;
    JsonObject args = ingress.args;
    switch (commandName) {
      case CMD_LIFECYCLE_ACTIVATE:
        executeLifecycleActivate(args, result);
        break;
      case CMD_LIFECYCLE_DEACTIVATE:
        executeLifecycleDeactivate(args, result);
        break;
      case CMD_LIFECYCLE_DEACTIVATE_ACTIVE:
        executeLifecycleDeactivateActive(result);
        break;
      case CMD_ACTIVATE_SELECTED_TEST_DEVICES:
        executeActivateSelectedTestDevices(args, result);
        break;
      case CMD_DEACTIVATE_SELECTED_TEST_DEVICES:
        executeDeactivateSelectedTestDevices(result);
        break;
      case CMD_SHOW_LIFECYCLE_STATE:
        executeShowLifecycleState(args, result);
        break;
      default:
        result.ok = false;
        result.message = TEXT_UNKNOWN_COMMAND_PREFIX + commandName;
        result.outText = result.message;
        break;
    }
    return result;
  }

  private void executeLifecycleActivate(JsonObject args, BridgeUiCommandResult result) {
    if (!dependencies.isRuntimeActivationAllowed()) {
      result.ok = false;
      result.message = TEXT_ACTIVATE_BLOCKED_DISABLED;
      result.outText = result.message;
      return;
    }
    String label = dependencies.parseUiArgString(args, ARG_LABEL);
    if (label == null || label.isBlank()) {
      result.ok = false;
      result.message = TEXT_REQUIRED_ACTIVATE_LABEL;
      result.outText = result.message;
      return;
    }
    ActivationMode mode = parseMode(args, result);
    if (mode == null) {
      return;
    }
    ActivationResult activation = dependencies.activateLifecycle(label, mode);
    result.ok = activation.success();
    result.message = activation.success()
        ? successActivateMessage(activation.requestedLabel())
        : selectLifecycleErrorMessage(activation.errorCode(), activation.errorMessage());
    result.outText = result.message;
    result.outJson = buildActivationPayload(activation).toString();
  }

  private void executeActivateSelectedTestDevices(JsonObject args, BridgeUiCommandResult result) {
    if (!dependencies.isRuntimeActivationAllowed()) {
      result.ok = false;
      result.message = TEXT_ACTIVATE_BLOCKED_DISABLED;
      result.outText = result.message;
      return;
    }
    ActivationMode mode = parseMode(args, result);
    if (mode == null) {
      return;
    }
    ActivationResult activation = dependencies.activateSelectedTestDevices(mode);
    result.ok = activation.success();
    result.message = activation.success()
        ? TEXT_SELECTED_TEST_SCOPE_ACTIVE
        : selectLifecycleErrorMessage(activation.errorCode(), activation.errorMessage());
    result.outText = result.message;
    result.outJson = buildActivationPayload(activation).toString();
  }

  private void executeLifecycleDeactivate(JsonObject args, BridgeUiCommandResult result) {
    String label = dependencies.parseUiArgString(args, ARG_LABEL);
    if (label == null || label.isBlank()) {
      result.ok = false;
      result.message = TEXT_REQUIRED_DEACTIVATE_LABEL;
      result.outText = result.message;
      return;
    }
    DeactivateResult deactivation = dependencies.deactivateLifecycle(label);
    result.ok = deactivation.success();
    result.message = deactivation.success()
        ? successDeactivateMessage(deactivation.requestedLabel())
        : selectLifecycleErrorMessage(deactivation.errorCode(), deactivation.errorMessage());
    result.outText = result.message;
    result.outJson = buildDeactivatePayload(OPERATION_DEACTIVATE, deactivation).toString();
  }

  private void executeDeactivateSelectedTestDevices(BridgeUiCommandResult result) {
    DeactivateResult deactivation = dependencies.deactivateSelectedTestDevices();
    result.ok = deactivation.success();
    result.message = deactivation.success()
        ? successDeactivateActiveMessage(deactivation)
        : selectLifecycleErrorMessage(deactivation.errorCode(), deactivation.errorMessage());
    result.outText = result.message;
    result.outJson =
        buildDeactivatePayload(OPERATION_DEACTIVATE_ACTIVE, deactivation).toString();
  }

  private void executeLifecycleDeactivateActive(BridgeUiCommandResult result) {
    DeactivateResult deactivation = dependencies.deactivateActiveLifecycle();
    result.ok = deactivation.success();
    result.message = deactivation.success()
        ? successDeactivateActiveMessage(deactivation)
        : selectLifecycleErrorMessage(deactivation.errorCode(), deactivation.errorMessage());
    result.outText = result.message;
    result.outJson = buildDeactivatePayload(OPERATION_DEACTIVATE_ACTIVE, deactivation).toString();
  }

  private void executeShowLifecycleState(JsonObject args, BridgeUiCommandResult result) {
    boolean wantsJson = Boolean.TRUE.equals(dependencies.parseUiArgBoolean(args, ARG_JSON));
    dependencies.applyShowResult(
        result,
        dependencies.buildLifecycleStateText(),
        dependencies.buildLifecycleStateJson(),
        wantsJson);
  }

  private ActivationMode parseMode(JsonObject args, BridgeUiCommandResult result) {
    String rawMode = dependencies.parseUiArgString(args, ARG_MODE);
    if (rawMode == null || rawMode.isBlank()) {
      return ActivationMode.READ_ONLY;
    }
    try {
      return ActivationMode.valueOf(rawMode.trim().toUpperCase(Locale.ROOT));
    } catch (IllegalArgumentException ex) {
      result.ok = false;
      result.message = TEXT_INVALID_MODE_PREFIX + rawMode;
      result.outText = result.message;
      return null;
    }
  }

  private JsonObject buildActivationPayload(ActivationResult activation) {
    JsonObject payload = new JsonObject();
    payload.addProperty(JSON_KEY_OPERATION, OPERATION_ACTIVATE);
    payload.addProperty(JSON_KEY_SUCCESS, activation.success());
    payload.addProperty(JSON_KEY_REQUESTED_LABEL, safeText(activation.requestedLabel()));
    payload.addProperty(JSON_KEY_SESSION_ID, safeText(activation.sessionId()));
    payload.addProperty(JSON_KEY_MODE, activation.mode() != null ? activation.mode().name() : "");
    payload.add(JSON_KEY_REQUESTED_DEVICE_LABELS, toJsonArray(activation.requestedDeviceLabels()));
    payload.add(JSON_KEY_INSTANTIATED_DEVICE_LABELS, toJsonArray(activation.instantiatedDeviceLabels()));
    payload.add(JSON_KEY_FAILED_DEVICE_LABELS, toJsonArray(activation.failedDeviceLabels()));
    payload.addProperty(JSON_KEY_STATE, activation.state() != null ? activation.state().name() : "");
    payload.addProperty(JSON_KEY_ERROR_CODE, safeText(activation.errorCode()));
    payload.addProperty(JSON_KEY_ERROR_MESSAGE, safeText(activation.errorMessage()));
    payload.add(JSON_KEY_LIFECYCLE, dependencies.buildLifecycleStateJson());
    return payload;
  }

  private JsonObject buildDeactivatePayload(String operation, DeactivateResult deactivation) {
    JsonObject payload = new JsonObject();
    payload.addProperty(JSON_KEY_OPERATION, operation);
    payload.addProperty(JSON_KEY_SUCCESS, deactivation.success());
    payload.addProperty(JSON_KEY_REQUESTED_LABEL, safeText(deactivation.requestedLabel()));
    payload.addProperty(JSON_KEY_SESSION_ID, safeText(deactivation.sessionId()));
    payload.add(JSON_KEY_DEACTIVATED_DEVICE_LABELS, toJsonArray(deactivation.deactivatedDeviceLabels()));
    payload.addProperty(JSON_KEY_STATE, deactivation.state() != null ? deactivation.state().name() : "");
    payload.addProperty(JSON_KEY_ERROR_CODE, safeText(deactivation.errorCode()));
    payload.addProperty(JSON_KEY_ERROR_MESSAGE, safeText(deactivation.errorMessage()));
    payload.add(JSON_KEY_LIFECYCLE, dependencies.buildLifecycleStateJson());
    return payload;
  }

  private JsonArray toJsonArray(java.util.List<String> values) {
    JsonArray array = new JsonArray();
    if (values == null) {
      return array;
    }
    for (String value : values) {
      if (value != null && !value.isBlank()) {
        array.add(value);
      }
    }
    return array;
  }

  private String selectLifecycleErrorMessage(String errorCode, String errorMessage) {
    if (errorMessage != null && !errorMessage.isBlank()) {
      return errorMessage;
    }
    if (errorCode != null && !errorCode.isBlank()) {
      return errorCode;
    }
    return "";
  }

  private String successActivateMessage(String requestedLabel) {
    if (TEXT_ACTIVE_GROUP_LABEL.equals(requestedLabel)) {
      return TEXT_SELECTED_ACTIVE_GROUP_SCOPE_ACTIVE;
    }
    if (requestedLabel != null && requestedLabel.startsWith(TEXT_SELECTED_TEST_SCOPE_LABEL_PREFIX)) {
      return TEXT_SELECTED_TEST_SCOPE_ACTIVE;
    }
    return String.format(TEXT_ACTIVATED_FMT, requestedLabel);
  }

  private String successDeactivateActiveMessage(DeactivateResult deactivation) {
    if (deactivation == null) {
      return TEXT_SCOPE_DEACTIVATED;
    }
    if (deactivation.deactivatedDeviceLabels() == null || deactivation.deactivatedDeviceLabels().isEmpty()) {
      return TEXT_GROUP_ALREADY_INACTIVE;
    }
    return TEXT_SCOPE_DEACTIVATED;
  }

  private String successDeactivateMessage(String requestedLabel) {
    if (TEXT_ACTIVE_GROUP_LABEL.equals(requestedLabel)
        || (requestedLabel != null
            && requestedLabel.startsWith(TEXT_SELECTED_TEST_SCOPE_LABEL_PREFIX))) {
      return TEXT_SCOPE_DEACTIVATED;
    }
    return String.format(TEXT_DEACTIVATED_FMT, requestedLabel);
  }

  private String safeText(String value) {
    return value != null ? value : "";
  }
}
