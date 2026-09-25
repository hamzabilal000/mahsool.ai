# Retrieval eval — pipeline-lookup-rerank-dev (dev split, 2026-09-25)

| Group | n | Hit@5 | Recall@5 (all gold) | MRR@10 |
|---|---|---|---|---|
| english | 27 | 100.0% | 98.2% | 0.975 |
| urdu | 12 | 83.3% | 83.3% | 0.833 |
| roman_urdu | 12 | 75.0% | 70.8% | 0.616 |
| all | 51 | 90.2% | 88.2% | 0.857 |

## Misses (5)

| id | gold | top-5 retrieved |
|---|---|---|
| ur-005 | ITO2001-s114 | ITO2001-sch1-pIV-divIV, WHT2027-s235, ITO2001-s63A, ITO2001-sch1-pIII-divV, WHT2027-s155 |
| ur-007 | ITO2001-s118 | ITO2001-sch1-pIV-divVII, ITO2001-sch1-pI-divI, ITO2001-sch1-pI-divIIB, ITO2001-sch1-pI-divI, WHT2027-s149 |
| ru-004 | ITO2001-s59 | ITO2001-s59B, ITO2001-s56, ITR2002-r13P, ITO2001-s149, ITO2001-sch4 |
| ru-005 | ITO2001-s114 | ITO2001-s114B, ITO2001-s182, ITO2001-s118, ITR2002-r80, ITR2002-r81A |
| ru-010 | ITO2001-s181AA | ITR2002-r81A, ITR2002-r78O, ITR2002-r83C, ITR2002-r83C, ITR2002-r13O |
