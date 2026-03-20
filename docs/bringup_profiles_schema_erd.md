# Bringup Profiles ER Diagram

Purpose: Show a database-style ERD view of the bringup profiles JSON structure.

```mermaid
erDiagram
    BRINGUP_PROFILES ||--o{ PROFILE : contains
    PROFILE ||--o{ DEVICE_ENTRY : has
    DEVICE_ENTRY ||--o| LIMIT_CONFIG : uses
    BRINGUP_PROFILES ||--o| DIAGRAM : includes
    DIAGRAM ||--o{ DIAGRAM_PROFILE : contains
    DIAGRAM_PROFILE ||--o{ NODE : has

    BRINGUP_PROFILES {
        int schema_version
        string data_version
        string data_hash
        string default_profile
    }

    PROFILE {
        string name
        string section
    }

    DEVICE_ENTRY {
        int id
        string label
        string vendor
        string type
        string motor
        bool terminator
    }

    LIMIT_CONFIG {
        int fwdDio
        int revDio
        bool invert
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
        int id
        int bus
        int row
        float x
        float freeY
        float scale
    }
```

Notes:
- This ERD is a conceptual mapping of JSON objects to relational entities.
- `PROFILE.section` represents which list a device came from (e.g., `neos`, `krakens`, `devices`, `pdh`).
- Optional JSON fields are shown without nullable markers to keep the ERD compact.
