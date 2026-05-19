package frc.robot.tests.dsl.signals;

/**
 * NAME
 *   DslSignalMeta - Immutable metadata for one DSL-visible device signal.
 *
 * DESCRIPTION
 *   Captures the validator/runtime contract exported to the generated host-side
 *   signal catalog. Device-type providers return these entries to the central
 *   registry.
 */
public record DslSignalMeta(
    String valueType,
    boolean readable,
    boolean writable,
    boolean clearable,
    Double safeValue,
    boolean safeProvider,
    boolean unsafeExitAllowed) {}
