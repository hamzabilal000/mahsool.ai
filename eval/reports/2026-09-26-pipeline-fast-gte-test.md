# Retrieval eval — pipeline-fast-gte-test (test split, 2026-09-26)

| Group | n | Hit@5 | Recall@5 (all gold) | MRR@10 |
|---|---|---|---|---|
| english | 73 | 97.3% | 94.3% | 0.888 |
| fbr | 39 | 97.4% | 97.4% | 0.816 |
| urdu | 28 | 96.4% | 93.5% | 0.862 |
| roman_urdu | 28 | 89.3% | 83.9% | 0.771 |
| all | 168 | 95.8% | 93.2% | 0.848 |

## Misses (7)

| id | gold | top-5 retrieved |
|---|---|---|
| en-087 | ITO2001-s37, ITO2001-sch1-pI-divVIII | ITO2001-sch2-pIII-cl9A, ITO2001-sch1-pI-divVII, ITO2001-sch1-pI-divVII, ITR2002-r13N, ITO2001-sch1-pIV-divXVIII |
| ur-024 | ITO2001-s102 | ITO2001-s51, ITO2001-sch2-pII-cl5AB, ITO2001-s44, ITO2001-s43, ITO2001-s103 |
| ru-016 | ITO2001-s41 | ITO2001-sch1-pI-divI, ITO2001-s49, ITO2001-s99D, ITO2001-sch2-pI-cl105B, ITO2001-s39 |
| ru-024 | ITO2001-s102 | ITO2001-s51, ITO2001-s101, ITO2001-s44, ITO2001-s43, ITO2001-sch2-pII-cl5AA |
| ru-030 | ITO2001-s149 | ITO2001-sch2-pI-cl23A, ITO2001-s12, ITR2002-r78B, ITO2001-sch1-pI-divI, ITR2002-r78B |
| fbr-003 | ITO2001-s12 | ITO2001-s146B, ITO2001-s146D, ITO2001-s149, ITO2001-s110, ITO2001-s205 |
| en-100 | ITO2001-s115, ITO2001-s114 | ITO2001-s101, ITO2001-s51, ITO2001-s105, ITO2001-s143, ITO2001-s101A |
