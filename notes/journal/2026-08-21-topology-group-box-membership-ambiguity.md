REMINDER_STATUS: ACTIVE

- Future issue: topology-editor group boxes can visually contain devices that are not actual group members.
- Example observed: `SPARKMAX/NEO 25` appeared inside the drawn `motors` box while the left panel group column correctly showed no `motors` membership for that device.
- Likely cause: layout/bounding-box rendering ambiguity rather than incorrect group membership data.
- When fixing:
  - verify whether this is purely visual layout or persisted group-box geometry behavior
  - make group membership clearer than simple enclosure inside the rectangle
  - test local topology-editor view against runtime/group selection panes so the two surfaces are less confusing together
