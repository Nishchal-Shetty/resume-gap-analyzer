import re
import pdfplumber
import requests
from bs4 import BeautifulSoup
from io import BytesIO


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract plain text from PDF bytes using pdfplumber.

    Args:
        file_bytes: Raw bytes of the PDF file.

    Returns:
        Cleaned plain text with pages joined by newlines.

    Raises:
        ValueError: If the PDF contains no extractable text.
        RuntimeError: If the PDF cannot be opened or parsed.
    """
    try:
        with pdfplumber.open(BytesIO(file_bytes)) as pdf:
            if not pdf.pages:
                raise ValueError("PDF has no pages.")
            pages = [page.extract_text() or "" for page in pdf.pages]
    except ValueError:
        raise
    except Exception as exc:
        raise RuntimeError(f"Failed to open or parse PDF: {exc}") from exc

    text = "\n".join(pages).strip()
    # Collapse runs of 3+ newlines down to two (preserve paragraph breaks)
    text = re.sub(r"\n{3,}", "\n\n", text)

    if not text:
        raise ValueError(
            "No text could be extracted from the PDF. "
            "The file may be scanned or image-only."
        )
    return text


def extract_text_from_url(url: str) -> str:
    """Fetch a web page and return its visible plain text.

    Removes script, style, nav, footer, and header tags before extraction
    so only human-readable content is returned.

    Args:
        url: Fully-qualified URL to fetch.

    Returns:
        Cleaned plain text of the page's visible content.

    Raises:
        ValueError: If the URL is not HTTP/HTTPS or the page returns no text.
        RuntimeError: If the request fails or the response cannot be parsed.
    """
    if not url.startswith(("http://", "https://")):
        raise ValueError(f"URL must start with http:// or https://: {url!r}")

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        )
    }

    try:
        response = requests.get(url, timeout=10, headers=headers)
        response.raise_for_status()
    except requests.exceptions.Timeout:
        raise RuntimeError(f"Request timed out fetching URL: {url}")
    except requests.exceptions.HTTPError as exc:
        raise RuntimeError(
            f"HTTP {exc.response.status_code} error fetching URL: {url}"
        ) from exc
    except requests.exceptions.RequestException as exc:
        raise RuntimeError(f"Failed to fetch URL {url!r}: {exc}") from exc

    try:
        soup = BeautifulSoup(response.text, "html.parser")
    except Exception as exc:
        raise RuntimeError(f"Failed to parse HTML from {url!r}: {exc}") from exc

    for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
        tag.decompose()

    text = soup.get_text(separator="\n", strip=True)
    # Collapse runs of 3+ newlines down to two
    text = re.sub(r"\n{3,}", "\n\n", text).strip()

    if not text:
        raise ValueError(f"No visible text found at URL: {url}")
    return text
