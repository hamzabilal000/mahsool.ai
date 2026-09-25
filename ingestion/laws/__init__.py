from ingestion.laws.base import LawConfig
from ingestion.laws.ito2001 import ITO_2001
from ingestion.laws.itr2002 import ITR_2002
from ingestion.laws.wht2027 import WHT_2027

LAWS: dict[str, LawConfig] = {cfg.id_prefix: cfg for cfg in (ITO_2001, ITR_2002, WHT_2027)}

__all__ = ["LAWS", "LawConfig"]
