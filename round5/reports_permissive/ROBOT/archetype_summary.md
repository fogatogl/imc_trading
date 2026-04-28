# ROBOT — permissive classifier

## Per-family ranking (1 = strongest on the axis)

| product | mr | mom | mm | obi | pair |
|---|---:|---:|---:|---:|---:|
| ROBOT_VACUUMING | 4 | 1 | 2 | 1 | 1 |
| ROBOT_MOPPING | 3 | 3 | 3 | 4 | 5 |
| ROBOT_DISHES | 1 | 4 | 5 | 4 | 3 |
| ROBOT_LAUNDRY | 5 | 2 | 1 | 3 | 1 |
| ROBOT_IRONING | 2 | 5 | 4 | 2 | 4 |

## Counts
- MR_FLAG: 3
- MOM_FLAG: 0
- MM_FLAG: 0
- OBI_FLAG: 0
- PAIR_FLAG: 5
- NO_EDGE: 0

### MR_FLAG
- **ROBOT_MOPPING** (rank 3/5, score=-1.441) — [MR] vr_k5=0.961<0.97 (z=-3.09, p=0.00198); [PAIR] partner=ROBOT_IRONING corr=-0.82 coint_p=0.266
- **ROBOT_DISHES** (rank 1/5, score=+3.514) — [MR] vr_k5=0.555<0.97 (z=-35.15, p=0) | acf1=-0.232<-0.01 (Bartlett p=0) | IC[momentum_10]=-0.148 @ h=1 (sign=-1, t=-17.26, p=0, FDR-pass); [PAIR] partner=ROBOT_LAUNDRY corr=-0.72 coint_p=0.257
- **ROBOT_IRONING** (rank 2/5, score=+0.963) — [MR] vr_k5=0.782<0.97 (z=-17.24, p=0) | acf1=-0.125<-0.01 (Bartlett p=0) | IC[trade_imbalance]=-0.067 @ h=1000 (sign=-1, t=-2.68, p=0.00738, FDR-pass); [PAIR] partner=ROBOT_MOPPING corr=-0.82 coint_p=0.266; [TOP_OBI_IN_FAMILY rank=2/5 score=+0.026]

### MOM_FLAG
- _(none)_

### MM_FLAG
- _(none)_

### OBI_FLAG
- _(none)_

### PAIR_FLAG
- **ROBOT_VACUUMING** (rank 1/5, score=+0.732) — [PAIR] partner=ROBOT_LAUNDRY corr=+0.79 coint_p=0.0701; [TOP_MOM_IN_FAMILY rank=1/5 score=+1.074]; [TOP_MM_IN_FAMILY rank=2/5 score=+0.146]; [TOP_OBI_IN_FAMILY rank=1/5 score=+0.027]
- **ROBOT_MOPPING** (rank 5/5, score=+0.626) — [MR] vr_k5=0.961<0.97 (z=-3.09, p=0.00198); [PAIR] partner=ROBOT_IRONING corr=-0.82 coint_p=0.266
- **ROBOT_DISHES** (rank 3/5, score=+0.653) — [MR] vr_k5=0.555<0.97 (z=-35.15, p=0) | acf1=-0.232<-0.01 (Bartlett p=0) | IC[momentum_10]=-0.148 @ h=1 (sign=-1, t=-17.26, p=0, FDR-pass); [PAIR] partner=ROBOT_LAUNDRY corr=-0.72 coint_p=0.257
- **ROBOT_LAUNDRY** (rank 1/5, score=+0.732) — [PAIR] partner=ROBOT_VACUUMING corr=+0.79 coint_p=0.0701; [TOP_MOM_IN_FAMILY rank=2/5 score=+0.770]; [TOP_MM_IN_FAMILY rank=1/5 score=+0.154]
- **ROBOT_IRONING** (rank 4/5, score=+0.627) — [MR] vr_k5=0.782<0.97 (z=-17.24, p=0) | acf1=-0.125<-0.01 (Bartlett p=0) | IC[trade_imbalance]=-0.067 @ h=1000 (sign=-1, t=-2.68, p=0.00738, FDR-pass); [PAIR] partner=ROBOT_MOPPING corr=-0.82 coint_p=0.266; [TOP_OBI_IN_FAMILY rank=2/5 score=+0.026]

### TOP_MOM_IN_FAMILY (rank ≤ K but MOM_FLAG missed)
- **ROBOT_VACUUMING** (rank 1/5, score=+1.074)
- **ROBOT_LAUNDRY** (rank 2/5, score=+0.770)

### TOP_MM_IN_FAMILY (rank ≤ K but MM_FLAG missed)
- **ROBOT_VACUUMING** (rank 2/5, score=+0.146)
- **ROBOT_LAUNDRY** (rank 1/5, score=+0.154)

### TOP_OBI_IN_FAMILY (rank ≤ K but OBI_FLAG missed)
- **ROBOT_VACUUMING** (rank 1/5, score=+0.027)
- **ROBOT_IRONING** (rank 2/5, score=+0.026)

### NO_EDGE
- _(none — every product carries at least one flag or top-rank)_
