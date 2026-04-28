# GALAXY_SOUNDS — permissive classifier

## Per-family ranking (1 = strongest on the axis)

| product | mr | mom | mm | obi | pair |
|---|---:|---:|---:|---:|---:|
| GALAXY_SOUNDS_DARK_MATTER | 2 | 5 | 3 | 4 | 3 |
| GALAXY_SOUNDS_BLACK_HOLES | 3 | 2 | 5 | 3 | 2 |
| GALAXY_SOUNDS_PLANETARY_RINGS | 5 | 1 | 1 | 2 | 3 |
| GALAXY_SOUNDS_SOLAR_WINDS | 4 | 4 | 2 | 1 | 1 |
| GALAXY_SOUNDS_SOLAR_FLAMES | 1 | 3 | 4 | 5 | 5 |

## Counts
- MR_FLAG: 3
- MOM_FLAG: 0
- MM_FLAG: 0
- OBI_FLAG: 5
- PAIR_FLAG: 2
- NO_EDGE: 0

### MR_FLAG
- **GALAXY_SOUNDS_DARK_MATTER** (rank 2/5, score=+1.250) — [MR] acf1=-0.012<-0.01 (Bartlett p=0.0365) | IC[neg_spread]=+0.131 @ h=1000 (sign=+1, t=+2.91, p=0.00358, FDR-pass); [OBI] IC[obi_l1]=+0.052 @ h=1 (t=+9.00, p=0, FDR-pass)
- **GALAXY_SOUNDS_BLACK_HOLES** (rank 3/5, score=+0.617) — [MR] acf1=-0.017<-0.01 (Bartlett p=0.00407); [OBI] IC[obi_l1]=+0.059 @ h=1 (t=+9.88, p=0, FDR-pass); [TOP_MOM_IN_FAMILY rank=2/5 score=+0.677]; [TOP_PAIR_IN_FAMILY rank=2/5 score=+0.404]
- **GALAXY_SOUNDS_SOLAR_FLAMES** (rank 1/5, score=+1.889) — [MR] acf1=-0.012<-0.01 (Bartlett p=0.0356) | IC[neg_spread]=+0.180 @ h=1000 (sign=+1, t=+2.88, p=0.00401, FDR-pass); [OBI] IC[obi_l1]=+0.052 @ h=1 (t=+8.94, p=0, FDR-pass); [PAIR] partner=GALAXY_SOUNDS_SOLAR_WINDS corr=-0.34 coint_p=0.081

### MOM_FLAG
- _(none)_

### MM_FLAG
- _(none)_

### OBI_FLAG
- **GALAXY_SOUNDS_DARK_MATTER** (rank 4/5, score=+0.052) — [MR] acf1=-0.012<-0.01 (Bartlett p=0.0365) | IC[neg_spread]=+0.131 @ h=1000 (sign=+1, t=+2.91, p=0.00358, FDR-pass); [OBI] IC[obi_l1]=+0.052 @ h=1 (t=+9.00, p=0, FDR-pass)
- **GALAXY_SOUNDS_BLACK_HOLES** (rank 3/5, score=+0.059) — [MR] acf1=-0.017<-0.01 (Bartlett p=0.00407); [OBI] IC[obi_l1]=+0.059 @ h=1 (t=+9.88, p=0, FDR-pass); [TOP_MOM_IN_FAMILY rank=2/5 score=+0.677]; [TOP_PAIR_IN_FAMILY rank=2/5 score=+0.404]
- **GALAXY_SOUNDS_PLANETARY_RINGS** (rank 2/5, score=+0.059) — [OBI] IC[obi_l1]=+0.059 @ h=1 (t=+9.96, p=0, FDR-pass); [TOP_MOM_IN_FAMILY rank=1/5 score=+1.792]; [TOP_MM_IN_FAMILY rank=1/5 score=+1.085]
- **GALAXY_SOUNDS_SOLAR_WINDS** (rank 1/5, score=+0.065) — [OBI] IC[obi_l1]=+0.065 @ h=1 (t=+11.29, p=0, FDR-pass); [PAIR] partner=GALAXY_SOUNDS_SOLAR_FLAMES corr=-0.34 coint_p=0.081; [TOP_MM_IN_FAMILY rank=2/5 score=+1.069]
- **GALAXY_SOUNDS_SOLAR_FLAMES** (rank 5/5, score=+0.052) — [MR] acf1=-0.012<-0.01 (Bartlett p=0.0356) | IC[neg_spread]=+0.180 @ h=1000 (sign=+1, t=+2.88, p=0.00401, FDR-pass); [OBI] IC[obi_l1]=+0.052 @ h=1 (t=+8.94, p=0, FDR-pass); [PAIR] partner=GALAXY_SOUNDS_SOLAR_WINDS corr=-0.34 coint_p=0.081

### PAIR_FLAG
- **GALAXY_SOUNDS_SOLAR_WINDS** (rank 1/5, score=+0.428) — [OBI] IC[obi_l1]=+0.065 @ h=1 (t=+11.29, p=0, FDR-pass); [PAIR] partner=GALAXY_SOUNDS_SOLAR_FLAMES corr=-0.34 coint_p=0.081; [TOP_MM_IN_FAMILY rank=2/5 score=+1.069]
- **GALAXY_SOUNDS_SOLAR_FLAMES** (rank 5/5, score=+0.308) — [MR] acf1=-0.012<-0.01 (Bartlett p=0.0356) | IC[neg_spread]=+0.180 @ h=1000 (sign=+1, t=+2.88, p=0.00401, FDR-pass); [OBI] IC[obi_l1]=+0.052 @ h=1 (t=+8.94, p=0, FDR-pass); [PAIR] partner=GALAXY_SOUNDS_SOLAR_WINDS corr=-0.34 coint_p=0.081

### TOP_MOM_IN_FAMILY (rank ≤ K but MOM_FLAG missed)
- **GALAXY_SOUNDS_BLACK_HOLES** (rank 2/5, score=+0.677)
- **GALAXY_SOUNDS_PLANETARY_RINGS** (rank 1/5, score=+1.792)

### TOP_MM_IN_FAMILY (rank ≤ K but MM_FLAG missed)
- **GALAXY_SOUNDS_PLANETARY_RINGS** (rank 1/5, score=+1.085)
- **GALAXY_SOUNDS_SOLAR_WINDS** (rank 2/5, score=+1.069)

### TOP_PAIR_IN_FAMILY (rank ≤ K but PAIR_FLAG missed)
- **GALAXY_SOUNDS_BLACK_HOLES** (rank 2/5, score=+0.404)

### NO_EDGE
- _(none — every product carries at least one flag or top-rank)_
