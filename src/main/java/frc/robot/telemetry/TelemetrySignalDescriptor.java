package frc.robot.telemetry;

/**
 * NAME
 *   TelemetrySignalDescriptor - Typed identity and display metadata for one signal stream.
 *
 * DESCRIPTION
 *   Describes a robot-local signal without exposing REST, JSON, WPILOG, or
 *   graph-widget types.
 */
public record TelemetrySignalDescriptor(
    String signalDefinitionKey,
    String signalId,
    String sourceInstanceId,
    String subjectKey,
    String deviceLabel,
    String signalName,
    TelemetryValueKind valueKind,
    TelemetryUnit unit,
    TelemetryEngineeringDimension engineeringDimension,
    long nominalCadenceUs,
    long staleAfterUs,
    boolean graphable) {
  TelemetrySignalDescriptor withSourceInstance(
      String replacementSourceInstanceId,
      String replacementSignalId) {
    return new TelemetrySignalDescriptor(
        signalDefinitionKey,
        replacementSignalId,
        replacementSourceInstanceId,
        subjectKey,
        deviceLabel,
        signalName,
        valueKind,
        unit,
        engineeringDimension,
        nominalCadenceUs,
        staleAfterUs,
        graphable);
  }
}
