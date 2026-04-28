# UV_VISOR — permissive classifier

## Per-family ranking (1 = strongest on the axis)

| product | mr | mom | mm | obi | pair |
|---|---:|---:|---:|---:|---:|
| UV_VISOR_AMBER | 1 | 3 | 4 | 4 | 1 |
| UV_VISOR_MAGENTA | 2 | 5 | 1 | 2 | 1 |
| UV_VISOR_ORANGE | 4 | 1 | 3 | 5 | 5 |
| UV_VISOR_RED | 3 | 2 | 5 | 3 | 3 |
| UV_VISOR_YELLOW | 5 | 4 | 2 | 1 | 4 |

## Counts
- MR_FLAG: 4
- MOM_FLAG: 2
- MM_FLAG: 0
- OBI_FLAG: 5
- PAIR_FLAG: 3
- NO_EDGE: 0

### MR_FLAG
- **UV_VISOR_AMBER** (rank 1/5, score=+2.818) — [MR] IC[neg_spread]=+0.292 @ h=1000 (sign=+1, t=+3.47, p=0.000512, FDR-pass); [MOM] hurst=0.56>0.55; [OBI] IC[obi_l1]=+0.059 @ h=1 (t=+10.31, p=0, FDR-pass); [PAIR] partner=UV_VISOR_MAGENTA corr=-0.87 coint_p=0.0416
- **UV_VISOR_MAGENTA** (rank 2/5, score=+0.739) — [MR] IC[neg_spread]=+0.155 @ h=1000 (sign=+1, t=+2.02, p=0.0431, FDR-pass); [OBI] IC[obi_l1]=+0.059 @ h=1 (t=+9.72, p=0, FDR-pass); [PAIR] partner=UV_VISOR_AMBER corr=-0.87 coint_p=0.0416; [TOP_MM_IN_FAMILY rank=1/5 score=+1.129]
- **UV_VISOR_ORANGE** (rank 4/5, score=-1.416) — [MR] IC[neg_spread]=+0.122 @ h=1000 (sign=+1, t=+1.92, p=0.0554, FDR-pass); [OBI] IC[obi_l1]=+0.058 @ h=1 (t=+9.90, p=0, FDR-pass); [PAIR] partner=UV_VISOR_AMBER corr=-0.71 coint_p=0.826; [TOP_MOM_IN_FAMILY rank=1/5 score=+1.366]
- **UV_VISOR_RED** (rank 3/5, score=+0.583) — [MR] IC[neg_spread]=+0.143 @ h=1000 (sign=+1, t=+2.78, p=0.00548, FDR-pass); [MOM] hurst=0.56>0.55; [OBI] IC[obi_l1]=+0.059 @ h=1 (t=+9.89, p=0, FDR-pass)

### MOM_FLAG
- **UV_VISOR_AMBER** (rank 3/5, score=+0.335) — [MR] IC[neg_spread]=+0.292 @ h=1000 (sign=+1, t=+3.47, p=0.000512, FDR-pass); [MOM] hurst=0.56>0.55; [OBI] IC[obi_l1]=+0.059 @ h=1 (t=+10.31, p=0, FDR-pass); [PAIR] partner=UV_VISOR_MAGENTA corr=-0.87 coint_p=0.0416
- **UV_VISOR_RED** (rank 2/5, score=+0.382) — [MR] IC[neg_spread]=+0.143 @ h=1000 (sign=+1, t=+2.78, p=0.00548, FDR-pass); [MOM] hurst=0.56>0.55; [OBI] IC[obi_l1]=+0.059 @ h=1 (t=+9.89, p=0, FDR-pass)

### MM_FLAG
- _(none)_

### OBI_FLAG
- **UV_VISOR_AMBER** (rank 4/5, score=+0.059) — [MR] IC[neg_spread]=+0.292 @ h=1000 (sign=+1, t=+3.47, p=0.000512, FDR-pass); [MOM] hurst=0.56>0.55; [OBI] IC[obi_l1]=+0.059 @ h=1 (t=+10.31, p=0, FDR-pass); [PAIR] partner=UV_VISOR_MAGENTA corr=-0.87 coint_p=0.0416
- **UV_VISOR_MAGENTA** (rank 2/5, score=+0.059) — [MR] IC[neg_spread]=+0.155 @ h=1000 (sign=+1, t=+2.02, p=0.0431, FDR-pass); [OBI] IC[obi_l1]=+0.059 @ h=1 (t=+9.72, p=0, FDR-pass); [PAIR] partner=UV_VISOR_AMBER corr=-0.87 coint_p=0.0416; [TOP_MM_IN_FAMILY rank=1/5 score=+1.129]
- **UV_VISOR_ORANGE** (rank 5/5, score=+0.058) — [MR] IC[neg_spread]=+0.122 @ h=1000 (sign=+1, t=+1.92, p=0.0554, FDR-pass); [OBI] IC[obi_l1]=+0.058 @ h=1 (t=+9.90, p=0, FDR-pass); [PAIR] partner=UV_VISOR_AMBER corr=-0.71 coint_p=0.826; [TOP_MOM_IN_FAMILY rank=1/5 score=+1.366]
- **UV_VISOR_RED** (rank 3/5, score=+0.059) — [MR] IC[neg_spread]=+0.143 @ h=1000 (sign=+1, t=+2.78, p=0.00548, FDR-pass); [MOM] hurst=0.56>0.55; [OBI] IC[obi_l1]=+0.059 @ h=1 (t=+9.89, p=0, FDR-pass)
- **UV_VISOR_YELLOW** (rank 1/5, score=+0.061) — [OBI] IC[obi_l1]=+0.061 @ h=1 (t=+10.56, p=0, FDR-pass); [TOP_MM_IN_FAMILY rank=2/5 score=+1.099]

### PAIR_FLAG
- **UV_VISOR_AMBER** (rank 1/5, score=+0.831) — [MR] IC[neg_spread]=+0.292 @ h=1000 (sign=+1, t=+3.47, p=0.000512, FDR-pass); [MOM] hurst=0.56>0.55; [OBI] IC[obi_l1]=+0.059 @ h=1 (t=+10.31, p=0, FDR-pass); [PAIR] partner=UV_VISOR_MAGENTA corr=-0.87 coint_p=0.0416
- **UV_VISOR_MAGENTA** (rank 1/5, score=+0.831) — [MR] IC[neg_spread]=+0.155 @ h=1000 (sign=+1, t=+2.02, p=0.0431, FDR-pass); [OBI] IC[obi_l1]=+0.059 @ h=1 (t=+9.72, p=0, FDR-pass); [PAIR] partner=UV_VISOR_AMBER corr=-0.87 coint_p=0.0416; [TOP_MM_IN_FAMILY rank=1/5 score=+1.129]
- **UV_VISOR_ORANGE** (rank 5/5, score=+0.342) — [MR] IC[neg_spread]=+0.122 @ h=1000 (sign=+1, t=+1.92, p=0.0554, FDR-pass); [OBI] IC[obi_l1]=+0.058 @ h=1 (t=+9.90, p=0, FDR-pass); [PAIR] partner=UV_VISOR_AMBER corr=-0.71 coint_p=0.826; [TOP_MOM_IN_FAMILY rank=1/5 score=+1.366]

### TOP_MOM_IN_FAMILY (rank ≤ K but MOM_FLAG missed)
- **UV_VISOR_ORANGE** (rank 1/5, score=+1.366)

### TOP_MM_IN_FAMILY (rank ≤ K but MM_FLAG missed)
- **UV_VISOR_MAGENTA** (rank 1/5, score=+1.129)
- **UV_VISOR_YELLOW** (rank 2/5, score=+1.099)

### NO_EDGE
- _(none — every product carries at least one flag or top-rank)_
