# Retrieval eval — pipeline-fast-gte-d69-test (test split, 2026-10-02)

| Group | n | Hit@5 | Recall@5 (all gold) | MRR@10 |
|---|---|---|---|---|
| english | 73 | 98.6% | 95.2% | 0.886 |
| fbr | 39 | 97.4% | 97.4% | 0.904 |
| urdu | 28 | 100.0% | 98.8% | 0.914 |
| roman_urdu | 28 | 100.0% | 95.2% | 0.866 |
| all | 168 | 98.8% | 96.3% | 0.892 |

## Misses (2)

| id | gold | top-5 retrieved |
|---|---|---|
| en-087 | ITO2001-s37, ITO2001-sch1-pI-divVIII | ITO2001-sch2-pIII-cl9A, ITO2001-sch1-pI-divVII, ITO2001-sch1-pI-divVII, ITR2002-r13N, ITO2001-sch1-pIV-divXVIII |
| fbr-029 | ITO2001-s21 | ITO2001-sch5-pI, ITO2001-s20, ITR2002-r13, ITO2001-s105, ITO2001-s22 |
