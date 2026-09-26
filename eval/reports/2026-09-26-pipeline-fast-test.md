# Retrieval eval — pipeline-fast-test (test split, 2026-09-26)

| Group | n | Hit@5 | Recall@5 (all gold) | MRR@10 |
|---|---|---|---|---|
| english | 73 | 98.6% | 95.0% | 0.933 |
| fbr | 39 | 94.9% | 94.9% | 0.913 |
| urdu | 28 | 92.9% | 88.1% | 0.903 |
| roman_urdu | 28 | 92.9% | 88.7% | 0.828 |
| all | 168 | 95.8% | 92.8% | 0.906 |

## Misses (7)

| id | gold | top-5 retrieved |
|---|---|---|
| en-070 | ITO2001-s168 | ITO2001-s8, ITO2001-sch10, ITO2001-s169, ITO2001-s153, ITO2001-s147 |
| ur-024 | ITO2001-s102 | ITO2001-s51, ITO2001-s101A, ITO2001-s44, ITO2001-s43, ITO2001-s109A |
| ur-034 | ITO2001-s168 | ITO2001-s8, ITO2001-s153, ITO2001-s4, ITO2001-s147, ITO2001-s169 |
| ru-024 | ITO2001-s102 | ITO2001-s51, ITO2001-s43, ITO2001-s101, ITO2001-s44, ITO2001-s109A |
| ru-034 | ITO2001-s168 | ITO2001-s8, ITO2001-s153, ITO2001-s4, ITO2001-s147, ITO2001-sch8 |
| fbr-026 | ITO2001-s70 | ITO2001-s167, ITO2001-s162, ITO2001-s169, ITO2001-s161, ITO2001-s168 |
| fbr-029 | ITO2001-s21 | ITO2001-sch5-pI, ITO2001-s104, ITO2001-s20, ITO2001-s105, ITR2002-r13 |
