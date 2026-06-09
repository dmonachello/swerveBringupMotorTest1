"""
NAME
    robot_test_dsl - Host-side parser/compiler/validator for the robot test DSL.

DESCRIPTION
    Provides source parsing, normalized JSON compilation, and validation for the
    execution DSL defined by ROBOT_DIAGNOSTIC_TEST_DSL_SPEC_V0_3.md.
"""

from .model import (
    DSL_SCHEMA_VERSION,
    DEFAULT_TEST_SET,
    BUILTIN_TIMER_NAME,
    RobotTestDslStore,
    RobotTestDslEntry,
    RobotTestDslNormalized,
    RobotTestDslDeviceRef,
    RobotTestDslReference,
    RobotTestDslLiteral,
    RobotTestDslCondition,
    RobotTestDslSetStatement,
    RobotTestDslClearStatement,
    RobotTestDslUnsafeExit,
    RobotTestDslPhase,
)
from .compiler import compile_source, compile_store_sources
from .serializer import store_from_payload, store_to_payload, source_hash
from .validator import ValidationIssue, ValidationResult, validate_entry, validate_store
from .service import (
    DslImportResult,
    DslServiceError,
    cleanup_stale_tests_in_store,
    device_catalog,
    import_test_into_root_payload,
    issue_detail,
    issue_line_excerpt,
    render_validation_text,
    resolve_profile_test_names,
    signal_catalog,
    store_from_root_payload,
    validate_store_for_profile,
    write_store_to_root_payload,
)

__all__ = [
    "DSL_SCHEMA_VERSION",
    "DEFAULT_TEST_SET",
    "BUILTIN_TIMER_NAME",
    "RobotTestDslStore",
    "RobotTestDslEntry",
    "RobotTestDslNormalized",
    "RobotTestDslDeviceRef",
    "RobotTestDslReference",
    "RobotTestDslLiteral",
    "RobotTestDslCondition",
    "RobotTestDslSetStatement",
    "RobotTestDslClearStatement",
    "RobotTestDslUnsafeExit",
    "RobotTestDslPhase",
    "compile_source",
    "compile_store_sources",
    "store_from_payload",
    "store_to_payload",
    "source_hash",
    "ValidationIssue",
    "ValidationResult",
    "validate_entry",
    "validate_store",
    "DslImportResult",
    "DslServiceError",
    "cleanup_stale_tests_in_store",
    "device_catalog",
    "import_test_into_root_payload",
    "issue_detail",
    "issue_line_excerpt",
    "render_validation_text",
    "resolve_profile_test_names",
    "signal_catalog",
    "store_from_root_payload",
    "validate_store_for_profile",
    "write_store_to_root_payload",
]
