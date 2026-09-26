"""GET /eval/summary and GET /eval/ablation.png — the public evaluation page's data.

Both are committed files written by the eval scripts (`python -m eval.summary`,
`python -m eval.plot_ablation`), so the page shows exactly what the reports say.
"""

import json
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse, JSONResponse

REPORTS = Path(__file__).resolve().parents[3] / "eval" / "reports"
router = APIRouter(prefix="/eval")


def not_found(what: str) -> JSONResponse:
    content = {"success": False, "data": None, "error": f"{what} not generated yet",
               "code": "NOT_FOUND"}  # fmt: skip
    return JSONResponse(status_code=404, content=content)


@router.get("/summary")
async def summary() -> JSONResponse:
    path = REPORTS / "summary.json"
    if not path.exists():
        return not_found("eval/reports/summary.json")
    data = json.loads(path.read_text(encoding="utf-8"))
    return JSONResponse({"success": True, "data": data, "error": None, "code": "OK"})


@router.get("/ablation.png", response_model=None)
async def ablation_chart() -> FileResponse | JSONResponse:
    path = REPORTS / "ablation-test.png"
    if not path.exists():
        return not_found("eval/reports/ablation-test.png")
    return FileResponse(path, media_type="image/png")
