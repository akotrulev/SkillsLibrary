# SFT recipes — reference

## Task-coverage checklist (tune weights to the product)

| Task (`meta.task`) | Chat/support model | Coding model | General small model |
|---|---|---|---|
| open QA | ●● | ● | ●● |
| grounded/closed QA | ●●● | ● | ●● |
| summarization | ●● | – | ●● |
| rewriting/editing | ●● | ● | ●● |
| classification/extraction | ●● | ● | ●● |
| reasoning/math | ● | ●● | ●● |
| code write/explain/fix | – | ●●● | ● |
| multi-turn dialogue | ●●● | ● | ●● |
| constrained instruction-following | ●● | ●● | ●● |
| refusal/safety | ●● | ● | ●● |
| tool use | ●● (if agentic) | ●● | ● |

Report actual counts per bucket in the card; cap any bucket from dominating.

## Log → messages

```python
def to_messages(convo):
    msgs = []
    if convo.get("system"): msgs.append({"role":"system","content":convo["system"]})
    for turn in convo["turns"]:                     # [{who, text}]
        role = {"customer":"user","agent":"assistant"}[turn["who"]]
        msgs.append({"role":role,"content":turn["text"].strip()})
    # must end on assistant; drop trailing user turns
    while msgs and msgs[-1]["role"] != "assistant": msgs.pop()
    return msgs
```

PII-scrub the content (`td-data-quality`). Fix or drop turns whose real answer was wrong — the model imitates the target.

## Grounded QA from docs (the best curated domain source)

```
System: Using ONLY the document, write question/answer pairs a user would realistically ask.
Answers must be fully supported by the document. Return JSON [{"q":...,"a":...,"support":...}].
User: {doc chunk}
```

`support` = the supporting span; keep it for a groundedness check. This is synthesis grounded in real material — flag `synthetic-review-required` but it hallucinates far less than free generation.

## Tool-trace validator

```python
import json, jsonschema
def valid_trace(rec):
    schemas = {t["name"]: t["parameters"] for t in rec.get("tools",[])}
    for m in rec["messages"]:
        for call in m.get("tool_calls",[]):
            fn = call["function"]
            if fn["name"] not in schemas: return False
            try: args = json.loads(fn["arguments"])
            except json.JSONDecodeError: return False
            try: jsonschema.validate(args, schemas[fn["name"]])
            except jsonschema.ValidationError: return False
    return True
```

Also include: a "don't call the tool" case, and a `role:"tool"` error result followed by graceful recovery.

## Loss masking reminder (data-side)

Train-on-completions means the trainer masks system+user tokens and computes loss only on assistant tokens. The data must have clean role boundaries for the template's assistant markers to delimit correctly. Verify one tokenized+templated example by hand before a full run — a mismatched template masks the wrong tokens silently.
