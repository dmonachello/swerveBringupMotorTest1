package frc.robot.diag.input;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

/**
 * NAME
 *   InputSensorStateModel - Shared profile-scoped input/sensor state view-model.
 *
 * DESCRIPTION
 *   Carries sectioned rows and display-ready field entries for report and UI
 *   surfaces that need the same current-profile input/sensor state contract.
 */
public final class InputSensorStateModel {
  public static final String CONFIDENCE_HIGH = "HIGH";
  public static final String CONFIDENCE_MEDIUM = "MEDIUM";
  public static final String CONFIDENCE_LOW = "LOW";
  public static final String CONFIDENCE_UNKNOWN = "UNKNOWN";

  public final List<Section> sections;

  /**
   * NAME
   *   InputSensorStateModel - Construct one immutable view-model.
   *
   * PARAMETERS
   *   sections - ordered section list for presentation.
   */
  public InputSensorStateModel(List<Section> sections) {
    this.sections = sections != null
        ? Collections.unmodifiableList(new ArrayList<>(sections))
        : Collections.emptyList();
  }

  /**
   * NAME
   *   Section - One display section grouping related device families.
   */
  public static final class Section {
    public final String key;
    public final String title;
    public final List<Row> rows;

    /**
     * NAME
     *   Section - Construct one display section.
     *
     * PARAMETERS
     *   key - stable section identifier.
     *   title - operator-facing section title.
     *   rows - ordered rows belonging to the section.
     */
    public Section(String key, String title, List<Row> rows) {
      this.key = key != null ? key : "";
      this.title = title != null ? title : "";
      this.rows = rows != null
          ? Collections.unmodifiableList(new ArrayList<>(rows))
          : Collections.emptyList();
    }
  }

  /**
   * NAME
   *   Row - One supported input/sensor device row.
   */
  public static final class Row {
    public final String label;
    public final String family;
    public final String model;
    public final boolean present;
    public final String stateConfidence;
    public final String notes;
    public final boolean selected;
    public final List<Field> fields;

    /**
     * NAME
     *   Row - Construct one device row.
     *
     * PARAMETERS
     *   label - configured device label.
     *   family - canonical family name.
     *   model - concrete model text when available.
     *   present - runtime-local presence state.
     *   stateConfidence - operator-facing confidence token.
     *   notes - optional operator-facing note text.
     *   selected - whether the row matches the shared selected device.
     *   fields - ordered display fields for the row.
     */
    public Row(
        String label,
        String family,
        String model,
        boolean present,
        String stateConfidence,
        String notes,
        boolean selected,
        List<Field> fields) {
      this.label = label != null ? label : "";
      this.family = family != null ? family : "";
      this.model = model != null ? model : "";
      this.present = present;
      this.stateConfidence = stateConfidence != null ? stateConfidence : CONFIDENCE_UNKNOWN;
      this.notes = notes != null ? notes : "";
      this.selected = selected;
      this.fields = fields != null
          ? Collections.unmodifiableList(new ArrayList<>(fields))
          : Collections.emptyList();
    }
  }

  /**
   * NAME
   *   Field - One ordered display field for a row.
   */
  public static final class Field {
    public final String key;
    public final String text;

    /**
     * NAME
     *   Field - Construct one display field.
     *
     * PARAMETERS
     *   key - stable field identifier.
     *   text - display-ready text fragment such as key=value.
     */
    public Field(String key, String text) {
      this.key = key != null ? key : "";
      this.text = text != null ? text : "";
    }
  }
}
