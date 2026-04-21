# Bringup Label Link Map

Purpose: Visualize where device labels are used as references across bringup structures.

```mermaid
flowchart LR
    DevicesTable["devices[].label"]

    subgraph Config["bringup_system.json"]
        ProfileDevices["profiles.<name>.devices[]"]
        Attachments["devices[].attachments[]"]
        DiagramNodes["diagram.profiles.<name>.nodes[].label"]
        GroupMembers["bridgeConfig.byProfile.<name>.groups[].members[].device"]
        SelectedDevice["bridgeConfig.byProfile.<name>.selectedDevice.device"]
    end

    subgraph Tests["bringup_system.json (bridgeConfig tests)"]
        TestMotorLabels["bridgeConfig.byProfile.<name>.tests.test_sets.<set>[].motorLabels[]"]
    end

    ProfileDevices --> DevicesTable
    Attachments --> DevicesTable
    DiagramNodes --> DevicesTable
    GroupMembers --> DevicesTable
    SelectedDevice --> DevicesTable
    TestMotorLabels --> DevicesTable
```

Notes:
- All label references must match exactly one entry in `devices[].label`.
- Labels are globally unique within the devices table.
- Diagram nodes are label-linked only when the node represents a real device.
