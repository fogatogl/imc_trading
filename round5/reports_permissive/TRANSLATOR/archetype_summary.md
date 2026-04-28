# TRANSLATOR — permissive classifier

## Per-family ranking (1 = strongest on the axis)

| product | mr | mom | mm | obi | pair |
|---|---:|---:|---:|---:|---:|
| TRANSLATOR_ASTRO_BLACK | 3 | 3 | 1 | 2 | 2 |
| TRANSLATOR_ECLIPSE_CHARCOAL | 2 | 2 | 5 | 5 | 3 |
| TRANSLATOR_GRAPHITE_MIST | 4 | 4 | 3 | 4 | 5 |
| TRANSLATOR_SPACE_GRAY | 5 | 1 | 4 | 3 | 4 |
| TRANSLATOR_VOID_BLUE | 1 | 5 | 2 | 1 | 1 |

## Counts
- MR_FLAG: 2
- MOM_FLAG: 0
- MM_FLAG: 0
- OBI_FLAG: 1
- PAIR_FLAG: 0
- NO_EDGE: 1

### MR_FLAG
- **TRANSLATOR_ECLIPSE_CHARCOAL** (rank 2/5, score=+1.746) — [MR] IC[neg_spread]=+0.119 @ h=1000 (sign=+1, t=+3.74, p=0.000182, FDR-pass); [TOP_MOM_IN_FAMILY rank=2/5 score=+0.235]
- **TRANSLATOR_VOID_BLUE** (rank 1/5, score=+2.538) — [MR] IC[neg_spread]=+0.148 @ h=1000 (sign=+1, t=+2.38, p=0.0172, FDR-pass); [OBI] IC[obi_l1]=+0.043 @ h=1 (t=+7.35, p=1.95e-13, FDR-pass); [TOP_MM_IN_FAMILY rank=2/5 score=+0.305]; [TOP_PAIR_IN_FAMILY rank=1/5 score=+0.582]

### MOM_FLAG
- _(none)_

### MM_FLAG
- _(none)_

### OBI_FLAG
- **TRANSLATOR_VOID_BLUE** (rank 1/5, score=+0.043) — [MR] IC[neg_spread]=+0.148 @ h=1000 (sign=+1, t=+2.38, p=0.0172, FDR-pass); [OBI] IC[obi_l1]=+0.043 @ h=1 (t=+7.35, p=1.95e-13, FDR-pass); [TOP_MM_IN_FAMILY rank=2/5 score=+0.305]; [TOP_PAIR_IN_FAMILY rank=1/5 score=+0.582]

### PAIR_FLAG
- _(none)_

### TOP_MOM_IN_FAMILY (rank ≤ K but MOM_FLAG missed)
- **TRANSLATOR_ECLIPSE_CHARCOAL** (rank 2/5, score=+0.235)
- **TRANSLATOR_SPACE_GRAY** (rank 1/5, score=+3.329)

### TOP_MM_IN_FAMILY (rank ≤ K but MM_FLAG missed)
- **TRANSLATOR_ASTRO_BLACK** (rank 1/5, score=+0.319)
- **TRANSLATOR_VOID_BLUE** (rank 2/5, score=+0.305)

### TOP_OBI_IN_FAMILY (rank ≤ K but OBI_FLAG missed)
- **TRANSLATOR_ASTRO_BLACK** (rank 2/5, score=+0.035)

### TOP_PAIR_IN_FAMILY (rank ≤ K but PAIR_FLAG missed)
- **TRANSLATOR_ASTRO_BLACK** (rank 2/5, score=+0.528)
- **TRANSLATOR_VOID_BLUE** (rank 1/5, score=+0.582)

### NO_EDGE
- **TRANSLATOR_GRAPHITE_MIST** — no flag, no top-rank
