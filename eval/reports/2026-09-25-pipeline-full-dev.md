# Retrieval eval — pipeline-full-dev (dev split, 2026-09-25)

| Group | n | Hit@5 | Recall@5 (all gold) | MRR@10 |
|---|---|---|---|---|
| english | 27 | 100.0% | 98.2% | 0.975 |
| urdu | 12 | 100.0% | 100.0% | 0.944 |
| roman_urdu | 12 | 75.0% | 70.8% | 0.720 |
| all | 51 | 94.1% | 92.2% | 0.908 |

## Misses (3)

| id | gold | top-5 retrieved |
|---|---|---|
| ru-004 | ITO2001-s59 | ITO2001-s59B, ITO2001-s56, ITR2002-r13P, ITO2001-s149, ITO2001-sch4 |
| ru-005 | ITO2001-s114 | ITO2001-s114B, ITO2001-s182, ITO2001-s118, ITR2002-r80, ITR2002-r81A |
| ru-010 | ITO2001-s181AA | ITR2002-r78O, ITR2002-r13O, ITO2001-s2, ITO2001-s99A, ITO2001-sch1-pI-divVIIIB |
