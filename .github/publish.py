#!/usr/bin/env python3
"""Publish convention docs to Confluence.

Reads confluence.yaml and publishes the page tree to the productive space:
section skeletons are always created; child pages only when status=active.

Required environment variables:
  CONFLUENCE_URL           https://your-instance.atlassian.net
  CONFLUENCE_USER          your@email.com
  CONFLUENCE_TOKEN         Atlassian API token (not your password)
  CONFLUENCE_SPACE         Confluence space key
  CONFLUENCE_ROOT_PAGE_ID  Root page ID for the publish
"""

import os
import sys
import yaml
import requests
import mistune
from requests.auth import HTTPBasicAuth

try:
    from md2cf.confluence_renderer import ConfluenceRenderer
except ImportError:
    print("ERROR: md2cf not installed. Run: pip install -r requirements.txt", file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------------------
# Frontmatter + Markdown → Confluence storage format
# ---------------------------------------------------------------------------

def parse_frontmatter(text: str) -> tuple[dict, str]:
    """Extract YAML frontmatter. Returns (meta, content_without_frontmatter)."""
    if text.startswith("---\n"):
        end = text.find("\n---\n", 4)
        if end != -1:
            meta = yaml.safe_load(text[4:end]) or {}
            return meta, text[end + 5:]
    return {}, text


def to_storage(markdown_text: str) -> str:
    renderer = ConfluenceRenderer(use_xhtml=True)
    md = mistune.Markdown(renderer=renderer)
    return md(markdown_text)


def write_with_frontmatter(path: str, meta: dict, content: str) -> None:
    """Rewrite `path` with `meta` as YAML frontmatter followed by `content`."""
    fm_text = yaml.safe_dump(meta, default_flow_style=False, sort_keys=False).rstrip()
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"---\n{fm_text}\n---\n{content}")


# ---------------------------------------------------------------------------
# Confluence REST API helpers
# ---------------------------------------------------------------------------

class ConfluenceClient:
    def __init__(self, host: str, user: str, token: str, space: str):
        self.base = f"{host}/wiki/rest/api"
        self.auth = HTTPBasicAuth(user, token)
        self.headers = {"Content-Type": "application/json", "Accept": "application/json"}
        self.space = space

    def _get(self, path, **params):
        resp = requests.get(f"{self.base}{path}", auth=self.auth, params=params)
        resp.raise_for_status()
        return resp.json()

    def _post(self, path, payload):
        resp = requests.post(f"{self.base}{path}", auth=self.auth, headers=self.headers, json=payload)
        resp.raise_for_status()
        return resp.json()

    def _put(self, path, payload=None):
        resp = requests.put(f"{self.base}{path}", auth=self.auth, headers=self.headers, json=payload)
        resp.raise_for_status()
        return resp.json() if resp.content else {}

    def find_child_page(self, title: str, parent_id: str) -> dict | None:
        """Find a direct child of parent_id by title.

        Scoped to the parent rather than the whole space: Confluence titles are
        space-unique, but a global title lookup would also match identically
        titled pages in other convention trees (e.g. another repo's "General"),
        causing the script to reuse — or, via update, re-parent — the wrong page.
        """
        start, limit = 0, 100
        while True:
            data = self._get(
                f"/content/{parent_id}/child/page",
                expand="version", start=start, limit=limit,
            )
            for page in data.get("results", []):
                if page["title"] == title:
                    return page
            if data.get("size", 0) < limit:
                break
            start += limit
        return None

    def get_page(self, page_id: str) -> dict | None:
        """Fetch a page by ID, or None if it no longer exists (404)."""
        try:
            return self._get(f"/content/{page_id}", expand="version,body.storage,ancestors")
        except requests.HTTPError as e:
            if e.response is not None and e.response.status_code == 404:
                return None
            raise

    def create_page(self, title: str, parent_id: str, body: str) -> dict:
        return self._post("/content", {
            "type": "page",
            "title": title,
            "space": {"key": self.space},
            "ancestors": [{"id": parent_id}],
            "body": {"storage": {"value": body, "representation": "storage"}},
        })

    def update_page(self, page_id: str, title: str, version: int, parent_id: str, body: str) -> dict:
        return self._put(f"/content/{page_id}", {
            "type": "page",
            "title": title,
            "version": {"number": version + 1},
            "ancestors": [{"id": parent_id}],
            "body": {"storage": {"value": body, "representation": "storage"}},
        })

    def upsert_page(self, page_id: str | None, title: str, parent_id: str, body: str) -> str:
        """Create or update a page. Returns the resolved page ID.

        Identity safeguard: when `page_id` is given (stored in confluence.yaml for
        sections or in a file's `confluence_page_id` frontmatter for child pages),
        update that exact page — no title guessing, so a rename or a title clash
        can never silently spawn a duplicate. Only when no ID is known do we fall
        back to a parent-scoped title lookup, then create.
        """
        existing = None
        if page_id:
            existing = self.get_page(str(page_id))
            if existing is None:
                print(f"    [warning]   page id {page_id} not found, creating new page for '{title}'", file=sys.stderr)
        else:
            found = self.find_child_page(title, parent_id)
            if found:
                existing = self.get_page(found["id"])

        if existing:
            current_title = existing["title"]
            current_body = existing["body"]["storage"]["value"]
            ancestors = existing.get("ancestors") or []
            current_parent = ancestors[-1]["id"] if ancestors else None
            if current_title == title and current_body == body and str(current_parent) == str(parent_id):
                print(f"    [unchanged] {title}")
            else:
                self.update_page(existing["id"], title, existing["version"]["number"], parent_id, body)
                print(f"    [updated]   {title}")
            return existing["id"]
        else:
            result = self.create_page(title, parent_id, body)
            print(f"    [created]   {title} (id={result['id']})")
            return result["id"]

    def move_page(self, page_id: str, position: str, target_id: str) -> None:
        requests.put(
            f"{self.base}/content/{page_id}/move/{position}/{target_id}",
            auth=self.auth,
        ).raise_for_status()

    def reorder(self, page_ids: list) -> None:
        for i in range(1, len(page_ids)):
            self.move_page(page_ids[i], "after", page_ids[i - 1])


# ---------------------------------------------------------------------------
# Publish logic
# ---------------------------------------------------------------------------

def publish_tree(client: ConfluenceClient, config: dict, root_page_id: str) -> list:
    """
    Publish the page tree under root_page_id.

    Section skeletons are always created; child pages only when status=active.
    """
    errors = []
    section_ids = []

    # Optional title suffix (config-level), appended in brackets to every page
    # title — e.g. suffix "Testing" turns "General" into "General (Testing)".
    # Keeps titles unique within a space shared by multiple convention trees.
    suffix = config.get("suffix")

    def titled(name: str) -> str:
        return f"{name} ({suffix})" if suffix else name

    for section in config["pages"]:
        section_title = titled(section["title"])
        section_id_hint = section.get("id")
        print(f"\n  {section_title}")

        section_body = (
            f"<p>Conventions for the <strong>{section['title']}</strong> domain. "
            f"See child pages for details.</p>"
        )
        try:
            section_id = client.upsert_page(section_id_hint, section_title, root_page_id, section_body)
            section_ids.append(section_id)
        except requests.HTTPError as e:
            print(f"    ERROR creating section '{section_title}': {e}", file=sys.stderr)
            errors.append(section_title)
            continue

        if not section_id_hint:
            print(f"    [note] add 'id: {section_id}' under section '{section['title']}' in "
                  f"confluence.yaml to lock its identity", file=sys.stderr)

        child_ids = []
        for child in section.get("children", []):
            file_path = child["file"]
            title = titled(child["title"])

            if not os.path.exists(file_path):
                print(f"    [skip]      {title} ({file_path} not found)")
                continue

            with open(file_path, encoding="utf-8") as f:
                raw = f.read()

            meta, content = parse_frontmatter(raw)
            status = meta.get("status", "draft")

            if status != "active":
                print(f"    [skip]      {title} (status: {status})")
                continue

            body = to_storage(content)
            page_id = meta.get("confluence_page_id")

            try:
                child_id = client.upsert_page(page_id, title, section_id, body)
                child_ids.append(child_id)
            except requests.HTTPError as e:
                print(f"    ERROR publishing '{title}': {e}", file=sys.stderr)
                errors.append(title)
                continue

            # Write the resolved ID back into the file's frontmatter so the next
            # run targets this exact page — the safeguard against duplicates.
            if str(page_id) != str(child_id):
                new_meta = {"confluence_page_id": int(child_id),
                            **{k: v for k, v in meta.items() if k != "confluence_page_id"}}
                write_with_frontmatter(file_path, new_meta, content)
                print(f"    [frontmatter] wrote confluence_page_id={child_id} to {file_path}")

        if len(child_ids) > 1:
            client.reorder(child_ids)

    if len(section_ids) > 1:
        client.reorder(section_ids)

    return errors


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    with open("confluence.yaml", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    host = os.environ["CONFLUENCE_URL"].strip().rstrip("/")
    if not host.startswith("http"):
        host = f"https://{host}"
    user = os.environ["CONFLUENCE_USER"]
    token = os.environ["CONFLUENCE_TOKEN"]
    space = os.environ["CONFLUENCE_SPACE"]
    root_page_id = os.environ["CONFLUENCE_ROOT_PAGE_ID"]

    client = ConfluenceClient(host, user, token, space)

    print("\n=== Publishing active pages to Confluence ===")
    errors = publish_tree(client, config, root_page_id)

    if errors:
        print(f"\nFinished with {len(errors)} error(s): {errors}", file=sys.stderr)
        sys.exit(1)
    else:
        print("\nAll pages published successfully.")


if __name__ == "__main__":
    main()
