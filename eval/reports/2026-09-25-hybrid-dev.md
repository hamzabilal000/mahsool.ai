# Retrieval eval — hybrid-dev (dev split, 2026-09-25)

| Group | n | Hit@5 | Recall@5 (all gold) | MRR@10 |
|---|---|---|---|---|
| english | 27 | 92.6% | 90.7% | 0.847 |
| urdu | 12 | 83.3% | 70.8% | 0.649 |
| roman_urdu | 12 | 66.7% | 66.7% | 0.521 |
| all | 51 | 84.3% | 80.4% | 0.723 |

## Misses (8)

| id | gold | top-5 retrieved |
|---|---|---|
| en-051 | ITO2001-s137 | ITO2001-s127, ITO2001-s124, ITO2001-s122, ITO2001-s122D, ITO2001-s122 |
| en-059 | ITO2001-s153 | ITO2001-sch2-pIV-cl70, ITO2001-sch2-pII-cl9AD, ITO2001-sch2-pIV-cl45A, ITO2001-sch2-pIII-cl18, ITO2001-s165C |
| ur-005 | ITO2001-s114 | ITO2001-sch1-pIIB, ITR2002-r231I, ITO2001-s15, ITR2002-r13P, ITO2001-sch1-pIII-divV |
| ur-007 | ITO2001-s118 | ITO2001-sch1-pI-divI, ITO2001-sch1-pIV-divIII, ITO2001-sch1-pI-divI, ITO2001-sch1-pIIB, ITO2001-sch6-pI |
| ru-004 | ITO2001-s59 | ITO2001-s59B, ITR2002-r13F, ITR2002-r13P, ITR2002-r13P, ITO2001-sch4 |
| ru-009 | ITO2001-sch1-pIII-divV | ITO2001-s31, ITO2001-s231AB, ITO2001-sch1-pI-divII, ITO2001-s152, ITO2001-s153 |
| ru-010 | ITO2001-s181AA | ITO2001-s2, WHT2027-s235, ITO2001-sch12, ITO2001-sch5-pII, ITO2001-sch5-pI |
| ru-012 | ITO2001-s236C, ITO2001-sch1-pIV-divX | ITO2001-s147, ITO2001-s7D, ITO2001-s236O, ITO2001-s236A, ITO2001-s147A |
