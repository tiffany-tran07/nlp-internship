"""Streamlit search interface for ``scripts.main``.

Run with::

    streamlit run scripts/frontend/search.py

Set ``NLP_API_URL`` when the API is not available at localhost:8000.
"""

from __future__ import annotations

import json
import os
from typing import Any

import requests
import streamlit as st


DEFAULT_API_URL = "http://localhost:8000"
CONNECT_TIMEOUT_SECONDS = 3
READ_TIMEOUT_SECONDS = 30


class APIError(RuntimeError):
    """A user-displayable error returned by, or while calling, the API."""


def normalize_api_url(value: str) -> str:
    value = value.strip().rstrip("/")
    if not value.startswith(("http://", "https://")):
        raise ValueError("API URL must begin with http:// or https://")
    return value


@st.cache_resource
def api_session() -> requests.Session:
    session = requests.Session()
    session.headers.update({"Accept": "application/json"})
    return session


def error_detail(response: requests.Response) -> str:
    try:
        body = response.json()
    except ValueError:
        return response.text.strip() or f"HTTP {response.status_code}"

    detail = body.get("detail", body) if isinstance(body, dict) else body
    if isinstance(detail, list):
        messages = []
        for item in detail:
            if isinstance(item, dict):
                location = ".".join(str(part) for part in item.get("loc", []))
                message = item.get("msg", "Invalid value")
                messages.append(f"{location}: {message}" if location else str(message))
            else:
                messages.append(str(item))
        return "; ".join(messages)
    return str(detail)


def api_request(
    method: str,
    api_url: str,
    path: str,
    *,
    payload: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], requests.Response]:
    try:
        response = api_session().request(
            method,
            f"{api_url}{path}",
            json=payload,
            timeout=(CONNECT_TIMEOUT_SECONDS, READ_TIMEOUT_SECONDS),
        )
    except requests.Timeout as exc:
        raise APIError("The API timed out. Try again or reduce the result count.") from exc
    except requests.ConnectionError as exc:
        raise APIError(
            f"Could not connect to {api_url}. Confirm that the FastAPI server is running."
        ) from exc
    except requests.RequestException as exc:
        raise APIError(f"API request failed: {exc}") from exc

    if not response.ok:
        detail = error_detail(response)
        if response.status_code == 429:
            retry_after = response.headers.get("Retry-After", "1")
            detail = f"Rate limit reached. Retry in about {retry_after} second(s)."
        raise APIError(f"{detail} (HTTP {response.status_code})")

    try:
        body = response.json()
    except ValueError as exc:
        raise APIError("The API returned an invalid JSON response.") from exc
    if not isinstance(body, dict):
        raise APIError("The API returned an unexpected response shape.")
    return body, response


@st.cache_data(ttl=10, show_spinner=False)
def api_status(api_url: str) -> dict[str, Any]:
    body, _ = api_request("GET", api_url, "/ready")
    return body


def parse_document_upload(uploaded_file: Any) -> list[dict[str, Any]]:
    try:
        raw = uploaded_file.getvalue().decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("The document file must use UTF-8 encoding.") from exc

    try:
        if uploaded_file.name.lower().endswith(".jsonl"):
            documents = [json.loads(line) for line in raw.splitlines() if line.strip()]
        else:
            value = json.loads(raw)
            documents = value.get("documents") if isinstance(value, dict) else value
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON near line {exc.lineno}, column {exc.colno}.") from exc

    if not isinstance(documents, list):
        raise ValueError("Upload a JSON array or an object containing a 'documents' array.")

    normalized = []
    for index, document in enumerate(documents, start=1):
        if not isinstance(document, dict):
            raise ValueError(f"Document {index} must be a JSON object.")
        document_id = document.get("id")
        text = document.get("text")
        metadata = document.get("metadata", {})
        if not isinstance(document_id, str) or not document_id.strip():
            raise ValueError(f"Document {index} requires a non-empty string 'id'.")
        if not isinstance(text, str) or not text.strip():
            raise ValueError(f"Document {index} requires non-empty string 'text'.")
        if not isinstance(metadata, dict):
            raise ValueError(f"Document {index} 'metadata' must be an object.")
        normalized.append({"id": document_id.strip(), "text": text.strip(), "metadata": metadata})
    return normalized


def first_value(metadata: dict[str, Any], *keys: str) -> Any | None:
    for key in keys:
        value = metadata.get(key)
        if value not in (None, ""):
            return value
    return None


def format_price(value: Any) -> str | None:
    if value in (None, ""):
        return None
    try:
        return f"${float(value):,.0f}"
    except (TypeError, ValueError):
        return str(value)


def display_result(result: dict[str, Any], position: int) -> None:
    metadata = result.get("metadata")
    metadata = metadata if isinstance(metadata, dict) else {}
    listing_id = str(result.get("id", f"Result {position}"))
    address = first_value(metadata, "address", "L_Address")
    city = first_value(metadata, "city", "L_City")
    title_parts = [str(address)] if address else [f"Listing {listing_id}"]
    if city:
        title_parts.append(str(city))

    with st.container():
        st.subheader(" — ".join(title_parts))

        price = format_price(first_value(metadata, "price", "L_SystemPrice"))
        bedrooms = first_value(metadata, "bedrooms", "beds", "L_Keyword2")
        bathrooms = first_value(metadata, "bathrooms", "baths", "LM_Dec_3")
        score = result.get("score")

        columns = st.columns(4)
        columns[0].metric("Price", price or "—")
        columns[1].metric("Bedrooms", bedrooms if bedrooms is not None else "—")
        columns[2].metric("Bathrooms", bathrooms if bathrooms is not None else "—")
        try:
            score_label = f"{float(score):.3f}"
        except (TypeError, ValueError):
            score_label = "—"
        columns[3].metric("Relevance", score_label)

        text = result.get("text")
        if text:
            st.write(str(text))
        else:
            st.caption("No listing text was returned.")

        with st.expander("Listing metadata"):
            st.json({"id": listing_id, **metadata})
        st.divider()


st.set_page_config(
    page_title="Real Estate Intelligent Search",
    page_icon="🏠",
    layout="wide",
)

st.title("Real Estate Intelligent Search")
st.caption("Search listings using natural-language requirements.")

with st.sidebar:
    st.header("API connection")
    configured_url = os.getenv("NLP_API_URL", DEFAULT_API_URL)
    api_url_input = st.text_input("API URL", value=configured_url)
    try:
        api_url = normalize_api_url(api_url_input)
    except ValueError as exc:
        st.error(str(exc))
        st.stop()

    try:
        readiness = api_status(api_url)
    except APIError as exc:
        st.error(str(exc))
        readiness = None
    else:
        database = readiness.get("database", {})
        if readiness.get("status") == "degraded":
            st.warning("API connected, but database loading failed")
            if database.get("error"):
                st.caption(str(database["error"]))
        else:
            st.success("API connected")
        st.caption(f"{readiness.get('documents', 0):,} documents loaded")
        if database.get("loaded_at"):
            st.caption(f"Database refreshed: {database['loaded_at']}")

        if st.button("Reload from database", use_container_width=True):
            try:
                with st.spinner("Loading listings from MySQL…"):
                    result, _ = api_request("POST", api_url, "/documents/reload")
                api_status.clear()
                st.session_state.pop("search_response", None)
                st.success(f"Loaded {result.get('documents', 0):,} documents.")
                st.rerun()
            except APIError as exc:
                st.error(str(exc))

    st.divider()
    st.subheader("Load search documents")
    st.caption("Accepts `.json` or `.jsonl` documents with `id`, `text`, and optional `metadata`.")
    uploaded_file = st.file_uploader("Document file", type=("json", "jsonl"))
    if st.button("Replace API documents", disabled=uploaded_file is None, use_container_width=True):
        try:
            documents = parse_document_upload(uploaded_file)
            with st.spinner("Loading documents into the API…"):
                result, _ = api_request("PUT", api_url, "/documents", payload={"documents": documents})
            api_status.clear()
            st.session_state.pop("search_response", None)
            st.success(f"Loaded {result.get('documents', len(documents)):,} documents.")
        except (APIError, ValueError) as exc:
            st.error(str(exc))


with st.form("search_form"):
    query = st.text_input(
        "What are you looking for?",
        value="3 bed 2 bath under 700k in Irvine",
        max_chars=2_000,
        placeholder="For example: 3 bedrooms under $800k with a pool",
    )
    option_columns = st.columns(2)
    top_k = option_columns[0].slider("Maximum results", min_value=1, max_value=100, value=10)
    apply_filters = option_columns[1].checkbox(
        "Apply parsed filters",
        value=True,
        help="Use parsed price, bedroom, bathroom, and city requirements against document metadata.",
    )
    submitted = st.form_submit_button("Search", type="primary", use_container_width=True)


if submitted:
    if not query.strip():
        st.warning("Enter a search query.")
    elif readiness is None:
        st.error("The API is unavailable. Check the connection settings and try again.")
    else:
        try:
            with st.spinner("Searching listings…"):
                search_response, response = api_request(
                    "POST",
                    api_url,
                    "/search",
                    payload={
                        "query": query.strip(),
                        "top_k": top_k,
                        "apply_query_filters": apply_filters,
                    },
                )
            st.session_state["search_response"] = search_response
            st.session_state["search_cache"] = response.headers.get("X-Cache", "UNKNOWN")
        except APIError as exc:
            st.error(str(exc))


search_response = st.session_state.get("search_response")
if search_response:
    results = search_response.get("results", [])
    count = search_response.get("count", len(results))
    header_columns = st.columns((3, 1))
    header_columns[0].subheader(f"Found {count:,} listing{'s' if count != 1 else ''}")
    header_columns[1].caption(f"Cache: {st.session_state.get('search_cache', 'UNKNOWN')}")

    filters = search_response.get("parsed_filters", {})
    with st.expander("Parsed query filters", expanded=bool(filters)):
        if filters:
            st.json(filters)
        else:
            st.caption("No structured filters were identified.")

    if not results:
        st.info(
            "No matching listings were found. Try broader wording, disable parsed filters, "
            "or load documents from the sidebar."
        )
    else:
        for position, result in enumerate(results, start=1):
            if isinstance(result, dict):
                display_result(result, position)
            else:
                st.warning(f"Result {position} had an unexpected response shape.")
elif readiness and readiness.get("documents", 0) == 0:
    st.info("The API has no search documents loaded. Upload a JSON or JSONL file from the sidebar.")
