---
name: written-materials
description: Use when the player reads or examines written content like leaflets, signs, books, scrolls, or inscriptions.
---

# Written Materials

## When to Apply

Apply this skill when the player:
- Reads something: read, peruse, study
- Examines written content: examine, look at, inspect
- Opens a document: open, unfold

## Types of Written Materials

- Leaflets
- Signs
- Books
- Scrolls
- Terminal screens
- Inscriptions
- Notes
- Letters
- Plaques

## Critical Rule: Verbatim Quoting

When the player reads, examines, or opens a written item, you MUST quote its `description` text **exactly as written in the data**.

Do NOT:
- Paraphrase the text
- Summarize the content
- Embellish or add to the text
- Interpret the meaning

## Allowed Framing

You may add brief atmospheric framing before the quote:
- "The leaflet reads:"
- "The inscription says:"
- "The sign proclaims:"
- "Faded words on the page:"

But the content itself must be **verbatim**.

## Example

**Location data:**
```json
{
  "interactables": [
    {
      "id": "welcome_sign",
      "name": "Welcome Sign",
      "description": "WELCOME TO DUNGEON-1. AUTHORIZED PERSONNEL ONLY. TRESPASSERS WILL BE PROCESSED."
    }
  ]
}
```

**Player:** "read sign"

**Correct response:**
> The sign reads:
>
> WELCOME TO DUNGEON-1. AUTHORIZED PERSONNEL ONLY. TRESPASSERS WILL BE PROCESSED.

**Incorrect response:**
> The sign welcomes you to Dungeon-1 and warns that only authorized personnel should enter.

## Preserving Formatting

If the written material has specific formatting (caps, line breaks, etc.), preserve it:
- ALL CAPS should remain ALL CAPS
- Line breaks should be maintained
- Special characters should be included

## Multiple Readings

If the player reads the same material again, quote it again exactly. Don't say "You already read that" unless they've read it multiple times in immediate succession.

## Unreadable Materials

If something is:
- Too faded to read
- In an unknown language
- Damaged beyond legibility

Describe what they see, but don't invent text that wasn't in the data.

## Never Do

- Never summarize written content
- Never paraphrase inscriptions
- Never add your own interpretation
- Never invent text not in the data
