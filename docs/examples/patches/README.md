# Patch PR Templates

This directory contains example patches for corpus updates.

## Files

| File | Description |
|------|-------------|
| `2026-02-05-add-privacy-policy.yaml` | Example patch adding new policy document |
| `expected_result.yaml` | What RAGLeakLab should report after this patch |

## Usage

1. Create a patch file following the template structure
2. Open a PR with the patch + any corpus changes
3. CI runs delta check against baseline
4. Review the generated report
5. Merge if validation passes

## Patch File Structure

```yaml
metadata:
  date: "YYYY-MM-DD"
  author: your-team
  description: "What this patch does"
  ticket: JIRA-123

add:
  - id: document_id
    path: path/to/file.txt
    tags: [tag1, tag2]

modify:
  - id: existing_doc_id
    path: path/to/updated.txt
    reason: "Why modified"

remove:
  - id: old_doc_id
    reason: "Why removed"

expected_claims:
  added: [...]
  modified: [...]
  removed: [...]

validation:
  must_detect: [claim_ids...]
  must_not_leak: [claim_ids...]
```

See the example files for complete templates.
