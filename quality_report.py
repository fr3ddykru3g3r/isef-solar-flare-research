"""QUALITY value counts per month across the full range, from the raw (pre-filter) files.

Bit meanings quoted verbatim from the JSOC/HMI QUALITY documentation:
  http://jsoc.stanford.edu/doc/data/hmi/Quality_Bits/QUALITY.txt  (NB: UPDATED ON MAY 24, 2013)
The filter QUALITY == 0 is NOT changed here; this only reports what is being excluded.
"""
import glob
import pandas as pd

# verbatim from the JSOC doc above, "Line-of-Sight and Vector field data products
# CREATED BUT IN SUB-OPTIMAL CONDITIONS, QUALITY > 0" section
BITS = {
    0x00010000: ("QUAL_LOWINTERPNUM", "the number of averaging points is lower than TempIntNum, AND/OR 2 interpolation points were separated by more than the cadence"),
    0x00008000: ("QUAL_LOWKEYWORDNUM", "some keywords (especially CROTA2, DSUN_OBS, and CRLT_OBS) could not be interpolated properly at target time, but a closest-neighbour approximation was used"),
    0x00004000: ("QUAL_ISSTARGET", "the ISS loop was OPEN for one or several filtergrams used to produce the observable"),
    0x00002000: ("QUAL_NOTEMP", "cannot read the temperatures needed for polarization calibration (default temperature used)"),
    0x00001000: ("QUAL_NOGAPFILL", "the code could not properly gap-fill all the lev 1 filtergrams"),
    0x00000800: ("QUAL_LIMBFITISSUE", "some lev1 records were discarded because R_SUN, and/or CRPIX1/CRPIX2 were missing or too different from the median value of the other lev 1 records (too much jitter for instance)"),
    0x00000400: ("QUAL_NOCOSMICRAY", "some cosmic-ray hit lists could not be read for the level 1 filtergrams"),
    0x00000200: ("QUAL_ECLIPSE", "at least one lev1 record was taken during an eclipse"),
    0x00000100: ("QUAL_LARGEFTSID", "HFTSACID of target filtergram > 4000, which adds noise to observables"),
    0x00000080: ("QUAL_TEMPERROR", "Code error discovered, will be corrected in later versions, see notes at http://jsoc2.stanford.edu/doc/data/hmi/Quality_Bits"),
    0x00000020: ("QUAL_POORQUALITY", "poor quality: careful when using these observables due to eclipse, or lunar transit, or thermal recovery, or open ISS, or other issues..."),
}


def main():
    per_month, seen = [], {}
    for f in sorted(glob.glob("data/raw_sharp_*.csv")):
        stem = f.split("raw_sharp_")[1][:8]
        if len(stem) != 8 or not stem.isdigit():
            continue
        month = f"{stem[:4]}-{stem[4:6]}"
        q = pd.to_numeric(pd.read_csv(f, usecols=["QUALITY"], low_memory=False)["QUALITY"], errors="coerce").dropna().astype(int)
        per_month.append({"month": month, "rows": len(q), "quality_zero": int((q == 0).sum()),
                          "top_values": dict(q.value_counts().head(4))})
        for v in q.unique():
            for bit in BITS:
                if v & bit:
                    seen[bit] = seen.get(bit, 0) + int((q == v).sum())

    df = pd.DataFrame(per_month).sort_values("month")
    df["pct_zero"] = df["quality_zero"] / df["rows"]
    df.to_csv("data/quality_report.csv", index=False)

    print("QUALITY per month (raw, pre-filter)")
    print("month     rows  QUALITY==0   %zero   most common values")
    for _, r in df.iterrows():
        print(f"{r['month']}  {r['rows']:6d}  {r['quality_zero']:9d}  {r['pct_zero']:6.1%}   {r['top_values']}")

    empty = df[df["quality_zero"] == 0]
    print(f"\nmonths with ZERO QUALITY==0 rows: {len(empty)}")
    for _, r in empty.iterrows():
        print(f"  {r['month']}  ({r['rows']} raw rows, all excluded)  values: {r['top_values']}")

    print("\ndocumented meaning of each bit that appears in this range")
    print("(verbatim, http://jsoc.stanford.edu/doc/data/hmi/Quality_Bits/QUALITY.txt, updated 2013-05-24)")
    for bit in sorted(seen, reverse=True):
        name, desc = BITS[bit]
        print(f"  0x{bit:08X}  {name:22s} affected rows ~{seen[bit]}\n      {desc}")


REPROCESSING_NOTE = """
QUAL_TEMPERROR (0x80) -- what JSOC actually documents
  QUALITY.notes (http://jsoc.stanford.edu/doc/data/hmi/Quality_Bits/QUALITY.notes,
  last modified 2017-09-19) states verbatim:

    "In cases where 45s or 720s data exists and there is a code error detected
     we will set bit 0x80 for existing records while they are waiting replacement
     with reprocesed data.  the cases where this has happened include:
       1.  Sept 2017.  for CALVER64 masked with 0xF0000 leaves 0x20000 for the initial
           year+ of modL data, we set QUALITY 0x80 while waiting for reprocessing
           of hmi.S_720s and all of its derived products.  The records with this
           QUALITY bit set should not be visible once the reprocessing is done.
           It is expected to take several months."

  So 0x80 marks records held pending replacement by reprocessed data. The only
  period JSOC enumerates in these notes is Sept 2017. The May 2016 records we see
  are NOT covered by any documented case we could find, and they still carried the
  bit when queried on 2026-09-21 -- i.e. we have no JSOC statement that they were
  reprocessed, and no JSOC statement about why they are flagged.

  This is a flagged processing error, not evidence either way about the underlying
  data. We do not infer data quality from the bit name. QUALITY == 0 stays.
"""

if __name__ == "__main__":
    main()
    print(REPROCESSING_NOTE)
