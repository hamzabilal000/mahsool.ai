# ruff: noqa: E501  (law text, kept on one line per cell run)
"""Layout fixes for the Ordinance (DECISIONS D69): merged table cells the PDF text layer splits
across rows, put back together in the first row. Same words, same order; only the "|" cell
borders move (`ingestion.chunk.apply_layout_fixes` checks it)."""

# Divisions VII (securities) and VIII (property) of Part I of the First Schedule: the last column
# (assets acquired on or after 1 July 2024) is one merged cell for every holding period.
LAYOUT_FIXES: dict[str, list[tuple[str, str]]] = {
    "ITO2001-sch1-pI-divVII-t1": [
        (
            "| 1. | Where the holding period does not exceed one year | 15% | 15% for persons appearing on the Active Taxpayers’ List on the date of acquisition and the date of disposal of |\n| 2. | Where the holding period exceeds one | 12.5% |  |\n| year but does not exceed two years | securities and at the rate specified in Division I for individuals and association of persons and Division II for companies in respect of persons not appearing on the Active Taxpayers’ List on the date of acquisition and date of disposal of securities: Provided that the rate of tax for individuals and association of persons not appearing on the Active Taxpayers’ List, the rate of tax shall not be less than 15% in any case. |  |  |\n",
            "| 1. | Where the holding period does not exceed one year | 15% | 15% for persons appearing on the Active Taxpayers’ List on the date of acquisition and the date of disposal of securities and at the rate specified in Division I for individuals and association of persons and Division II for companies in respect of persons not appearing on the Active Taxpayers’ List on the date of acquisition and date of disposal of securities: Provided that the rate of tax for individuals and association of persons not appearing on the Active Taxpayers’ List, the rate of tax shall not be less than 15% in any case. |\n| 2. | Where the holding period exceeds one year but does not exceed two years | 12.5% |  |\n",
        ),
    ],
    "ITO2001-sch1-pI-divVIII-t1": [
        (
            "| 1. | Where the holding period does not exceed one year | 15% | 15% . . | 15% | 15% for persons appearing on the Active Taxpayers’ List |\n| 2. | Where the holding period exceeds one year but does not exceed two years | 12.5% | 10% | 7.5% | on date of disposal of property and at the rates specified in Division I for individuals and association of persons and Division II for companies in respect of persons not appearing on the Active Taxpayers’ List on the date of disposal of property: Provided that the rate of tax for individuals and association of persons not appearing on the Active Taxpayers’ List on the date of disposal, the rate of tax shall not be less than 15% of the gain. |\n",
            "| 1. | Where the holding period does not exceed one year | 15% | 15% . . | 15% | 15% for persons appearing on the Active Taxpayers’ List on date of disposal of property and at the rates specified in Division I for individuals and association of persons and Division II for companies in respect of persons not appearing on the Active Taxpayers’ List on the date of disposal of property: Provided that the rate of tax for individuals and association of persons not appearing on the Active Taxpayers’ List on the date of disposal, the rate of tax shall not be less than 15% of the gain. |\n| 2. | Where the holding period exceeds one year but does not exceed two years | 12.5% | 10% | 7.5% |  |\n",
        ),
    ],
}
