package frc.robot;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import org.junit.jupiter.api.Test;

class BuildInfoTest {

  @Test
  void buildRevisionConstantIsPresent() {
    assertFalse(BuildInfo.BUILD_REVISION.isBlank());
    assertEquals("build-revision", BuildInfo.BUILD_LABEL_REVISION);
    assertFalse(BuildInfo.BUILD_WORKSPACE_REVISION.isBlank());
    assertEquals("workspace-revision", BuildInfo.BUILD_LABEL_WORKSPACE_REVISION);
    assertFalse(BuildInfo.BUILD_CODE_REVISION.isBlank());
    assertEquals("code-revision", BuildInfo.BUILD_LABEL_CODE_REVISION);
    assertFalse(BuildInfo.BUILD_TIMESTAMP.isBlank());
    assertEquals("build-time", BuildInfo.BUILD_LABEL_TIME);
    assertFalse(BuildInfo.BUILD_COMMIT_TIMESTAMP.isBlank());
    assertEquals("commit-time", BuildInfo.BUILD_LABEL_COMMIT_TIME);
  }

  @Test
  void formatBuildLineIncludesRevisionValue() {
    String line = BuildInfo.formatBuildLine(BuildInfo.BUILD_LABEL_REVISION, BuildInfo.BUILD_REVISION);

    assertTrue(line.startsWith(BuildInfo.BUILD_LABEL_REVISION + BuildInfo.BUILD_SEPARATOR));
    assertTrue(line.endsWith(BuildInfo.BUILD_REVISION));
  }

  @Test
  void bootRevisionLineIncludesBootPrefixAndRevision() {
    String line = BuildInfo.buildBootRevisionLine();

    assertTrue(line.startsWith(BuildInfo.BOOT_PREFIX));
    assertTrue(line.endsWith(BuildInfo.BUILD_REVISION));
  }

  @Test
  void bootCodeRevisionLineIncludesBootPrefixAndCodeRevision() {
    String line = BuildInfo.buildBootCodeRevisionLine();

    assertTrue(line.startsWith(BuildInfo.BOOT_PREFIX));
    assertTrue(line.endsWith(BuildInfo.BUILD_CODE_REVISION));
  }

  @Test
  void bootWorkspaceRevisionLineIncludesBootPrefixAndWorkspaceRevision() {
    String line = BuildInfo.buildBootWorkspaceRevisionLine();

    assertTrue(line.startsWith(BuildInfo.BOOT_PREFIX));
    assertTrue(line.endsWith(BuildInfo.BUILD_WORKSPACE_REVISION));
  }
}
