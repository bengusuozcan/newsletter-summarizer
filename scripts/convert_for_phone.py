import json, textwrap, argparse, re

def main():
    p = argparse.ArgumentParser(description="Convert JSONL summaries to clean phone text")
    p.add_argument("--in", dest="inp", default="summaries_daily.jsonl", help="Input .jsonl")
    p.add_argument("--out", dest="out", default="summaries_for_phone.txt", help="Output .txt")
    p.add_argument("--wrap", dest="wrap", type=int, default=100, help="Line wrap width")
    args = p.parse_args()

    wrap = lambda s: "\n".join(textwrap.wrap((s or "").strip(), width=args.wrap)) if s else ""

    first = True
    with open(args.inp, encoding="utf-8") as f, open(args.out, "w", encoding="utf-8") as out:
        for line in f:
            if not line.strip(): continue
            j = json.loads(line)
            subj = (j.get("subject") or "").strip().upper()
            date = (j.get("date_iso") or "").split("T")[0]
            summary = j.get("summary_4to5_sentences") or j.get("summary") or ""
            highlights = j.get("highlights") or []

            if not first: out.write("\n" + "-"*40 + "\n\n")
            first = False
            out.write(f"{subj}\n")
            out.write(f"Date: {date}\n\n")
            out.write("Summary:\n" + wrap(summary) + "\n\n")
            if highlights:
                out.write("Highlights:\n")
                for h in highlights:
                    h = re.sub(r"```.*?```", "", h, flags=re.DOTALL)
                    h = re.sub(r"\s+", " ", h).strip()
                    out.write(f"• {h}\n")

if __name__ == "__main__":
    main()
