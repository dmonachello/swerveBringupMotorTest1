# Bringup System ER Diagram

Purpose: Show a database-style ERD view of the bringup profiles JSON structure.

```mermaid
erDiagram
    BRINGUP_SYSTEM ||--o{ PROFILE : contains
    BRINGUP_SYSTEM ||--o{ DEVICE_DEFINITION : devices_table
    PROFILE ||--o{ DEVICE_DEFINITION : references_by_label
    BRINGUP_SYSTEM ||--o| DIAGRAM : includes
    DIAGRAM ||--o{ DIAGRAM_PROFILE : contains
    DIAGRAM_PROFILE ||--o{ NODE : has
    BRINGUP_SYSTEM ||--o| BRIDGE_CONFIG : includes
    BRIDGE_CONFIG ||--o{ BRIDGE_PROFILE : byProfile
    BRIDGE_PROFILE ||--o{ GROUP : contains
    GROUP ||--o{ MEMBER : has
    GROUP ||--o{ BINDING : has

    BRINGUP_SYSTEM {
        int schema_version
        string data_version
        string data_hash
        string default_profile
    }

    PROFILE {
        string name
        string[] devices
    }

    DEVICE_DEFINITION {
        string label
        string deviceInterface
        int manufacturer
        int deviceType
        int id
        string model
        string type
        bool invert
        string[] attachments
        string[] tags
        bool terminator
    }

    DIAGRAM {
        string name
    }

    DIAGRAM_PROFILE {
        string profile_name
        int busCount
        float busSpacing
        float panY
        float zoom
    }

    NODE {
        string nodeType
        string category
        string label
        int bus
        int row
        float x
        float freeY
        float scale
    }

    BRIDGE_CONFIG {
        int schemaVersion
        string generatedAt
    }

    BRIDGE_PROFILE {
        string profile_name
    }

    GROUP {
        string name
        bool enabled
    }

    MEMBER {
        string device
        bool enabled
    }

    BINDING {
        string input
        string kind
        float value
    }
```

Notes:
- This ERD is a conceptual mapping of JSON objects to relational entities.
- Root schema_version is 4.
- Profiles only store device labels; identity fields live in the devices table.
- `DEVICE_DEFINITION.id` is the single interface-local identifier field across CAN, DIO, USB, and similar interfaces.
- Topology `NODE` records for `nodeType=device` resolve device identity by `label` and do not store a duplicated hardware id.
- Optional JSON fields are shown without nullable markers to keep the ERD compact.
