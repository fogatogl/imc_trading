# SNACKPACK — permissive classifier

## Per-family ranking (1 = strongest on the axis)

| product | mr | mom | mm | obi | pair |
|---|---:|---:|---:|---:|---:|
| SNACKPACK_CHOCOLATE | 2 | 3 | 3 | 2 | 2 |
| SNACKPACK_VANILLA | 4 | 1 | 2 | 3 | 1 |
| SNACKPACK_RASPBERRY | 5 | 4 | 5 | 4 | 4 |
| SNACKPACK_STRAWBERRY | 1 | 2 | 4 | 5 | 3 |
| SNACKPACK_PISTACHIO | 3 | 5 | 1 | 1 | 5 |

## Counts
- MR_FLAG: 5
- MOM_FLAG: 0
- MM_FLAG: 0
- OBI_FLAG: 5
- PAIR_FLAG: 5
- NO_EDGE: 0

### MR_FLAG
- **SNACKPACK_CHOCOLATE** (rank 2/5, score=+0.445) — [MR] vr_k5=0.950<0.97 (z=-3.94, p=8.09e-05) | acf1=-0.031<-0.01 (Bartlett p=8.84e-08) | IC[neg_spread]=+0.088 @ h=1000 (sign=+1, t=+3.09, p=0.00202, FDR-pass); [OBI] IC[obi_l1]=+0.118 @ h=1 (t=+19.97, p=0, FDR-pass); [PAIR] partner=SNACKPACK_VANILLA corr=-0.93 coint_p=0.462
- **SNACKPACK_VANILLA** (rank 4/5, score=-0.191) — [MR] vr_k5=0.952<0.97 (z=-3.81, p=0.000141) | acf1=-0.027<-0.01 (Bartlett p=3.46e-06) | IC[neg_spread]=+0.089 @ h=1000 (sign=+1, t=+3.01, p=0.00262, FDR-pass); [OBI] IC[obi_l1]=+0.114 @ h=1 (t=+19.34, p=0, FDR-pass); [PAIR] partner=SNACKPACK_CHOCOLATE corr=-0.93 coint_p=0.462; [TOP_MOM_IN_FAMILY rank=1/5 score=+1.143]; [TOP_MM_IN_FAMILY rank=2/5 score=+2.139]
- **SNACKPACK_RASPBERRY** (rank 5/5, score=-1.071) — [MR] acf1=-0.017<-0.01 (Bartlett p=0.0034) | IC[neg_spread]=+0.098 @ h=1000 (sign=+1, t=+4.02, p=5.88e-05, FDR-pass); [OBI] IC[obi_l1]=+0.102 @ h=1 (t=+17.62, p=0, FDR-pass); [PAIR] partner=SNACKPACK_PISTACHIO corr=-0.50 coint_p=0.0217
- **SNACKPACK_STRAWBERRY** (rank 1/5, score=+0.511) — [MR] acf1=-0.014<-0.01 (Bartlett p=0.0143) | IC[neg_spread]=+0.126 @ h=1000 (sign=+1, t=+2.11, p=0.0351, FDR-pass); [OBI] IC[obi_l1]=+0.097 @ h=1 (t=+17.05, p=0, FDR-pass); [PAIR] partner=SNACKPACK_CHOCOLATE corr=-0.54 coint_p=0.0356; [TOP_MOM_IN_FAMILY rank=2/5 score=+0.959]
- **SNACKPACK_PISTACHIO** (rank 3/5, score=+0.306) — [MR] acf1=-0.025<-0.01 (Bartlett p=1.27e-05) | IC[neg_spread]=+0.099 @ h=1000 (sign=+1, t=+2.25, p=0.0247, FDR-pass); [OBI] IC[obi_l1]=+0.132 @ h=1 (t=+22.82, p=0, FDR-pass); [PAIR] partner=SNACKPACK_RASPBERRY corr=-0.50 coint_p=0.0217; [TOP_MM_IN_FAMILY rank=1/5 score=+2.737]

### MOM_FLAG
- _(none)_

### MM_FLAG
- _(none)_

### OBI_FLAG
- **SNACKPACK_CHOCOLATE** (rank 2/5, score=+0.118) — [MR] vr_k5=0.950<0.97 (z=-3.94, p=8.09e-05) | acf1=-0.031<-0.01 (Bartlett p=8.84e-08) | IC[neg_spread]=+0.088 @ h=1000 (sign=+1, t=+3.09, p=0.00202, FDR-pass); [OBI] IC[obi_l1]=+0.118 @ h=1 (t=+19.97, p=0, FDR-pass); [PAIR] partner=SNACKPACK_VANILLA corr=-0.93 coint_p=0.462
- **SNACKPACK_VANILLA** (rank 3/5, score=+0.114) — [MR] vr_k5=0.952<0.97 (z=-3.81, p=0.000141) | acf1=-0.027<-0.01 (Bartlett p=3.46e-06) | IC[neg_spread]=+0.089 @ h=1000 (sign=+1, t=+3.01, p=0.00262, FDR-pass); [OBI] IC[obi_l1]=+0.114 @ h=1 (t=+19.34, p=0, FDR-pass); [PAIR] partner=SNACKPACK_CHOCOLATE corr=-0.93 coint_p=0.462; [TOP_MOM_IN_FAMILY rank=1/5 score=+1.143]; [TOP_MM_IN_FAMILY rank=2/5 score=+2.139]
- **SNACKPACK_RASPBERRY** (rank 4/5, score=+0.102) — [MR] acf1=-0.017<-0.01 (Bartlett p=0.0034) | IC[neg_spread]=+0.098 @ h=1000 (sign=+1, t=+4.02, p=5.88e-05, FDR-pass); [OBI] IC[obi_l1]=+0.102 @ h=1 (t=+17.62, p=0, FDR-pass); [PAIR] partner=SNACKPACK_PISTACHIO corr=-0.50 coint_p=0.0217
- **SNACKPACK_STRAWBERRY** (rank 5/5, score=+0.097) — [MR] acf1=-0.014<-0.01 (Bartlett p=0.0143) | IC[neg_spread]=+0.126 @ h=1000 (sign=+1, t=+2.11, p=0.0351, FDR-pass); [OBI] IC[obi_l1]=+0.097 @ h=1 (t=+17.05, p=0, FDR-pass); [PAIR] partner=SNACKPACK_CHOCOLATE corr=-0.54 coint_p=0.0356; [TOP_MOM_IN_FAMILY rank=2/5 score=+0.959]
- **SNACKPACK_PISTACHIO** (rank 1/5, score=+0.132) — [MR] acf1=-0.025<-0.01 (Bartlett p=1.27e-05) | IC[neg_spread]=+0.099 @ h=1000 (sign=+1, t=+2.25, p=0.0247, FDR-pass); [OBI] IC[obi_l1]=+0.132 @ h=1 (t=+22.82, p=0, FDR-pass); [PAIR] partner=SNACKPACK_RASPBERRY corr=-0.50 coint_p=0.0217; [TOP_MM_IN_FAMILY rank=1/5 score=+2.737]

### PAIR_FLAG
- **SNACKPACK_CHOCOLATE** (rank 2/5, score=+0.919) — [MR] vr_k5=0.950<0.97 (z=-3.94, p=8.09e-05) | acf1=-0.031<-0.01 (Bartlett p=8.84e-08) | IC[neg_spread]=+0.088 @ h=1000 (sign=+1, t=+3.09, p=0.00202, FDR-pass); [OBI] IC[obi_l1]=+0.118 @ h=1 (t=+19.97, p=0, FDR-pass); [PAIR] partner=SNACKPACK_VANILLA corr=-0.93 coint_p=0.462
- **SNACKPACK_VANILLA** (rank 1/5, score=+0.920) — [MR] vr_k5=0.952<0.97 (z=-3.81, p=0.000141) | acf1=-0.027<-0.01 (Bartlett p=3.46e-06) | IC[neg_spread]=+0.089 @ h=1000 (sign=+1, t=+3.01, p=0.00262, FDR-pass); [OBI] IC[obi_l1]=+0.114 @ h=1 (t=+19.34, p=0, FDR-pass); [PAIR] partner=SNACKPACK_CHOCOLATE corr=-0.93 coint_p=0.462; [TOP_MOM_IN_FAMILY rank=1/5 score=+1.143]; [TOP_MM_IN_FAMILY rank=2/5 score=+2.139]
- **SNACKPACK_RASPBERRY** (rank 4/5, score=+0.494) — [MR] acf1=-0.017<-0.01 (Bartlett p=0.0034) | IC[neg_spread]=+0.098 @ h=1000 (sign=+1, t=+4.02, p=5.88e-05, FDR-pass); [OBI] IC[obi_l1]=+0.102 @ h=1 (t=+17.62, p=0, FDR-pass); [PAIR] partner=SNACKPACK_PISTACHIO corr=-0.50 coint_p=0.0217
- **SNACKPACK_STRAWBERRY** (rank 3/5, score=+0.528) — [MR] acf1=-0.014<-0.01 (Bartlett p=0.0143) | IC[neg_spread]=+0.126 @ h=1000 (sign=+1, t=+2.11, p=0.0351, FDR-pass); [OBI] IC[obi_l1]=+0.097 @ h=1 (t=+17.05, p=0, FDR-pass); [PAIR] partner=SNACKPACK_CHOCOLATE corr=-0.54 coint_p=0.0356; [TOP_MOM_IN_FAMILY rank=2/5 score=+0.959]
- **SNACKPACK_PISTACHIO** (rank 5/5, score=+0.487) — [MR] acf1=-0.025<-0.01 (Bartlett p=1.27e-05) | IC[neg_spread]=+0.099 @ h=1000 (sign=+1, t=+2.25, p=0.0247, FDR-pass); [OBI] IC[obi_l1]=+0.132 @ h=1 (t=+22.82, p=0, FDR-pass); [PAIR] partner=SNACKPACK_RASPBERRY corr=-0.50 coint_p=0.0217; [TOP_MM_IN_FAMILY rank=1/5 score=+2.737]

### TOP_MOM_IN_FAMILY (rank ≤ K but MOM_FLAG missed)
- **SNACKPACK_VANILLA** (rank 1/5, score=+1.143)
- **SNACKPACK_STRAWBERRY** (rank 2/5, score=+0.959)

### TOP_MM_IN_FAMILY (rank ≤ K but MM_FLAG missed)
- **SNACKPACK_VANILLA** (rank 2/5, score=+2.139)
- **SNACKPACK_PISTACHIO** (rank 1/5, score=+2.737)

### NO_EDGE
- _(none — every product carries at least one flag or top-rank)_
