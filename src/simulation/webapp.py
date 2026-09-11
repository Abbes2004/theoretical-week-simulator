"""Minimal Flask web UI for the theoretical-week simulator.

docs/context/project_context.md section 10 ("User Interface") asks for a
simple interface letting a user select/enter a POI, consult component
availability, see the calculated theoretical week, identify the blocking
component, and detect missing/invalid information. This module implements
exactly that, nothing more (MASTER_PROMPT.md: "Do not create unnecessary UI
complexity").

Dataset selection: every route accepts ?dataset=real|demo (default: real,
or whatever `create_app(default_dataset=...)` was started with). 'demo' is
the SYNTHETIC pre-Phase-2 demonstration dataset (see
docs/decisions/0003-synthetic-demo-dataset.md); the UI always renders an
explicit warning banner while viewing it, and the dataset choice is
preserved across every link on the page so it is never possible to
silently drift from real to synthetic data.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
from flask import Flask, render_template_string, request

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from configs import settings  # noqa: E402
from src.simulation.simulator import lookup_poi, validate_against_historical  # noqa: E402

_BASE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Theoretical Week Simulator (Phase 1)</title>
  <style>
    body { font-family: system-ui, sans-serif; max-width: 900px; margin: 2rem auto; padding: 0 1rem; color: #1a1a1a; }
    h1 { font-size: 1.4rem; }
    form { margin: 1rem 0; display: flex; gap: 0.5rem; }
    input[type=text] { padding: 0.4rem; font-size: 1rem; }
    button { padding: 0.4rem 0.8rem; }
    table { border-collapse: collapse; width: 100%; margin-top: 1rem; }
    th, td { border: 1px solid #ccc; padding: 0.35rem 0.5rem; text-align: left; font-size: 0.9rem; }
    .status-CALCULATED { color: #0a7d2c; font-weight: bold; }
    .status-INCOMPLETE_DATA { color: #b8860b; font-weight: bold; }
    .status-INVALID_DATA { color: #b00020; font-weight: bold; }
    .status-NOT_APPLICABLE { color: #666; font-weight: bold; }
    .flag { display: inline-block; background: #eee; border-radius: 4px; padding: 0.1rem 0.4rem; margin: 0.1rem; font-size: 0.8rem; }
    .origin-SYNTHETIC { background: #ffe9a8; padding: 0.1rem 0.4rem; border-radius: 4px; }
    .origin-REAL { background: #d7f0d7; padding: 0.1rem 0.4rem; border-radius: 4px; }
    nav a { margin-right: 1rem; }
    .note { color: #555; font-size: 0.85rem; }
    .demo-banner {
      background: #b00020; color: #fff; font-weight: bold; text-align: center;
      padding: 0.6rem; border-radius: 4px; margin-bottom: 1rem; letter-spacing: 0.02em;
    }
    .dataset-switch { float: right; font-size: 0.85rem; font-weight: normal; }
  </style>
</head>
<body>
  {{ banner|safe }}
  <h1>Theoretical Week Simulator &mdash; Phase 1 (local)
    <span class="dataset-switch">{{ switch_link|safe }}</span>
  </h1>
  <nav><a href="/?dataset={{ dataset }}">Lookup</a><a href="/browse?dataset={{ dataset }}">Browse dataset</a></nav>
  {{ body|safe }}
</body>
</html>
"""

_DEMO_BANNER = (
    "<div class='demo-banner'>SYNTHETIC DEMO DATA -- generated for demonstration only, "
    "NOT real company data (see data/synthetic/demo_2025_2026/metadata/README.md)</div>"
)


def _dataset_path(dataset: str) -> Path:
    return settings.DATA_CANONICAL / "poi_canonical.parquet" if dataset == "real" else settings.DEMO_CANONICAL_PARQUET


def _load_canonical(dataset: str) -> pd.DataFrame | None:
    path = _dataset_path(dataset)
    if not path.exists():
        return None
    return pd.read_parquet(path)


def _join_list_cell(value) -> str:
    """Render a list-typed canonical column cell as text.

    A parquet round-trip returns list columns as numpy arrays rather than
    Python lists, so this must not assume `isinstance(value, list)`.
    """
    if value is None:
        return ""
    try:
        return ", ".join(str(v) for v in value)
    except TypeError:
        return str(value)


def _resolve_dataset(default_dataset: str) -> str:
    requested = request.args.get("dataset", default_dataset)
    return requested if requested in ("real", "demo") else default_dataset


def _render(body: str, dataset: str) -> str:
    other = "demo" if dataset == "real" else "real"
    other_label = "SYNTHETIC DEMO" if other == "demo" else "REAL"
    switch_link = f"<a href='{request.path}?dataset={other}'>Switch to {other_label} dataset</a>"
    banner = _DEMO_BANNER if dataset == "demo" else ""
    return render_template_string(_BASE, body=body, dataset=dataset, banner=banner, switch_link=switch_link)


def _not_found_body(dataset: str) -> str:
    hint = "python scripts/run_pipeline.py" if dataset == "real" else "python scripts/generate_demo_dataset.py"
    return f"<p class='note'>No {dataset.upper()} canonical dataset found. Run <code>{hint}</code> first.</p>"


def create_app(default_dataset: str = "real") -> Flask:
    app = Flask(__name__)

    @app.route("/", methods=["GET"])
    def index():
        dataset = _resolve_dataset(default_dataset)
        canonical = _load_canonical(dataset)
        id_sim = request.args.get("id_sim", "").strip()
        poi_sim = request.args.get("poi_sim", "").strip()

        body = """
        <form method="get" action="/">
          <input type="hidden" name="dataset" value="{{ dataset }}">
          <input type="text" name="id_sim" placeholder="Id_Sim" value="{{ id_sim }}">
          <input type="text" name="poi_sim" placeholder="POI_Sim" value="{{ poi_sim }}">
          <button type="submit">Look up</button>
        </form>
        """
        if canonical is None:
            body += _not_found_body(dataset)
            return _render(render_template_string(body, id_sim=id_sim, poi_sim=poi_sim, dataset=dataset), dataset)

        result_html = ""
        if id_sim and poi_sim:
            result = lookup_poi(canonical, id_sim, poi_sim)
            if result is None:
                result_html = f"<p>No POI found for Id_Sim={id_sim}, POI_Sim={poi_sim}.</p>"
            else:
                comp_rows = "".join(
                    f"<tr><td>{c}</td><td>{v if v is not None else '(missing)'}</td></tr>"
                    for c, v in result.component_dates.items()
                )
                flags = "".join(f"<span class='flag'>{f}</span>" for f in result.data_quality_flag) or "(none)"
                calc_html = ""
                if result.calculation_status == "CALCULATED":
                    calc_html = f"""
                    <p><b>DateTheorique:</b> {result.date_theorique}</p>
                    <p><b>SemTheorique:</b> {result.sem_theorique} ({result.sem_theorique_label})</p>
                    <p><b>BlockingElement:</b> {', '.join(result.blocking_element)}</p>
                    """
                else:
                    calc_html = f"""
                    <p><b>Missing components:</b> {', '.join(result.missing_components) or '(none)'}</p>
                    <p><b>Invalid components:</b> {', '.join(result.invalid_components) or '(none)'}</p>
                    """
                result_html = f"""
                <h2>Result <span class="origin-{result.data_origin}">{result.data_origin}</span></h2>
                <p><b>Status:</b> <span class="status-{result.calculation_status}">{result.calculation_status}</span></p>
                <table><tr><th>Component</th><th>Date</th></tr>{comp_rows}</table>
                {calc_html}
                <p><b>Quality flags:</b> {flags}</p>
                """
        summary = validate_against_historical(canonical)
        match_rate = "N/A" if summary.match_rate is None else f"{summary.match_rate:.1%}"
        body += f"""
        {result_html}
        <hr>
        <h3>Dataset overview</h3>
        <p>{len(canonical):,} POIs loaded from {_dataset_path(dataset).name}.
        Historical match rate: {match_rate} ({summary.comparable_pois} comparable POIs).</p>
        """
        return _render(render_template_string(body, id_sim=id_sim, poi_sim=poi_sim, dataset=dataset), dataset)

    @app.route("/browse")
    def browse():
        dataset = _resolve_dataset(default_dataset)
        canonical = _load_canonical(dataset)
        if canonical is None:
            return _render(_not_found_body(dataset), dataset)

        status_filter = request.args.get("status", "")
        page = max(int(request.args.get("page", 1)), 1)
        page_size = 50

        df = canonical
        if status_filter:
            df = df[df["calculation_status"] == status_filter]

        total = len(df)
        start = (page - 1) * page_size
        page_df = df.iloc[start:start + page_size]

        filter_links = "".join(
            f"<a href='/browse?dataset={dataset}&status={s}'>{s or 'ALL'}</a> "
            for s in ["", "CALCULATED", "INCOMPLETE_DATA", "INVALID_DATA", "NOT_APPLICABLE"]
        )

        rows = "".join(
            f"<tr><td>{r.id_sim}</td><td>{r.poi_sim}</td>"
            f"<td class='status-{r.calculation_status}'>{r.calculation_status}</td>"
            f"<td>{r.sem_theorique or ''}</td>"
            f"<td>{_join_list_cell(r.blocking_element)}</td>"
            f"<td><span class='origin-{r.data_origin}'>{r.data_origin}</span></td></tr>"
            for r in page_df.itertuples()
        )
        prev_link = (
            f"<a href='/browse?dataset={dataset}&status={status_filter}&page={page - 1}'>&laquo; prev</a>"
            if page > 1 else ""
        )
        next_link = (
            f"<a href='/browse?dataset={dataset}&status={status_filter}&page={page + 1}'>next &raquo;</a>"
            if start + page_size < total else ""
        )
        body = f"""
        <p>Filter: {filter_links}</p>
        <p>{total:,} POIs (showing {start + 1}-{min(start + page_size, total)})</p>
        <table>
          <tr><th>Id_Sim</th><th>POI_Sim</th><th>Status</th><th>SemTheorique</th><th>Blocking</th><th>Origin</th></tr>
          {rows}
        </table>
        <p>{prev_link} {next_link}</p>
        """
        return _render(body, dataset)

    return app


if __name__ == "__main__":
    create_app().run(debug=True)
