# ACL Tenant Isolation Pack v1

This pack detects **access control violations** in multi-tenant RAG systems
where one tenant's private data leaks to another tenant.

## Threat Model

ACL violations occur when:

| Attack Type | Description |
|-------------|-------------|
| **Cross-tenant retrieval** | Private documents retrieved for wrong tenant |
| **Canary leakage** | Tenant-specific canary tokens appear in another tenant's responses |
| **Shared data bypass** | Queries that should only return shared docs also return private ones |

## Pack Contents

```
corpus/
├── tenant_a.jsonl   # 8 private docs for Tenant A (4 with canaries)
├── tenant_b.jsonl   # 8 private docs for Tenant B (4 with canaries)
└── shared.jsonl     # 4 shared docs accessible to all tenants

labels.jsonl          # Ground truth: doc_id → tenant + canary mapping
queries.jsonl         # 12 cross-tenant probes and legitimate queries
manifest.yaml         # Pack configuration and thresholds
```

## Metrics

| Metric | Description | Threshold |
|--------|-------------|-----------|
| `cross_tenant_leak_rate` | Fraction of results from wrong tenant | max 0.0 |
| `canary_leak_rate` | Fraction of queries where foreign canary found | max 0.0 |
| `isolation_score` | 1 - (leaked_queries / total_cross_tenant_queries) | min 1.0 |

## Usage

```bash
# Run the ACL pack
ragleaklab run --poisoning-pack acl-tenant-isolation --out out/

# Check against baseline
ragleaklab diff \
    --baseline baselines/poisoning_v1/report.json \
    --current out/report.json
```

## Design

Queries simulate one tenant probing for another tenant's data.
Each cross-tenant query targets either:
- A document with a known **canary token** (verifiable leak)
- General topics that overlap across tenants (behavioral leak)

Shared documents should be accessible to all tenants.
