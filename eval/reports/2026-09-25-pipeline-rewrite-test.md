# Retrieval eval — pipeline-rewrite-test (test split, 2026-09-25)

| Group | n | Hit@5 | Recall@5 (all gold) | MRR@10 |
|---|---|---|---|---|
| english | 63 | 98.4% | 97.6% | 0.876 |
| fbr | 39 | 84.6% | 84.6% | 0.677 |
| urdu | 28 | 100.0% | 96.4% | 0.896 |
| roman_urdu | 28 | 89.3% | 83.9% | 0.798 |
| all | 158 | 93.7% | 91.8% | 0.816 |

## Misses (10)

| id | gold | top-5 retrieved |
|---|---|---|
| en-088 | ITO2001-s37A, ITO2001-sch1-pI-divVII | ITR2002-r13P, ITR2002-r13P, ITR2002-r13N, ITO2001-sch8, ITO2001-s100B |
| ru-024 | ITO2001-s102 | ITO2001-s101, ITO2001-s44, ITO2001-s105, ITO2001-s51, ITO2001-s43 |
| ru-029 | ITO2001-s137 | ITO2001-s114, ITO2001-sch9-pIII, ITO2001-sch2-pI-cl145A, ITO2001-s119, ITO2001-s182A |
| ru-039 | ITO2001-s236Y, ITO2001-sch1-pIV-divXXVII | ITO2001-s152, ITO2001-s21, WHT2027-s153, ITO2001-s165C, ITO2001-s6A |
| fbr-006 | ITO2001-s2 | ITO2001-s7B, ITO2001-s151, ITO2001-s46, ITO2001-sch1-pI-divIIIA, ITO2001-s28 |
| fbr-008 | ITO2001-s2 | ITR2002-r18, ITO2001-s6, ITO2001-sch5-pI, ITO2001-sch1-pI-divIV, ITO2001-s89 |
| fbr-009 | ITO2001-s2 | ITR2002-r19, ITO2001-s152, ITO2001-s154A, ITO2001-sch1-pI-divIV, ITO2001-s222A |
| fbr-010 | ITO2001-s2 | ITO2001-sch6-pIII, ITR2002-r115, ITR2002-r118, ITO2001-sch6-pIII, ITR2002-r116 |
| fbr-013 | ITO2001-s2 | ITO2001-sch7, ITR2002-r19H, ITO2001-s18, ITO2001-s11, ITO2001-sch9-pIII |
| fbr-026 | ITO2001-s70 | ITO2001-s162, ITO2001-s169, ITO2001-s138A, ITR2002-r168, ITO2001-s22 |
