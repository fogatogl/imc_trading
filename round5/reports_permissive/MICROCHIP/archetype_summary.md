# MICROCHIP — permissive classifier

## Per-family ranking (1 = strongest on the axis)

| product | mr | mom | mm | obi | pair |
|---|---:|---:|---:|---:|---:|
| MICROCHIP_CIRCLE | 4 | 3 | 3 | 2 | 5 |
| MICROCHIP_OVAL | 3 | 5 | 1 | 4 | 3 |
| MICROCHIP_SQUARE | 2 | 4 | 5 | 1 | 1 |
| MICROCHIP_RECTANGLE | 5 | 2 | 2 | 5 | 1 |
| MICROCHIP_TRIANGLE | 1 | 1 | 4 | 3 | 3 |

## Counts
- MR_FLAG: 2
- MOM_FLAG: 1
- MM_FLAG: 0
- OBI_FLAG: 0
- PAIR_FLAG: 4
- NO_EDGE: 0

### MR_FLAG
- **MICROCHIP_SQUARE** (rank 2/5, score=+1.456) — [MR] vr_k5=0.960<0.97 (z=-3.18, p=0.00145) | acf1=-0.024<-0.01 (Bartlett p=3.51e-05); [PAIR] partner=MICROCHIP_RECTANGLE corr=-0.88 coint_p=0.0196; [TOP_OBI_IN_FAMILY rank=1/5 score=+0.025]
- **MICROCHIP_TRIANGLE** (rank 1/5, score=+1.702) — [MR] IC[neg_zscore_mid_50]=+0.111 @ h=1000 (sign=+1, t=+4.46, p=8.25e-06, FDR-pass); [MOM] hurst=0.56>0.55; [PAIR] partner=MICROCHIP_OVAL corr=+0.87 coint_p=0.0526

### MOM_FLAG
- **MICROCHIP_TRIANGLE** (rank 1/5, score=+1.168) — [MR] IC[neg_zscore_mid_50]=+0.111 @ h=1000 (sign=+1, t=+4.46, p=8.25e-06, FDR-pass); [MOM] hurst=0.56>0.55; [PAIR] partner=MICROCHIP_OVAL corr=+0.87 coint_p=0.0526

### MM_FLAG
- _(none)_

### OBI_FLAG
- _(none)_

### PAIR_FLAG
- **MICROCHIP_OVAL** (rank 3/5, score=+0.825) — [PAIR] partner=MICROCHIP_TRIANGLE corr=+0.87 coint_p=0.0526; [TOP_MM_IN_FAMILY rank=1/5 score=-0.045]
- **MICROCHIP_SQUARE** (rank 1/5, score=+0.865) — [MR] vr_k5=0.960<0.97 (z=-3.18, p=0.00145) | acf1=-0.024<-0.01 (Bartlett p=3.51e-05); [PAIR] partner=MICROCHIP_RECTANGLE corr=-0.88 coint_p=0.0196; [TOP_OBI_IN_FAMILY rank=1/5 score=+0.025]
- **MICROCHIP_RECTANGLE** (rank 1/5, score=+0.865) — [PAIR] partner=MICROCHIP_SQUARE corr=-0.88 coint_p=0.0196; [TOP_MOM_IN_FAMILY rank=2/5 score=+0.900]; [TOP_MM_IN_FAMILY rank=2/5 score=-0.076]
- **MICROCHIP_TRIANGLE** (rank 3/5, score=+0.825) — [MR] IC[neg_zscore_mid_50]=+0.111 @ h=1000 (sign=+1, t=+4.46, p=8.25e-06, FDR-pass); [MOM] hurst=0.56>0.55; [PAIR] partner=MICROCHIP_OVAL corr=+0.87 coint_p=0.0526

### TOP_MOM_IN_FAMILY (rank ≤ K but MOM_FLAG missed)
- **MICROCHIP_RECTANGLE** (rank 2/5, score=+0.900)

### TOP_MM_IN_FAMILY (rank ≤ K but MM_FLAG missed)
- **MICROCHIP_OVAL** (rank 1/5, score=-0.045)
- **MICROCHIP_RECTANGLE** (rank 2/5, score=-0.076)

### TOP_OBI_IN_FAMILY (rank ≤ K but OBI_FLAG missed)
- **MICROCHIP_CIRCLE** (rank 2/5, score=+0.022)
- **MICROCHIP_SQUARE** (rank 1/5, score=+0.025)

### NO_EDGE
- _(none — every product carries at least one flag or top-rank)_
