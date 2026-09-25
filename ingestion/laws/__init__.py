from ingestion.laws.base import LawConfig
from ingestion.laws.ito2001 import ITO_2001

LAWS: dict[str, LawConfig] = {cfg.id_prefix: cfg for cfg in (ITO_2001,)}

__all__ = ["LAWS", "LawConfig"]
