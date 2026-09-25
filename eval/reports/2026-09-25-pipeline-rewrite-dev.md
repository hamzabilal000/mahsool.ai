# Retrieval eval — pipeline-rewrite-dev (dev split, 2026-09-25)

| Group | n | Hit@5 | Recall@5 (all gold) | MRR@10 |
|---|---|---|---|---|
| english | 27 | 88.9% | 87.0% | 0.823 |
| urdu | 12 | 100.0% | 95.8% | 0.840 |
| roman_urdu | 12 | 91.7% | 87.5% | 0.696 |
| all | 51 | 92.2% | 89.2% | 0.797 |

## Misses (4)

| id | gold | top-5 retrieved |
|---|---|---|
| en-009 | ITO2001-s9 | ITO2001-s4, ITO2001-sch1-pI-divI, ITO2001-sch1-pI-divI, ITO2001-s18, ITO2001-s32 |
| en-055 | ITO2001-s150 | ITO2001-sch1-pIII-divI, ITO2001-sch1-pI-divIII, ITO2001-sch2-pII-cl9AD, ITO2001-sch2-pII-cl18C, ITO2001-s5 |
| en-059 | ITO2001-s153 | ITO2001-sch2-pIII-cl18, ITO2001-sch2-pII-cl9AD, ITO2001-s165C, ITO2001-sch2-pIV-cl70, ITO2001-sch2-pIV-cl45A |
| ru-004 | ITO2001-s59 | ITO2001-s57A, ITO2001-s59B, ITO2001-s59B, ITO2001-sch4, ITO2001-s57 |
