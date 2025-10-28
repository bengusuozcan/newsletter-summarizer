SUMMARY_SCHEMA = {
  "name": "newsletter_summary",
  "strict": True,
  "schema": {
    "type": "object",
    "additionalProperties": False,
    "properties": {
      "subject": {"type": "string"},
      "date_iso": {"type": "string", "format": "date-time"},
      "summary_4to5_sentences": {
        "type": "string",
        "description": "A concise 4-5 sentence summary of the newsletter content."
      },
      "highlights": {
        "type": "array",
        "items": {"type": "string"},
        "minItems": 3,
        "maxItems": 7,
        "description": "Most important highlights as short bullets."
      }
    },
    "required": ["subject", "date_iso", "summary_4to5_sentences", "highlights"]
  }
}
