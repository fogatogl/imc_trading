# PANEL — permissive classifier

## Per-family ranking (1 = strongest on the axis)

| product | mr | mom | mm | obi | pair |
|---|---:|---:|---:|---:|---:|
| PANEL_1X2 | 1 | 2 | 1 | 1 | 2 |
| PANEL_1X4 | 5 | 1 | 5 | 5 | 3 |
| PANEL_2X2 | 2 | 5 | 2 | 3 | 1 |
| PANEL_2X4 | 3 | 3 | 4 | 2 | 4 |
| PANEL_4X4 | 4 | 4 | 3 | 4 | 5 |

## Counts
- MR_FLAG: 2
- MOM_FLAG: 2
- MM_FLAG: 0
- OBI_FLAG: 1
- PAIR_FLAG: 0
- NO_EDGE: 1

### MR_FLAG
- **PANEL_1X2** (rank 1/5, score=+1.030) — [MR] IC[neg_spread]=+0.198 @ h=1000 (sign=+1, t=+2.68, p=0.00738, FDR-pass); [MOM] hurst=0.55>0.55; [OBI] IC[obi_l1]=+0.057 @ h=1 (t=+9.74, p=0, FDR-pass); [TOP_MM_IN_FAMILY rank=1/5 score=+1.049]; [TOP_PAIR_IN_FAMILY rank=2/5 score=+0.370]
- **PANEL_2X4** (rank 3/5, score=-0.116) — [MR] IC[neg_spread]=+0.150 @ h=1000 (sign=+1, t=+2.82, p=0.00476, FDR-pass); [TOP_OBI_IN_FAMILY rank=2/5 score=+0.040]

### MOM_FLAG
- **PANEL_1X2** (rank 2/5, score=-0.202) — [MR] IC[neg_spread]=+0.198 @ h=1000 (sign=+1, t=+2.68, p=0.00738, FDR-pass); [MOM] hurst=0.55>0.55; [OBI] IC[obi_l1]=+0.057 @ h=1 (t=+9.74, p=0, FDR-pass); [TOP_MM_IN_FAMILY rank=1/5 score=+1.049]; [TOP_PAIR_IN_FAMILY rank=2/5 score=+0.370]
- **PANEL_1X4** (rank 1/5, score=+3.712) — [MOM] hurst=0.58>0.55 | IC[momentum_10]=+0.057 @ h=100 (t=+3.11, p=0.00187, FDR-pass)

### MM_FLAG
- _(none)_

### OBI_FLAG
- **PANEL_1X2** (rank 1/5, score=+0.057) — [MR] IC[neg_spread]=+0.198 @ h=1000 (sign=+1, t=+2.68, p=0.00738, FDR-pass); [MOM] hurst=0.55>0.55; [OBI] IC[obi_l1]=+0.057 @ h=1 (t=+9.74, p=0, FDR-pass); [TOP_MM_IN_FAMILY rank=1/5 score=+1.049]; [TOP_PAIR_IN_FAMILY rank=2/5 score=+0.370]

### PAIR_FLAG
- _(none)_

### TOP_MR_IN_FAMILY (rank ≤ K but MR_FLAG missed)
- **PANEL_2X2** (rank 2/5, score=+0.968)

### TOP_MM_IN_FAMILY (rank ≤ K but MM_FLAG missed)
- **PANEL_1X2** (rank 1/5, score=+1.049)
- **PANEL_2X2** (rank 2/5, score=+0.311)

### TOP_OBI_IN_FAMILY (rank ≤ K but OBI_FLAG missed)
- **PANEL_2X4** (rank 2/5, score=+0.040)

### TOP_PAIR_IN_FAMILY (rank ≤ K but PAIR_FLAG missed)
- **PANEL_1X2** (rank 2/5, score=+0.370)
- **PANEL_2X2** (rank 1/5, score=+0.444)

### NO_EDGE
- **PANEL_4X4** — no flag, no top-rank
