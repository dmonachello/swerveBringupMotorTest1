package frc.robot.telemetry;

/**
 * NAME
 *   TelemetryUnit - Canonical unit and dimension for sampled telemetry.
 *
 * DESCRIPTION
 *   Keeps unit, dimension, and value-kind metadata consistent at registration
 *   time so graph consumers never infer meaning from a signal name.
 */
public enum TelemetryUnit {
  UNSPECIFIED("unspecified", "", TelemetryEngineeringDimension.UNSPECIFIED, TelemetryValueKind.NUMBER),
  VOLT("volts", "V", TelemetryEngineeringDimension.ELECTRIC_POTENTIAL, TelemetryValueKind.NUMBER),
  AMPERE("amperes", "A", TelemetryEngineeringDimension.ELECTRIC_CURRENT, TelemetryValueKind.NUMBER),
  RPM("revolutions per minute", "rpm", TelemetryEngineeringDimension.ROTATIONAL_VELOCITY, TelemetryValueKind.NUMBER),
  METER_PER_SECOND("meters per second", "m/s", TelemetryEngineeringDimension.LINEAR_VELOCITY, TelemetryValueKind.NUMBER),
  REVOLUTION("revolutions", "rev", TelemetryEngineeringDimension.ROTATIONAL_POSITION, TelemetryValueKind.NUMBER),
  CELSIUS("degrees Celsius", "°C", TelemetryEngineeringDimension.TEMPERATURE, TelemetryValueKind.NUMBER),
  DUTY_RATIO("normalized duty ratio", "1", TelemetryEngineeringDimension.DUTY_CYCLE, TelemetryValueKind.NUMBER),
  BOOLEAN("boolean", "", TelemetryEngineeringDimension.LOGIC, TelemetryValueKind.BOOLEAN);

  private final String canonicalName;
  private final String symbol;
  private final TelemetryEngineeringDimension dimension;
  private final TelemetryValueKind valueKind;

  TelemetryUnit(
      String canonicalName,
      String symbol,
      TelemetryEngineeringDimension dimension,
      TelemetryValueKind valueKind) {
    this.canonicalName = canonicalName;
    this.symbol = symbol;
    this.dimension = dimension;
    this.valueKind = valueKind;
  }

  public String canonicalName() {
    return canonicalName;
  }

  public String symbol() {
    return symbol;
  }

  public TelemetryEngineeringDimension dimension() {
    return dimension;
  }

  public TelemetryValueKind valueKind() {
    return valueKind;
  }
}
