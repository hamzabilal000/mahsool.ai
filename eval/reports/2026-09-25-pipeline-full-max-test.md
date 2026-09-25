# Retrieval eval — pipeline-full-max-test (test split, 2026-09-25)

| Group | n | Hit@5 | Recall@5 (all gold) | MRR@10 |
|---|---|---|---|---|
| english | 63 | 96.8% | 96.0% | 0.927 |
| urdu | 28 | 92.9% | 89.3% | 0.875 |
| roman_urdu | 28 | 92.9% | 91.1% | 0.824 |
| all | 119 | 95.0% | 93.3% | 0.891 |

## Misses (6)

| id | gold | top-5 retrieved |
|---|---|---|
| en-070 | ITO2001-s168 | ITO2001-s8, ITO2001-sch10, ITO2001-s146D, ITO2001-s4, ITO2001-s169 |
| en-076 | ITO2001-s181A | WHT2027-s156, WHT2027-s149, WHT2027-s233, WHT2027-s156A, WHT2027-s236A |
| ur-024 | ITO2001-s102 | ITO2001-s51, ITO2001-s101A, ITO2001-s44, ITO2001-s105, ITO2001-s43 |
| ur-034 | ITO2001-s168 | ITO2001-s146D, ITO2001-s8, ITO2001-s153, ITO2001-s4, ITO2001-s147 |
| ru-024 | ITO2001-s102 | ITO2001-s51, ITR2002-r43, ITO2001-s43, ITO2001-s101, ITO2001-s44 |
| ru-034 | ITO2001-s168 | ITO2001-sch4, ITO2001-s8, ITO2001-sch10, ITO2001-s153, ITO2001-s4 |
