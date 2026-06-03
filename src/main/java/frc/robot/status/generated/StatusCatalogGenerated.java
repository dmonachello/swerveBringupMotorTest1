package frc.robot.status.generated;

/** AUTO-GENERATED FILE. Do not modify; changes will be lost on regeneration. */
public final class StatusCatalogGenerated {
  public static final String GENERATED_FROM_HASH = "de338bf268bea7597b64e340be5068b543130eabc4b0cbee1a318f4948108368";

  public static final class Severity {
    public static final int SUCCESS = 0;
    public static final int INFO = 1;
    public static final int WARNING = 2;
    public static final int ERROR = 3;
    public static final int FATAL = 4;
    private Severity() {}
  }

  public static final class Facility {
    public static final int CLI_PARSER = 1;
    public static final int CLI_VALIDATOR = 2;
    public static final int EXECUTOR = 3;
    public static final int DEVICE = 4;
    public static final int GROUP = 5;
    public static final int INPUT_BINDING = 6;
    public static final int NETWORK = 7;
    public static final int CONFIG = 8;
    private Facility() {}
  }

  public static final class Message {
    public static final class CLI_PARSER {
      public static final int INVALID_FLAG = 1;
      public static final int INVALID_SYNTAX = 2;
      public static final int MISSING_ARGUMENT = 3;
      public static final int UNKNOWN_COMMAND = 4;
      private CLI_PARSER() {}
    }
    public static final class CLI_VALIDATOR {
      public static final int INVALID_VALUE = 1;
      public static final int OUT_OF_RANGE = 2;
      public static final int REQUIRED = 3;
      private CLI_VALIDATOR() {}
    }
    public static final class EXECUTOR {
      public static final int SUCCESS = 1;
      public static final int CANCELLED = 2;
      public static final int COMPLETED_WITH_WARNINGS = 3;
      public static final int FAILED = 4;
      public static final int INTERNAL_ERROR = 5;
      public static final int NOT_SUPPORTED = 6;
      private EXECUTOR() {}
    }
    public static final class DEVICE {
      public static final int PRESENT = 1;
      public static final int DEGRADED = 2;
      public static final int TELEMETRY_INVALID = 3;
      public static final int FAULTS_ACTIVE = 4;
      public static final int WARNINGS_ACTIVE = 5;
      public static final int COMMUNICATION_WEAK = 6;
      public static final int ABSENT = 7;
      public static final int INVALID_FIELD = 8;
      public static final int NOT_DEFINED = 9;
      public static final int NOT_FOUND = 10;
      public static final int PROBE_UNSUPPORTED_MODEL = 11;
      public static final int PROBE_INVALID_TARGET = 12;
      public static final int PROBE_TIMEOUT = 13;
      public static final int CAN_DISCONNECTED = 14;
      public static final int PROBE_EXCEPTION = 15;
      private DEVICE() {}
    }
    public static final class GROUP {
      public static final int EMPTY = 1;
      public static final int BINDING_INVALID = 2;
      public static final int MEMBER_MISSING = 3;
      public static final int NOT_FOUND = 4;
      private GROUP() {}
    }
    public static final class INPUT_BINDING {
      public static final int INVALID = 1;
      public static final int NOT_FOUND = 2;
      private INPUT_BINDING() {}
    }
    public static final class NETWORK {
      public static final int NOT_CONNECTED = 1;
      public static final int COMMAND_SEND_FAILED = 2;
      public static final int CONNECT_FAILED = 3;
      public static final int HANDSHAKE_FAILED = 4;
      public static final int ROBOT_UNAVAILABLE = 5;
      public static final int TIMEOUT = 6;
      private NETWORK() {}
    }
    public static final class CONFIG {
      public static final int VALID = 1;
      public static final int IMPORTED = 2;
      public static final int MERGED = 3;
      public static final int SAVED = 4;
      public static final int DUPLICATE_LABEL = 5;
      public static final int INVALID = 6;
      public static final int MISSING_DEVICE = 7;
      public static final int NOT_LOADED = 8;
      public static final int PROFILE_REQUIRED = 9;
      private CONFIG() {}
    }
    private Message() {}
  }

  public static int encode(int severity, int facility, int message) {
    return (facility << 16) | (message << 3) | severity;
  }

  public static final int SS__CLI_PARSER__INVALID_FLAG = encode(Severity.ERROR, Facility.CLI_PARSER, Message.CLI_PARSER.INVALID_FLAG);
  public static final int SS__CLI_PARSER__INVALID_SYNTAX = encode(Severity.ERROR, Facility.CLI_PARSER, Message.CLI_PARSER.INVALID_SYNTAX);
  public static final int SS__CLI_PARSER__MISSING_ARGUMENT = encode(Severity.ERROR, Facility.CLI_PARSER, Message.CLI_PARSER.MISSING_ARGUMENT);
  public static final int SS__CLI_PARSER__UNKNOWN_COMMAND = encode(Severity.ERROR, Facility.CLI_PARSER, Message.CLI_PARSER.UNKNOWN_COMMAND);
  public static final int SS__CLI_VALIDATOR__INVALID_VALUE = encode(Severity.ERROR, Facility.CLI_VALIDATOR, Message.CLI_VALIDATOR.INVALID_VALUE);
  public static final int SS__CLI_VALIDATOR__OUT_OF_RANGE = encode(Severity.ERROR, Facility.CLI_VALIDATOR, Message.CLI_VALIDATOR.OUT_OF_RANGE);
  public static final int SS__CLI_VALIDATOR__REQUIRED = encode(Severity.ERROR, Facility.CLI_VALIDATOR, Message.CLI_VALIDATOR.REQUIRED);
  public static final int SS__EXECUTOR__SUCCESS = encode(Severity.SUCCESS, Facility.EXECUTOR, Message.EXECUTOR.SUCCESS);
  public static final int SS__EXECUTOR__CANCELLED = encode(Severity.WARNING, Facility.EXECUTOR, Message.EXECUTOR.CANCELLED);
  public static final int SS__EXECUTOR__COMPLETED_WITH_WARNINGS = encode(Severity.WARNING, Facility.EXECUTOR, Message.EXECUTOR.COMPLETED_WITH_WARNINGS);
  public static final int SS__EXECUTOR__FAILED = encode(Severity.ERROR, Facility.EXECUTOR, Message.EXECUTOR.FAILED);
  public static final int SS__EXECUTOR__INTERNAL_ERROR = encode(Severity.ERROR, Facility.EXECUTOR, Message.EXECUTOR.INTERNAL_ERROR);
  public static final int SS__EXECUTOR__NOT_SUPPORTED = encode(Severity.ERROR, Facility.EXECUTOR, Message.EXECUTOR.NOT_SUPPORTED);
  public static final int SS__DEVICE__PRESENT = encode(Severity.SUCCESS, Facility.DEVICE, Message.DEVICE.PRESENT);
  public static final int SS__DEVICE__DEGRADED = encode(Severity.WARNING, Facility.DEVICE, Message.DEVICE.DEGRADED);
  public static final int SS__DEVICE__TELEMETRY_INVALID = encode(Severity.WARNING, Facility.DEVICE, Message.DEVICE.TELEMETRY_INVALID);
  public static final int SS__DEVICE__FAULTS_ACTIVE = encode(Severity.WARNING, Facility.DEVICE, Message.DEVICE.FAULTS_ACTIVE);
  public static final int SS__DEVICE__WARNINGS_ACTIVE = encode(Severity.WARNING, Facility.DEVICE, Message.DEVICE.WARNINGS_ACTIVE);
  public static final int SS__DEVICE__COMMUNICATION_WEAK = encode(Severity.WARNING, Facility.DEVICE, Message.DEVICE.COMMUNICATION_WEAK);
  public static final int SS__DEVICE__ABSENT = encode(Severity.ERROR, Facility.DEVICE, Message.DEVICE.ABSENT);
  public static final int SS__DEVICE__INVALID_FIELD = encode(Severity.ERROR, Facility.DEVICE, Message.DEVICE.INVALID_FIELD);
  public static final int SS__DEVICE__NOT_DEFINED = encode(Severity.ERROR, Facility.DEVICE, Message.DEVICE.NOT_DEFINED);
  public static final int SS__DEVICE__NOT_FOUND = encode(Severity.ERROR, Facility.DEVICE, Message.DEVICE.NOT_FOUND);
  public static final int SS__DEVICE__PROBE_UNSUPPORTED_MODEL = encode(Severity.ERROR, Facility.DEVICE, Message.DEVICE.PROBE_UNSUPPORTED_MODEL);
  public static final int SS__DEVICE__PROBE_INVALID_TARGET = encode(Severity.ERROR, Facility.DEVICE, Message.DEVICE.PROBE_INVALID_TARGET);
  public static final int SS__DEVICE__PROBE_TIMEOUT = encode(Severity.ERROR, Facility.DEVICE, Message.DEVICE.PROBE_TIMEOUT);
  public static final int SS__DEVICE__CAN_DISCONNECTED = encode(Severity.ERROR, Facility.DEVICE, Message.DEVICE.CAN_DISCONNECTED);
  public static final int SS__DEVICE__PROBE_EXCEPTION = encode(Severity.ERROR, Facility.DEVICE, Message.DEVICE.PROBE_EXCEPTION);
  public static final int SS__GROUP__EMPTY = encode(Severity.WARNING, Facility.GROUP, Message.GROUP.EMPTY);
  public static final int SS__GROUP__BINDING_INVALID = encode(Severity.ERROR, Facility.GROUP, Message.GROUP.BINDING_INVALID);
  public static final int SS__GROUP__MEMBER_MISSING = encode(Severity.ERROR, Facility.GROUP, Message.GROUP.MEMBER_MISSING);
  public static final int SS__GROUP__NOT_FOUND = encode(Severity.ERROR, Facility.GROUP, Message.GROUP.NOT_FOUND);
  public static final int SS__INPUT_BINDING__INVALID = encode(Severity.ERROR, Facility.INPUT_BINDING, Message.INPUT_BINDING.INVALID);
  public static final int SS__INPUT_BINDING__NOT_FOUND = encode(Severity.ERROR, Facility.INPUT_BINDING, Message.INPUT_BINDING.NOT_FOUND);
  public static final int SS__NETWORK__NOT_CONNECTED = encode(Severity.WARNING, Facility.NETWORK, Message.NETWORK.NOT_CONNECTED);
  public static final int SS__NETWORK__COMMAND_SEND_FAILED = encode(Severity.ERROR, Facility.NETWORK, Message.NETWORK.COMMAND_SEND_FAILED);
  public static final int SS__NETWORK__CONNECT_FAILED = encode(Severity.ERROR, Facility.NETWORK, Message.NETWORK.CONNECT_FAILED);
  public static final int SS__NETWORK__HANDSHAKE_FAILED = encode(Severity.ERROR, Facility.NETWORK, Message.NETWORK.HANDSHAKE_FAILED);
  public static final int SS__NETWORK__ROBOT_UNAVAILABLE = encode(Severity.ERROR, Facility.NETWORK, Message.NETWORK.ROBOT_UNAVAILABLE);
  public static final int SS__NETWORK__TIMEOUT = encode(Severity.ERROR, Facility.NETWORK, Message.NETWORK.TIMEOUT);
  public static final int SS__CONFIG__VALID = encode(Severity.SUCCESS, Facility.CONFIG, Message.CONFIG.VALID);
  public static final int SS__CONFIG__IMPORTED = encode(Severity.INFO, Facility.CONFIG, Message.CONFIG.IMPORTED);
  public static final int SS__CONFIG__MERGED = encode(Severity.INFO, Facility.CONFIG, Message.CONFIG.MERGED);
  public static final int SS__CONFIG__SAVED = encode(Severity.INFO, Facility.CONFIG, Message.CONFIG.SAVED);
  public static final int SS__CONFIG__DUPLICATE_LABEL = encode(Severity.ERROR, Facility.CONFIG, Message.CONFIG.DUPLICATE_LABEL);
  public static final int SS__CONFIG__INVALID = encode(Severity.ERROR, Facility.CONFIG, Message.CONFIG.INVALID);
  public static final int SS__CONFIG__MISSING_DEVICE = encode(Severity.ERROR, Facility.CONFIG, Message.CONFIG.MISSING_DEVICE);
  public static final int SS__CONFIG__NOT_LOADED = encode(Severity.ERROR, Facility.CONFIG, Message.CONFIG.NOT_LOADED);
  public static final int SS__CONFIG__PROFILE_REQUIRED = encode(Severity.ERROR, Facility.CONFIG, Message.CONFIG.PROFILE_REQUIRED);

  private StatusCatalogGenerated() {}
}
