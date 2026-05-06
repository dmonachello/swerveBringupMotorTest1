package frc.robot.tests.dsl;

import com.google.gson.annotations.SerializedName;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

/**
 * NAME
 *   DslModels - JSON model classes for normalized DSL tests.
 */
public final class DslModels {
  private DslModels() {}

  public static final class DslTestsRoot {
    @SerializedName("schemaVersion")
    public int schemaVersion = 1;
    @SerializedName("testsByName")
    public Map<String, DslTestEntry> testsByName;
    @SerializedName("testSets")
    public Map<String, List<String>> testSets;
    @SerializedName("defaultSet")
    public String defaultSet = "default";
  }

  public static final class DslTestEntry {
    public String source = "";
    public String sourceHash = "";
    public DslNormalizedTest normalized;
  }

  public static final class DslNormalizedTest {
    public String name = "";
    public List<DslDeviceRef> devices = new ArrayList<>();
    @SerializedName("unsafeExit")
    public List<DslUnsafeExit> unsafeExit = new ArrayList<>();
    public DslPhase init = new DslPhase();
    public DslPhase main = new DslPhase();
    public DslPhase close = new DslPhase();
  }

  public static final class DslDeviceRef {
    public String name = "";
  }

  public static final class DslReference {
    public String device = "";
    public String signal = "";
    public String text = "";
  }

  public static final class DslLiteral {
    public Object value;
    @SerializedName("valueType")
    public String valueType = "";
  }

  public static final class DslCondition {
    @SerializedName("id")
    public String id = "";
    public String kind = "";
    public String text = "";
    public DslReference reference = new DslReference();
    public String operator;
    public DslLiteral literal;
  }

  public static final class DslSetStatement {
    @SerializedName("id")
    public String id = "";
    public String text = "";
    public DslReference target = new DslReference();
    public DslLiteral literal = new DslLiteral();
  }

  public static final class DslClearStatement {
    @SerializedName("id")
    public String id = "";
    public String text = "";
    public DslReference target = new DslReference();
  }

  public static final class DslUnsafeExit {
    @SerializedName("id")
    public String id = "";
    public String text = "";
    public DslReference target = new DslReference();
  }

  public static final class DslPhase {
    public List<DslSetStatement> sets = new ArrayList<>();
    public List<DslClearStatement> clears = new ArrayList<>();
    public List<DslCondition> aborts = new ArrayList<>();
    public List<DslCondition> successes = new ArrayList<>();
    public List<DslCondition> untils = new ArrayList<>();
    public List<DslCondition> requires = new ArrayList<>();
  }
}
