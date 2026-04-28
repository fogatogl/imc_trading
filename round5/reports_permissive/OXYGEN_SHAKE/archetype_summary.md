# OXYGEN_SHAKE — permissive classifier

## Per-family ranking (1 = strongest on the axis)

| product | mr | mom | mm | obi | pair |
|---|---:|---:|---:|---:|---:|
| OXYGEN_SHAKE_CHOCOLATE | 3 | 5 | 4 | 2 | 1 |
| OXYGEN_SHAKE_MINT | 2 | 2 | 2 | 3 | 5 |
| OXYGEN_SHAKE_GARLIC | 5 | 1 | 3 | 1 | 1 |
| OXYGEN_SHAKE_MORNING_BREATH | 4 | 4 | 1 | 5 | 3 |
| OXYGEN_SHAKE_EVENING_BREATH | 1 | 3 | 5 | 4 | 4 |

## Counts
- MR_FLAG: 4
- MOM_FLAG: 0
- MM_FLAG: 0
- OBI_FLAG: 5
- PAIR_FLAG: 2
- NO_EDGE: 0

### MR_FLAG
- **OXYGEN_SHAKE_CHOCOLATE** (rank 3/5, score=+0.549) — [MR] vr_k5=0.836<0.97 (z=-12.96, p=0) | acf1=-0.089<-0.01 (Bartlett p=0) | IC[momentum_10]=-0.038 @ h=1 (sign=-1, t=-4.95, p=7.45e-07, FDR-pass); [OBI] IC[obi_l1]=+0.057 @ h=1 (t=+11.09, p=0, FDR-pass); [PAIR] partner=OXYGEN_SHAKE_GARLIC corr=+0.65 coint_p=0.0655
- **OXYGEN_SHAKE_MINT** (rank 2/5, score=+1.036) — [MR] IC[neg_spread]=+0.139 @ h=1000 (sign=+1, t=+1.78, p=0.0745, FDR-pass); [OBI] IC[obi_l1]=+0.055 @ h=1 (t=+9.62, p=0, FDR-pass); [TOP_MOM_IN_FAMILY rank=2/5 score=+2.270]; [TOP_MM_IN_FAMILY rank=2/5 score=+1.044]
- **OXYGEN_SHAKE_MORNING_BREATH** (rank 4/5, score=-1.220) — [MR] IC[momentum_10]=-0.032 @ h=10 (sign=-1, t=-2.46, p=0.014, FDR-pass); [OBI] IC[obi_l1]=+0.051 @ h=1 (t=+9.02, p=0, FDR-pass); [TOP_MM_IN_FAMILY rank=1/5 score=+1.124]
- **OXYGEN_SHAKE_EVENING_BREATH** (rank 1/5, score=+1.570) — [MR] vr_k5=0.798<0.97 (z=-15.93, p=0) | acf1=-0.123<-0.01 (Bartlett p=0) | IC[momentum_10]=-0.055 @ h=1 (sign=-1, t=-7.67, p=1.75e-14, FDR-pass); [OBI] IC[obi_l1]=+0.054 @ h=1 (t=+10.32, p=0, FDR-pass)

### MOM_FLAG
- _(none)_

### MM_FLAG
- _(none)_

### OBI_FLAG
- **OXYGEN_SHAKE_CHOCOLATE** (rank 2/5, score=+0.057) — [MR] vr_k5=0.836<0.97 (z=-12.96, p=0) | acf1=-0.089<-0.01 (Bartlett p=0) | IC[momentum_10]=-0.038 @ h=1 (sign=-1, t=-4.95, p=7.45e-07, FDR-pass); [OBI] IC[obi_l1]=+0.057 @ h=1 (t=+11.09, p=0, FDR-pass); [PAIR] partner=OXYGEN_SHAKE_GARLIC corr=+0.65 coint_p=0.0655
- **OXYGEN_SHAKE_MINT** (rank 3/5, score=+0.055) — [MR] IC[neg_spread]=+0.139 @ h=1000 (sign=+1, t=+1.78, p=0.0745, FDR-pass); [OBI] IC[obi_l1]=+0.055 @ h=1 (t=+9.62, p=0, FDR-pass); [TOP_MOM_IN_FAMILY rank=2/5 score=+2.270]; [TOP_MM_IN_FAMILY rank=2/5 score=+1.044]
- **OXYGEN_SHAKE_GARLIC** (rank 1/5, score=+0.066) — [OBI] IC[obi_l1]=+0.066 @ h=1 (t=+11.15, p=0, FDR-pass); [PAIR] partner=OXYGEN_SHAKE_CHOCOLATE corr=+0.65 coint_p=0.0655; [TOP_MOM_IN_FAMILY rank=1/5 score=+2.370]
- **OXYGEN_SHAKE_MORNING_BREATH** (rank 5/5, score=+0.051) — [MR] IC[momentum_10]=-0.032 @ h=10 (sign=-1, t=-2.46, p=0.014, FDR-pass); [OBI] IC[obi_l1]=+0.051 @ h=1 (t=+9.02, p=0, FDR-pass); [TOP_MM_IN_FAMILY rank=1/5 score=+1.124]
- **OXYGEN_SHAKE_EVENING_BREATH** (rank 4/5, score=+0.054) — [MR] vr_k5=0.798<0.97 (z=-15.93, p=0) | acf1=-0.123<-0.01 (Bartlett p=0) | IC[momentum_10]=-0.055 @ h=1 (sign=-1, t=-7.67, p=1.75e-14, FDR-pass); [OBI] IC[obi_l1]=+0.054 @ h=1 (t=+10.32, p=0, FDR-pass)

### PAIR_FLAG
- **OXYGEN_SHAKE_CHOCOLATE** (rank 1/5, score=+0.603) — [MR] vr_k5=0.836<0.97 (z=-12.96, p=0) | acf1=-0.089<-0.01 (Bartlett p=0) | IC[momentum_10]=-0.038 @ h=1 (sign=-1, t=-4.95, p=7.45e-07, FDR-pass); [OBI] IC[obi_l1]=+0.057 @ h=1 (t=+11.09, p=0, FDR-pass); [PAIR] partner=OXYGEN_SHAKE_GARLIC corr=+0.65 coint_p=0.0655
- **OXYGEN_SHAKE_GARLIC** (rank 1/5, score=+0.603) — [OBI] IC[obi_l1]=+0.066 @ h=1 (t=+11.15, p=0, FDR-pass); [PAIR] partner=OXYGEN_SHAKE_CHOCOLATE corr=+0.65 coint_p=0.0655; [TOP_MOM_IN_FAMILY rank=1/5 score=+2.370]

### TOP_MOM_IN_FAMILY (rank ≤ K but MOM_FLAG missed)
- **OXYGEN_SHAKE_MINT** (rank 2/5, score=+2.270)
- **OXYGEN_SHAKE_GARLIC** (rank 1/5, score=+2.370)

### TOP_MM_IN_FAMILY (rank ≤ K but MM_FLAG missed)
- **OXYGEN_SHAKE_MINT** (rank 2/5, score=+1.044)
- **OXYGEN_SHAKE_MORNING_BREATH** (rank 1/5, score=+1.124)

### NO_EDGE
- _(none — every product carries at least one flag or top-rank)_
