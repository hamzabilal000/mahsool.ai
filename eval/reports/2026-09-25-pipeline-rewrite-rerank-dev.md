# Retrieval eval — pipeline-rewrite-rerank-dev (dev split, 2026-09-25)

| Group | n | Hit@5 | Recall@5 (all gold) | MRR@10 |
|---|---|---|---|---|
| english | 27 | 100.0% | 98.2% | 0.975 |
| urdu | 12 | 91.7% | 91.7% | 0.931 |
| roman_urdu | 12 | 75.0% | 70.8% | 0.639 |
| all | 51 | 92.2% | 90.2% | 0.886 |

## Misses (4)

| id | gold | top-5 retrieved |
|---|---|---|
| ur-007 | ITO2001-s118 | ITO2001-sch1-pIV-divVII, ITO2001-sch9-pII, ITO2001-sch1-pI-divI, ITO2001-sch1-pI-divIIB, ITO2001-sch1-pI-divI |
| ru-004 | ITO2001-s59 | ITO2001-s59B, ITO2001-s56, ITO2001-sch7, ITR2002-r13P, ITO2001-s149 |
| ru-005 | ITO2001-s114 | ITO2001-s114B, ITO2001-s182, ITO2001-s118, ITR2002-r80, ITO2001-s121 |
| ru-010 | ITO2001-s181AA | ITO2001-s182, ITR2002-r19H, ITR2002-r81A, ITR2002-r13ZC, ITR2002-r78O |
