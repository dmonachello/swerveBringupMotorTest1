package frc.robot.status.generated;

/** Generated file. Do not edit manually. */
public final class StatusCatalogGenerated {
  public static final String GENERATED_FROM_HASH = "38ceaf85de3b06b2fc8f854415ceb5506f44f104387d4754b94c998794e79964";

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
      public static final int FAILED = 3;
      public static final int INTERNAL_ERROR = 4;
      public static final int NOT_SUPPORTED = 5;
      private EXECUTOR() {}
    }
    public static final class DEVICE {
      public static final int INVALID_FIELD = 1;
      public static final int NOT_DEFINED = 2;
      public static final int NOT_FOUND = 3;
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
  public static final int SS__EXECUTOR__FAILED = encode(Severity.ERROR, Facility.EXECUTOR, Message.EXECUTOR.FAILED);
  public static final int SS__EXECUTOR__INTERNAL_ERROR = encode(Severity.ERROR, Facility.EXECUTOR, Message.EXECUTOR.INTERNAL_ERROR);
  public static final int SS__EXECUTOR__NOT_SUPPORTED = encode(Severity.ERROR, Facility.EXECUTOR, Message.EXECUTOR.NOT_SUPPORTED);
  public static final int SS__DEVICE__INVALID_FIELD = encode(Severity.ERROR, Facility.DEVICE, Message.DEVICE.INVALID_FIELD);
  public static final int SS__DEVICE__NOT_DEFINED = encode(Severity.ERROR, Facility.DEVICE, Message.DEVICE.NOT_DEFINED);
  public static final int SS__DEVICE__NOT_FOUND = encode(Severity.ERROR, Facility.DEVICE, Message.DEVICE.NOT_FOUND);
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
