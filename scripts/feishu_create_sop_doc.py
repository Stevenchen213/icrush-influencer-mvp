"""Create Feishu doc from SOP markdown — all block_type=2 with inline styles."""
import os, sys, asyncio, httpx, re
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

ROOT = Path(__file__).resolve().parent.parent
SOP_MD = ROOT / "docs" / "达人二次判断-SOP.md"

APP_ID = os.environ["FEISHU_APP_ID"]
APP_SECRET = os.environ["FEISHU_APP_SECRET"]


def parse_inline(text: str) -> list[dict]:
    """Parse **bold** and `code` inline markup into text_run elements."""
    elements = []
    pattern = re.compile(r'(\*\*.*?\*\*|`.*?`)')
    parts = pattern.split(text)
    for part in parts:
        if not part:
            continue
        if part.startswith("**") and part.endswith("**"):
            elements.append({
                "text_run": {
                    "content": part[2:-2],
                    "text_element_style": {"bold": True}
                }
            })
        elif part.startswith("`") and part.endswith("`"):
            elements.append({
                "text_run": {
                    "content": part[1:-1],
                    "text_element_style": {"inline_code": True}
                }
            })
        else:
            elements.append({"text_run": {"content": part}})
    return elements


def make_block(elements: list[dict], heading_level: int = 0) -> dict:
    """Build a block_type=2 paragraph with optional heading style."""
    block = {
        "block_type": 2,
        "text": {
            "elements": elements,
            "style": {},
        }
    }
    if heading_level >= 1 and heading_level <= 3:
        block["text"]["style"]["heading_level"] = heading_level
    return block


def markdown_to_blocks(md_text: str) -> list[dict]:
    """Convert markdown to Feishu blocks (all block_type=2 with text styles).

    Heading levels via heading_level style. Lists via • prefix. Tables via
    indented text rows. Dividers via em-dash line.
    """
    blocks = []
    lines = md_text.split("\n")
    i = 0

    def parse_table_row(line: str) -> list[str]:
        return [cell.strip() for cell in line.strip("|").split("|")]

    in_table_headers = None
    in_table_rows = []
    in_code_block = False

    while i < len(lines):
        line = lines[i]

        # Code blocks: skip entirely
        if line.strip().startswith("```"):
            in_code_block = not in_code_block
            i += 1
            continue
        if in_code_block:
            i += 1
            continue

        # Blank line
        if not line.strip():
            i += 1
            continue

        # Separator (---)
        if line.strip() == "---":
            blocks.append(make_block(
                [{"text_run": {"content": "─" * 50, "text_element_style": {"bold": False}}}]
            ))
            i += 1
            continue

        # Table
        if "|" in line and line.strip().startswith("|"):
            row = parse_table_row(line)
            # Skip alignment rows like |---|---|
            if all(re.match(r"^[-:]+$", c) for c in row):
                i += 1
                continue

            if in_table_headers is None:
                in_table_headers = row
            else:
                in_table_rows.append(row)

            # Peek ahead: if next line is NOT a table row, flush
            if i + 1 >= len(lines) or "|" not in lines[i + 1]:
                # Header row
                header_els = []
                for j, h in enumerate(in_table_headers):
                    if j > 0:
                        header_els.append({"text_run": {"content": "  |  "}})
                    header_els.append({"text_run": {"content": h, "text_element_style": {"bold": True}}})
                blocks.append(make_block(header_els))

                # Separator below header
                blocks.append(make_block(
                    [{"text_run": {"content": "─" * 50}}]
                ))

                # Data rows
                for row in in_table_rows:
                    row_els = []
                    for j, cell in enumerate(row):
                        if j > 0:
                            row_els.append({"text_run": {"content": "  |  "}})
                        row_els.extend(parse_inline(cell))
                    blocks.append(make_block(row_els))

                # Blank line after table
                blocks.append(make_block([{"text_run": {"content": ""}}]))

                in_table_headers = None
                in_table_rows = []

            i += 1
            continue

        # h1
        h1_match = re.match(r'^#\s+(.+)$', line)
        if h1_match:
            els = parse_inline(h1_match.group(1))
            blocks.append(make_block(els, heading_level=1))
            i += 1
            continue

        # h2
        h2_match = re.match(r'^##\s+(.+)$', line)
        if h2_match:
            els = parse_inline(h2_match.group(1))
            blocks.append(make_block(els, heading_level=2))
            i += 1
            continue

        # h3
        h3_match = re.match(r'^###\s+(.+)$', line)
        if h3_match:
            els = parse_inline(h3_match.group(1))
            blocks.append(make_block(els, heading_level=3))
            i += 1
            continue

        # Blockquote → emoji-prefixed paragraph
        if line.startswith(">"):
            content = line.lstrip("> ").strip()
            blocks.append(make_block(
                [{"text_run": {"content": f"💡 {content}"}}]
            ))
            i += 1
            continue

        # Unordered list
        li_match = re.match(r'^[\-\*]\s+(.+)$', line)
        if li_match:
            els = [{"text_run": {"content": "• "}}]
            els.extend(parse_inline(li_match.group(1)))
            blocks.append(make_block(els))
            i += 1
            continue

        # Ordered list
        ol_match = re.match(r'^\d+\.\s+(.+)$', line)
        if ol_match:
            num = ol_match.group(0).split(".")[0]
            els = [{"text_run": {"content": f"{num}. "}}]
            els.extend(parse_inline(ol_match.group(1)))
            blocks.append(make_block(els))
            i += 1
            continue

        # Bold-only short line → heading 3
        bold_line = re.match(r'^\*\*(.+)\*\*$', line.strip())
        if bold_line and len(line.strip()) < 60:
            blocks.append(make_block(
                [{"text_run": {"content": bold_line.group(1), "text_element_style": {"bold": True}}}],
                heading_level=3
            ))
            i += 1
            continue

        # Regular paragraph
        els = parse_inline(line)
        if els:
            blocks.append(make_block(els))
        i += 1

    return blocks


async def main():
    async with httpx.AsyncClient(timeout=30) as c:
        # 1. Get tenant access token
        r = await c.post(
            "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
            json={"app_id": APP_ID, "app_secret": APP_SECRET},
        )
        if not r.is_success:
            print(f"Token ERROR {r.status_code}: {r.text}")
            return
        token = r.json()["tenant_access_token"]

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        # 2. Create doc
        r = await c.post(
            "https://open.feishu.cn/open-apis/docx/v1/documents",
            headers=headers,
            json={"title": "达人二次判断 — 操作 SOP"},
        )
        if not r.is_success:
            print(f"Create doc ERROR {r.status_code}: {r.text}")
            return
        doc_id = r.json()["data"]["document"]["document_id"]
        doc_url = f"https://icrush.feishu.cn/docx/{doc_id}"
        print(f"Doc created: {doc_url}")

        # 3. Convert markdown to blocks
        md_text = SOP_MD.read_text(encoding="utf-8")
        blocks = markdown_to_blocks(md_text)
        print(f"Blocks: {len(blocks)}")

        # 4. Add blocks in batches of 50
        page_id = doc_id
        errors = 0
        for batch_start in range(0, len(blocks), 50):
            batch = blocks[batch_start : batch_start + 50]
            r = await c.post(
                f"https://open.feishu.cn/open-apis/docx/v1/documents/{doc_id}/blocks/{page_id}/children",
                headers=headers,
                json={"children": batch, "index": -1},
            )
            if r.is_success:
                print(f"  Batch {batch_start}-{batch_start+len(batch)} OK")
            else:
                errors += 1
                print(f"  Batch {batch_start}-{batch_start+len(batch)} ERROR: {r.status_code} {r.text[:300]}")

        if errors:
            print(f"\n{errors} batch(es) failed. Check doc.")
        else:
            print(f"\nDone!  {doc_url}")


if __name__ == "__main__":
    asyncio.run(main())
