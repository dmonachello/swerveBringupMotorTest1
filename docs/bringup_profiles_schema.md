# Bringup System Schema Diagram

Purpose: Visualize the structure of `data/bringup_system.json` without showing live data.

```mermaid
classDiagram
    class BringupSystem {
        int schema_version
        string data_version
        string data_hash
        string default_profile
        DeviceDefinition[] devices
        Map~string, Profile~ profiles
        Diagram? diagram
        BridgeConfig? bridgeConfig
    }

    class Profile {
        string[] devices
        object? notes
        object? unknown
    }

    class DeviceDefinition {
        string label
        string deviceInterface
        int? manufacturer
        int? deviceType
        int? id
        string? model
        string? type
        bool? invert
        string[]? attachments
        string[]? tags
        bool? terminator
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
        object? neighborLinks
        object? neighborPorts
        object? canLinks
        object? deviceLinks
    }

    class Node {
        string objectType
        string nodeType
        string category
        string label
        int bus
        int row
        float x
        float? freeY
        float? scale
        string[]? tags
    }

    BringupSystem "1" --> "many" Profile : profiles
    BringupSystem "1" --> "many" DeviceDefinition : devices
    Profile "1" --> "many" DeviceDefinition : devices (by label)
    BringupSystem "0..1" --> Diagram : diagram
    Diagram "1" --> "many" DiagramProfile : profiles
    DiagramProfile "1" --> "many" Node : nodes
    BringupSystem "0..1" --> BridgeConfig : bridgeConfig
    BridgeConfig "1" --> "many" BridgeProfile : byProfile
    BridgeProfile "1" --> "many" Group : groups
    Group "1" --> "many" Member : members
    Group "1" --> "many" Binding : bindings
```

Notes:
- `schema_version`, `data_version`, and `data_hash` are required at the root (schema_version=5).
- `devices` is the central devices table; labels must be unique.
- `devices[].id` is the single interface-local identifier field for CAN, DIO, USB, and other device interfaces.
- Profiles list device labels only under `profiles.<name>.devices`.
- Limit switches are DIO devices with `type=limitSwitch` and are referenced by label in `attachments` on the CAN device.
- Diagram/topology nodes use `objectType` as the canonical shared kind field. `nodeType` is still written as a mirrored compatibility field.
- Diagram `objectType=device` entries resolve to device records by `label` and do not store a separate hardware id.
- Bridge group members are stored by shared object `label` and may reference device or infrastructure objects.
- `diagram` is editor-only and ignored by robot/PC tools.
- `bridgeConfig` is optional; the topology editor can read/write it for per-profile group overlays.
- Robot and PC tools ignore bridgeConfig for control logic (CLI/UI only).

```mermaid
classDiagram
    class BridgeConfig {
        int schemaVersion
        string? generatedAt
        Map~string, BridgeProfile~ byProfile
    }

    class BridgeProfile {
        Group[] groups
        object selectedDevice
    }

    class Group {
        string name
        bool enabled
        Member[] members
        Binding[] bindings
    }

    class Member {
        string label
        bool enabled
    }

    class Binding {
        string input
        string kind
        float? value
    }
```
