import comtradeapicall

df = comtradeapicall.previewFinalData(
    typeCode="C",
    freqCode="A",
    clCode="HS",
    period="2023",
    reporterCode="699",      # India
    cmdCode="TOTAL",
    flowCode="X",            # Exports
    partnerCode="0",         # World

    # Required in current comtradeapicall version
    partner2Code=None,
    customsCode=None,
    motCode=None,

    maxRecords=500,
    format_output="JSON",
    aggregateBy=None,
    breakdownMode="classic",
    countOnly=None,
    includeDesc=True
)

print(df.head())
print(df.columns)

df.to_csv("india_exports_world_2023_preview.csv", index=False)
print("Saved: india_exports_world_2023_preview.csv")