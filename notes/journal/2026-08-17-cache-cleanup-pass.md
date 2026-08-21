REMINDER_STATUS: ACTIVE

# Cache cleanup pass

- Do a cleanup pass to remove unnecessary data caching in the host UI/runtime coordination paths.
- Recent bugs repeatedly came from stale or duplicated cache state diverging from authoritative robot/shared state.
- Focus on operator-visible truth paths first, especially selected profile/test, active scope membership, and other UI/robot sync decisions.
- Demote caches to pending-intent or debounce-only roles where possible.
