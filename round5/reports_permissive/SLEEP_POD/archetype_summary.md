# SLEEP_POD — permissive classifier

## Per-family ranking (1 = strongest on the axis)

| product | mr | mom | mm | obi | pair |
|---|---:|---:|---:|---:|---:|
| SLEEP_POD_SUEDE | 1 | 5 | 3 | 2 | 3 |
| SLEEP_POD_LAMB_WOOL | 3 | 1 | 4 | 4 | 4 |
| SLEEP_POD_POLYESTER | 4 | 4 | 1 | 3 | 1 |
| SLEEP_POD_NYLON | 5 | 3 | 2 | 5 | 4 |
| SLEEP_POD_COTTON | 2 | 2 | 5 | 1 | 1 |

## Counts
- MR_FLAG: 3
- MOM_FLAG: 1
- MM_FLAG: 0
- OBI_FLAG: 1
- PAIR_FLAG: 5
- NO_EDGE: 0

### MR_FLAG
- **SLEEP_POD_SUEDE** (rank 1/5, score=+2.408) — [MR] IC[neg_spread]=+0.162 @ h=1000 (sign=+1, t=+1.90, p=0.057, FDR-pass); [PAIR] partner=SLEEP_POD_POLYESTER corr=+0.86 coint_p=0.151; [TOP_OBI_IN_FAMILY rank=2/5 score=+0.038]
- **SLEEP_POD_LAMB_WOOL** (rank 3/5, score=-0.462) — [MR] IC[neg_spread]=+0.146 @ h=1000 (sign=+1, t=+2.76, p=0.0057, FDR-pass); [PAIR] partner=SLEEP_POD_NYLON corr=+0.49 coint_p=0.0753; [TOP_MOM_IN_FAMILY rank=1/5 score=+2.217]
- **SLEEP_POD_COTTON** (rank 2/5, score=+1.604) — [MR] IC[neg_spread]=+0.206 @ h=1000 (sign=+1, t=+2.60, p=0.00921, FDR-pass); [MOM] hurst=0.56>0.55; [OBI] IC[obi_l1]=+0.049 @ h=1 (t=+8.52, p=0, FDR-pass); [PAIR] partner=SLEEP_POD_POLYESTER corr=+0.88 coint_p=0.101

### MOM_FLAG
- **SLEEP_POD_COTTON** (rank 2/5, score=+1.206) — [MR] IC[neg_spread]=+0.206 @ h=1000 (sign=+1, t=+2.60, p=0.00921, FDR-pass); [MOM] hurst=0.56>0.55; [OBI] IC[obi_l1]=+0.049 @ h=1 (t=+8.52, p=0, FDR-pass); [PAIR] partner=SLEEP_POD_POLYESTER corr=+0.88 coint_p=0.101

### MM_FLAG
- _(none)_

### OBI_FLAG
- **SLEEP_POD_COTTON** (rank 1/5, score=+0.049) — [MR] IC[neg_spread]=+0.206 @ h=1000 (sign=+1, t=+2.60, p=0.00921, FDR-pass); [MOM] hurst=0.56>0.55; [OBI] IC[obi_l1]=+0.049 @ h=1 (t=+8.52, p=0, FDR-pass); [PAIR] partner=SLEEP_POD_POLYESTER corr=+0.88 coint_p=0.101

### PAIR_FLAG
- **SLEEP_POD_SUEDE** (rank 3/5, score=+0.730) — [MR] IC[neg_spread]=+0.162 @ h=1000 (sign=+1, t=+1.90, p=0.057, FDR-pass); [PAIR] partner=SLEEP_POD_POLYESTER corr=+0.86 coint_p=0.151; [TOP_OBI_IN_FAMILY rank=2/5 score=+0.038]
- **SLEEP_POD_LAMB_WOOL** (rank 4/5, score=+0.456) — [MR] IC[neg_spread]=+0.146 @ h=1000 (sign=+1, t=+2.76, p=0.0057, FDR-pass); [PAIR] partner=SLEEP_POD_NYLON corr=+0.49 coint_p=0.0753; [TOP_MOM_IN_FAMILY rank=1/5 score=+2.217]
- **SLEEP_POD_POLYESTER** (rank 1/5, score=+0.787) — [PAIR] partner=SLEEP_POD_COTTON corr=+0.88 coint_p=0.101; [TOP_MM_IN_FAMILY rank=1/5 score=+0.356]
- **SLEEP_POD_NYLON** (rank 4/5, score=+0.456) — [PAIR] partner=SLEEP_POD_LAMB_WOOL corr=+0.49 coint_p=0.0753; [TOP_MM_IN_FAMILY rank=2/5 score=+0.339]
- **SLEEP_POD_COTTON** (rank 1/5, score=+0.787) — [MR] IC[neg_spread]=+0.206 @ h=1000 (sign=+1, t=+2.60, p=0.00921, FDR-pass); [MOM] hurst=0.56>0.55; [OBI] IC[obi_l1]=+0.049 @ h=1 (t=+8.52, p=0, FDR-pass); [PAIR] partner=SLEEP_POD_POLYESTER corr=+0.88 coint_p=0.101

### TOP_MOM_IN_FAMILY (rank ≤ K but MOM_FLAG missed)
- **SLEEP_POD_LAMB_WOOL** (rank 1/5, score=+2.217)

### TOP_MM_IN_FAMILY (rank ≤ K but MM_FLAG missed)
- **SLEEP_POD_POLYESTER** (rank 1/5, score=+0.356)
- **SLEEP_POD_NYLON** (rank 2/5, score=+0.339)

### TOP_OBI_IN_FAMILY (rank ≤ K but OBI_FLAG missed)
- **SLEEP_POD_SUEDE** (rank 2/5, score=+0.038)

### NO_EDGE
- _(none — every product carries at least one flag or top-rank)_
