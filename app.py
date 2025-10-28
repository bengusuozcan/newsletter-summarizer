import time, random
from openai import RateLimitError, APIError
import os, json, datetime as dt, argparse
from dotenv import load_dotenv
from openai import OpenAI
from summary_schema import SUMMARY_SCHEMA
from gmail_tools import (
    list_all_by_label, list_all_by_query, extract_plain_text,
    archive_message, get_or_create_label, add_label_id
)

# ---------- SETUP ----------
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# ---------- SUMMARIZER ----------
def summarize_email(subject, body, date_iso):
    """Summarize one newsletter with retries/backoff; works on older SDKs."""
    prompt = f"""
You summarize newsletters for a busy researcher.
- Write a faithful, neutral 4–5 sentence summary.
- Then produce 3–7 short 'highlights' bullets (most important points).
- Never invent links or facts. If uncertain, omit.

Return valid JSON:
{{
  "subject": "...",
  "date_iso": "...",
  "summary_4to5_sentences": "...",
  "highlights": ["point 1", "point 2", "..."]
}}

Now summarize:
Subject: {subject}
Date: {date_iso}
Content:
{body}
""".strip()

    # Retry with exponential backoff
    last_err = None
    for attempt in range(6):  # ~0s,1s,2s,4s,8s,16s
        try:
            resp = client.responses.create(model=MODEL, input=prompt)
            text = resp.output_text.strip()
            try:
                data = json.loads(text)
            except json.JSONDecodeError:
                data = {
                    "subject": subject,
                    "date_iso": date_iso,
                    "summary_4to5_sentences": text,
                    "highlights": [],
                }
            data.setdefault("subject", subject)
            data.setdefault("date_iso", date_iso)
            return data
        except (RateLimitError, APIError) as e:
            last_err = e
            sleep_s = min(16, 2 ** attempt) + random.random()
            time.sleep(sleep_s)
        except Exception as e:
            # Non-rate-limit errors: surface immediately
            raise
    # If we exhausted retries, re-raise the last rate-limit/API error
    raise last_err

# ---------- SAVE JSON ----------
def save_jsonl(rows, out_path):
    with open(out_path, "a", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


# ---------- JOBS ----------
def job_backlog_from_label(label_name: str, out_path="summaries_joshua_clear.jsonl"):
    """ONE-TIME: summarize EVERYTHING under an existing Gmail label."""
    msgs = list_all_by_label(label_name)
    results = []
    for m in msgs:
        subject, body = extract_plain_text(m)
        date_iso = dt.datetime.utcnow().isoformat() + "Z"
        summary = summarize_email(subject, body, date_iso)
        results.append(summary)
    save_jsonl(results, out_path)
    print(f"✅ Backlog complete: {len(results)} emails summarized → {out_path}")


def job_unread_from_address(address: str, label_to_apply: str,
                            archive=True, out_path="summaries_aiweekly.jsonl"):
    """Run once (or daily): unread from address → summarize → apply label (and optionally archive)."""
    q = f'from:{address} is:unread'
    msgs = list_all_by_query(q)
    if not msgs:
        print("No unread messages from that address.")
        return

    label_id = get_or_create_label(label_to_apply) if label_to_apply else None
    results = []

    for m in msgs:
        subject, body = extract_plain_text(m)
        date_iso = dt.datetime.utcnow().isoformat() + "Z"
        summary = summarize_email(subject, body, date_iso)
        results.append(summary)

        if label_id:
            add_label_id(m["id"], label_id)
        if archive:
            archive_message(m["id"])  # remove from Inbox to keep things tidy

    save_jsonl(results, out_path)
    print(f"✅ {len(results)} unread emails summarized and labeled '{label_to_apply}' → {out_path}")


# ---------- CLI ----------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Newsletter Summarizer")
    sub = parser.add_subparsers(dest="cmd")

    b = sub.add_parser("backlog", help="Summarize all emails under a Gmail label (one-time)")
    b.add_argument("--label", required=True,
                   help="Existing Gmail label name, e.g., 'Joshua Clear'")

    o = sub.add_parser("once", help="Summarize unread from a specific address (one-time)")
    o.add_argument("--from_addr", required=True, help="Email address to search (exact)")
    o.add_argument("--apply_label", default="Joshua Clear",
                   help="Label to apply after summarizing")
    o.add_argument("--no-archive", action="store_true",
                   help="Do not archive after labeling")

    d = sub.add_parser("daily",
                       help="Daily mode: unread from address -> summarize -> label -> archive")
    d.add_argument("--from_addr", required=True, help="Email address to search")
    d.add_argument("--apply_label", default="Joshua Clear",
                   help="Label to apply after summarizing")

    args = parser.parse_args()

    if args.cmd == "backlog":
        job_backlog_from_label(args.label)
    elif args.cmd == "once":
        job_unread_from_address(
            args.from_addr, args.apply_label, archive=not args.no_archive)
    elif args.cmd == "daily":
        job_unread_from_address(args.from_addr, args.apply_label, archive=True)
    else:
        parser.print_help()
