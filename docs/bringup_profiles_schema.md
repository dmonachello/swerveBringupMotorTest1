# Bringup Profiles Schema Diagram

Purpose: Visualize the structure of `data/bringup_profiles.json` without showing live data.

```mermaid
classDiagram
    class BringupProfiles {
        int schema_version (2)
        string data_version
        string data_hash
        string default_profile
        Map~string, Profile~ profiles
        Diagram? diagram
    }

    class Profile {
        DeviceEntry[] neos
        DeviceEntry[] neo550s
        DeviceEntry[] flexes
        DeviceEntry[] krakens
        DeviceEntry[] falcons
        DeviceEntry[] cancoders
        DeviceEntry[] candles
        DeviceEntry[] devices
        DeviceEntry? pdh
        DeviceEntry? pdp
        DeviceEntry? pigeon
        DeviceEntry? roborio
        object? notes
        object? unknown
    }

    class DeviceEntry {
        int id
        string label
        string vendor?
        string type?
        string motor?
        LimitConfig? limits
        bool? terminator
        string[]? tags
    }

    class LimitConfig {
        int fwdDio
        int revDio
        bool invert
    }

    class Diagram {
        Map~string, DiagramProfile~ profiles
    }

    class DiagramProfile {
        int busCount
        float busSpacing
        float panY
        float zoom
        Node[] nodes
        object? ethernetLinks
        object? canLinks
        object? deviceLinks
    }

    class Node {
        string nodeType
        string category
        string label
        int id
        int bus
        int row
        float x
        float? freeY
        float? scale
        string[]? tags
    }

    BringupProfiles "1" --> "many" Profile : profiles
    Profile "1" --> "many" DeviceEntry : lists/singletons
    DeviceEntry "0..1" --> LimitConfig
    BringupProfiles "0..1" --> Diagram : diagram
    Diagram "1" --> "many" DiagramProfile : profiles
    DiagramProfile "1" --> "many" Node : nodes
```

Notes:
- `schema_version`, `data_version`, and `data_hash` are required at the root (schema_version=2).
- `devices` entries require `vendor` and `type`.
- `diagram` is editor-only and ignored by robot/PC tools.
