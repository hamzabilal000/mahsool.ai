# Retrieval eval — pipeline-fast-test (test split, 2026-09-26)

| Group | n | Hit@5 | Recall@5 (all gold) | MRR@10 |
|---|---|---|---|---|
| english | 73 | 98.6% | 95.0% | 0.940 |
| fbr | 39 | 87.2% | 87.2% | 0.783 |
| urdu | 28 | 92.9% | 88.1% | 0.903 |
| roman_urdu | 28 | 92.9% | 88.7% | 0.828 |
| all | 168 | 94.0% | 91.0% | 0.878 |

## Misses (10)

| id | gold | top-5 retrieved |
|---|---|---|
| en-070 | ITO2001-s168 | ITO2001-s8, ITO2001-sch10, ITO2001-s169, ITO2001-s153, ITO2001-s147 |
| ur-024 | ITO2001-s102 | ITO2001-s51, ITO2001-s101A, ITO2001-s44, ITO2001-s43, ITO2001-s109A |
| ur-034 | ITO2001-s168 | ITO2001-s8, ITO2001-s153, ITO2001-s4, ITO2001-s147, ITO2001-s169 |
| ru-024 | ITO2001-s102 | ITO2001-s51, ITO2001-s43, ITO2001-s101, ITO2001-s44, ITO2001-s109A |
| ru-034 | ITO2001-s168 | ITO2001-s8, ITO2001-s153, ITO2001-s4, ITO2001-s147, ITO2001-sch8 |
| fbr-006 | ITO2001-s2 | ITO2001-s46, ITO2001-s151, ITO2001-s7B, ITO2001-s28, ITO2001-s28 |
| fbr-008 | ITO2001-s2 | ITR2002-r18, ITO2001-s89, ITO2001-sch5-pI, ITO2001-s6, ITO2001-sch1-pI-divIV |
| fbr-013 | ITO2001-s2 | ITO2001-sch9-pIII, ITO2001-s109A, ITO2001-s9, ITO2001-s11, ITO2001-s111 |
| fbr-026 | ITO2001-s70 | ITO2001-s167, ITO2001-s162, ITO2001-s169, ITO2001-s161, ITO2001-s168 |
| fbr-029 | ITO2001-s21 | ITO2001-sch5-pI, ITO2001-s104, ITO2001-s20, ITO2001-s105, ITR2002-r13 |
