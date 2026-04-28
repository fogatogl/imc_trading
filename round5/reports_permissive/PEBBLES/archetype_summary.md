# PEBBLES — permissive classifier

## Per-family ranking (1 = strongest on the axis)

| product | mr | mom | mm | obi | pair |
|---|---:|---:|---:|---:|---:|
| PEBBLES_XS | 2 | 4 | 5 | 5 | 1 |
| PEBBLES_S | 4 | 2 | 3 | 1 | 2 |
| PEBBLES_M | 1 | 5 | 1 | 3 | 4 |
| PEBBLES_L | 4 | 1 | 2 | 2 | 5 |
| PEBBLES_XL | 3 | 3 | 4 | 4 | 3 |

## Counts
- MR_FLAG: 3
- MOM_FLAG: 1
- MM_FLAG: 0
- OBI_FLAG: 0
- PAIR_FLAG: 3
- NO_EDGE: 0

### MR_FLAG
- **PEBBLES_XS** (rank 2/5, score=+1.208) — [MR] acf1=-0.016<-0.01 (Bartlett p=0.00684); [PAIR] partner=PEBBLES_XL corr=-0.83 coint_p=0.482
- **PEBBLES_M** (rank 1/5, score=+1.984) — [MR] IC[neg_spread]=+0.217 @ h=1000 (sign=+1, t=+2.38, p=0.0172, FDR-pass); [TOP_MM_IN_FAMILY rank=1/5 score=+0.604]
- **PEBBLES_XL** (rank 3/5, score=-0.451) — [MR] IC[neg_zscore_mid_50]=+0.078 @ h=100 (sign=+1, t=+2.98, p=0.00287, FDR-pass); [PAIR] partner=PEBBLES_S corr=-0.83 coint_p=0.229

### MOM_FLAG
- **PEBBLES_S** (rank 2/5, score=+0.787) — [MOM] hurst=0.55>0.55; [PAIR] partner=PEBBLES_XL corr=-0.83 coint_p=0.229; [TOP_OBI_IN_FAMILY rank=1/5 score=+0.036]

### MM_FLAG
- _(none)_

### OBI_FLAG
- _(none)_

### PAIR_FLAG
- **PEBBLES_XS** (rank 1/5, score=+0.721) — [MR] acf1=-0.016<-0.01 (Bartlett p=0.00684); [PAIR] partner=PEBBLES_XL corr=-0.83 coint_p=0.482
- **PEBBLES_S** (rank 2/5, score=+0.704) — [MOM] hurst=0.55>0.55; [PAIR] partner=PEBBLES_XL corr=-0.83 coint_p=0.229; [TOP_OBI_IN_FAMILY rank=1/5 score=+0.036]
- **PEBBLES_XL** (rank 3/5, score=+0.643) — [MR] IC[neg_zscore_mid_50]=+0.078 @ h=100 (sign=+1, t=+2.98, p=0.00287, FDR-pass); [PAIR] partner=PEBBLES_S corr=-0.83 coint_p=0.229

### TOP_MOM_IN_FAMILY (rank ≤ K but MOM_FLAG missed)
- **PEBBLES_L** (rank 1/5, score=+1.611)

### TOP_MM_IN_FAMILY (rank ≤ K but MM_FLAG missed)
- **PEBBLES_M** (rank 1/5, score=+0.604)
- **PEBBLES_L** (rank 2/5, score=+0.480)

### TOP_OBI_IN_FAMILY (rank ≤ K but OBI_FLAG missed)
- **PEBBLES_S** (rank 1/5, score=+0.036)
- **PEBBLES_L** (rank 2/5, score=+0.029)

### NO_EDGE
- _(none — every product carries at least one flag or top-rank)_
