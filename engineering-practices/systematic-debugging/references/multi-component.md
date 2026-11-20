# Evidence in multi-component systems

When the system has multiple components (CI → build → signing, API → service → database), add diagnostic instrumentation before proposing fixes:
```
For each component boundary:
  - Log what data enters component
  - Log what data exits component
  - Verify environment/config propagation
  - Check state at each layer

Run once to gather evidence showing where it breaks
Then analyze evidence to identify failing component
Then investigate that specific component
```

**Example:**
```bash
echo "=== Secrets available in workflow: ==="
echo "IDENTITY: ${IDENTITY:+SET}${IDENTITY:-UNSET}"

echo "=== Env vars in build script: ==="
env | grep IDENTITY || echo "IDENTITY not in environment"

echo "=== Keychain state: ==="
security list-keychains
security find-identity -v

codesign --sign "$IDENTITY" --verbose=4 "$APP"
```

**This reveals:** Which layer fails (secrets → workflow ✓, workflow → build ✗)
