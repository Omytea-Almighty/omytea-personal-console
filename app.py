"""Omytea Personal Future Console — Streamlit MVP.

Master plan §9 World Console minimum viable instantiation.

Run:
    streamlit run app.py

Mock mode (no API key needed):
    OMYTEA_CONSOLE_MOCK=1 streamlit run app.py
"""

from __future__ import annotations

import json
import os
from typing import Any

import streamlit as st

import _brand
import currency
import pricing
import storage
from compiler import compile_belief_program, compile_branch_drilldown
from console import (
    ConsoleResult,
    _parse_time_horizon_to_steps,
    availability_status,
    belief_program_to_console,
    build_branch_comparison_rows,
    build_coherence_chart_data,
    build_continuous_distribution,
    build_decision_timeline_mermaid,
    compute_calibration_delta,
    format_delta_p,
    normalize_evidence_list,
    storyform_narrative,
)
from scenarios import AVAILABLE_SCENARIOS
from scenarios.career_decision import (
    INPUT_FIELDS as CAREER_DECISION_FIELDS,
    SCENARIO_NAME as CAREER_DECISION_NAME,
    validate_input,
)

st.set_page_config(
    page_title="Omytea Personal Future Console — MVP",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# Sidebar — system status + measurement-update entry
# ============================================================

def render_sidebar() -> str:
    """Sidebar shows system status + nav. Returns active mode."""
    st.sidebar.title(_brand.BRAND_NAME_SHORT)
    st.sidebar.caption(_brand.BRAND_TAGLINE)
    st.sidebar.divider()

    mode = st.sidebar.radio(
        "Mode",
        options=(
            "New prediction", "Video query", "Live webcam",
            "Measurement update", "Calibration history",
            "Pricing & pre-order",
        ),
        index=0,
    )

    st.sidebar.divider()
    st.sidebar.subheader("System status")
    status = availability_status()
    if status["mock_mode"]:
        st.sidebar.warning("⚠ MOCK MODE (OMYTEA_CONSOLE_MOCK=1)")
    if status["omytea_available"]:
        st.sidebar.success("✓ Omytea substrate available")
    else:
        st.sidebar.info("ℹ Omytea not importable — pure-dict mode")
        if status["omytea_import_error"]:
            st.sidebar.caption(f"Reason: {status['omytea_import_error']}")

    st.sidebar.divider()
    # v4.16 P7: locale / currency selector. Defaults to detected
    # locale (env var → DEFAULT_LOCALE = en_US for US market). User
    # may override for the session.
    detected = currency.detect_locale()
    if "user_locale" not in st.session_state:
        st.session_state.user_locale = detected
    locale_labels = {
        currency.LOCALE_US: "🇺🇸 US (USD)",
        currency.LOCALE_CN: "🇨🇳 中国 (CNY)",
        currency.LOCALE_EU: "🇪🇺 EU (EUR)",
        currency.LOCALE_GB: "🇬🇧 UK (GBP)",
        currency.LOCALE_JP: "🇯🇵 日本 (JPY)",
    }
    chosen = st.sidebar.selectbox(
        "Currency / Locale",
        options=list(currency.SUPPORTED_LOCALES),
        format_func=lambda k: locale_labels.get(k, k),
        index=list(currency.SUPPORTED_LOCALES).index(
            st.session_state.user_locale
        ),
        help=(
            "Default is USD (US market). Prices and pay-willingness "
            "anchors shown elsewhere in the app use this setting. "
            "Non-USD displays are flagged 'approx' since canonical "
            "billing currency is USD."
        ),
    )
    st.session_state.user_locale = chosen

    st.sidebar.divider()
    st.sidebar.caption(
        "Not a deterministic prediction system. Outputs are calibrated "
        "future scenarios with measurement-update feedback. Not medical / "
        "legal / financial advice."
    )
    st.sidebar.divider()
    st.sidebar.markdown(_brand.footer_markdown())

    return str(mode)


# ============================================================
# Mode 1 — New prediction
# ============================================================

def render_new_prediction() -> None:
    """Form input → compile → display branches + off-diagonal + evidence."""
    st.title("New prediction")
    st.write(
        "Enter a structured description of your decision below. "
        "The system compiles your input into a probabilistic hypothesis "
        "space and stores the snapshot so you can come back and report "
        "what actually happened."
    )

    scenario = st.selectbox(
        "Scenario",
        options=list(AVAILABLE_SCENARIOS.keys()),
        format_func=lambda k: f"{k} — {AVAILABLE_SCENARIOS[k]['description'][:80]}…",
    )

    st.markdown(f"**Description**: {AVAILABLE_SCENARIOS[scenario]['description']}")
    st.divider()

    # Render form fields
    form_data: dict[str, Any] = {}
    with st.form(key=f"form_{scenario}"):
        for field in AVAILABLE_SCENARIOS[scenario]["input_fields"]:
            if field.field_type == "textarea":
                form_data[field.key] = st.text_area(
                    field.label, help=field.hint, key=f"input_{field.key}",
                )
            elif field.field_type == "text":
                form_data[field.key] = st.text_input(
                    field.label, help=field.hint, key=f"input_{field.key}",
                )
            elif field.field_type == "select":
                form_data[field.key] = st.selectbox(
                    field.label, options=field.options,
                    help=field.hint, key=f"input_{field.key}",
                )
            else:
                form_data[field.key] = st.text_input(
                    field.label, help=field.hint, key=f"input_{field.key}",
                )

        # v4.16 P8: opt-in self-test flag so aggregate calibration view
        # can separate owner data from real-user data.
        form_data["is_owner_bias_flagged"] = st.checkbox(
            "I am the project owner / this is a self-test "
            "(track separately to remove ownership bias)",
            value=False,
            help=(
                "Check this if you are the project founder or running "
                "an internal self-test. Your data will still be stored "
                "and counted in calibration aggregates, but the "
                "'Calibration history' tab will let viewers see the "
                "distribution both with and without owner-tagged "
                "data points — honest meta-analysis."
            ),
        )

        submit = st.form_submit_button("Generate prediction")

    # v4.16 P2: persist the latest prediction in st.session_state so
    # post-submit interactions (drill-down clicks, view-mode toggles,
    # γ sliders) don't lose context across reruns.
    if submit:
        is_valid, err = validate_input(form_data)
        if not is_valid:
            st.error(err)
            return

        user_id = form_data.get("user_id", "").strip()
        if not user_id:
            st.error("Please provide a user handle.")
            return

        with st.spinner("Compiling input → BeliefProgram → hypothesis space…"):
            try:
                program = compile_belief_program(form_data, scenario=scenario)
                result = belief_program_to_console(program)
            except Exception as exc:  # noqa: BLE001 — show error to user
                st.error(f"Compilation failed: {exc}")
                return

        # Persist + freeze the snapshot in session_state for re-render.
        rec = storage.PredictionRecord(
            prediction_id=storage.new_prediction_id(),
            user_id=user_id,
            scenario=scenario,
            created_at=storage.now_unix(),
            user_input=form_data,
            belief_program=program.raw,
            wavefunction_snapshot={
                "hypotheses": [h.to_dict() for h in result.hypotheses],
            },
            joint_offdiag={
                "entries": [o.to_dict() for o in result.joint_offdiag],
            },
            is_owner_bias_flagged=bool(
                form_data.get("is_owner_bias_flagged", False)
            ),
        )
        storage.save_prediction(rec)
        st.session_state.current_prediction = {
            "prediction_id": rec.prediction_id,
            "result": result,
            "form_data": form_data,
            "scenario": scenario,
            "user_id": user_id,
            "program": program,
        }

    # Re-render the latest prediction (whether just submitted or
    # carried over from a previous run).
    current = st.session_state.get("current_prediction")
    if current is None:
        return
    _render_result(
        current["result"], current["form_data"], current["scenario"],
        current["user_id"], current["program"],
        prediction_id=current["prediction_id"],
    )


def _render_story_card(h: Any, kind_tag: str) -> None:
    """v4.16 P4 — narrative-first card. Narrative is the headline;
    probability + label + metadata sit in a smaller footer caption.
    Inverts the previous machine-table priority where label/probability
    led the visual hierarchy."""
    with st.container(border=True):
        st.markdown(
            f"### {kind_tag} {storyform_narrative(h.narrative, h.branch_type)}"
        )
        meta_parts = [
            f"**{h.probability * 100:.1f}%** probability",
            f"branch `{h.label}`",
        ]
        if h.depends_on_decision:
            meta_parts.append(f"requires decision `{h.depends_on_decision}`")
        if h.key_uncertainty_driver:
            meta_parts.append(f"hinges on _{h.key_uncertainty_driver}_")
        st.caption(" · ".join(meta_parts))


def _render_story_view(
    wishful: list[Any],
    realistic: list[Any],
    worst: list[Any],
    decision_options: list[str],
) -> None:
    """v4.16 P4 — story-view layout: wishful (hope) → realistic
    (likely) → worst (caution). Each branch rendered as a
    narrative-first card via _render_story_card."""
    if wishful:
        st.subheader("🌟 Best plausible case")
        st.caption(
            "The hoped-for future. Low probability but emotionally vivid. "
            "Use this as the anchor for thinking about what evidence / "
            "actions would shift its probability upward."
        )
        for h in wishful:
            _render_story_card(h, "🌟")

    if realistic:
        st.subheader("📊 Most-likely futures")
        st.caption(
            f"{len(realistic)} realistic branches across decision options: "
            f"{', '.join(decision_options)}"
        )
        for h in sorted(realistic, key=lambda x: -x.probability):
            _render_story_card(h, "📊")

    if worst:
        st.subheader("⚠️ Worst plausible case")
        st.caption(
            "The future to actively avoid. Low probability but specific. "
            "Use this to identify what preventive actions you should "
            "take regardless of which decision you pick."
        )
        for h in worst:
            _render_story_card(h, "⚠️")


def _render_comparison_table(result: ConsoleResult) -> None:
    """v4.16 P4 — side-by-side comparison view for users who want the
    classic table-shaped overview."""
    st.subheader("Branch comparison table")
    st.caption(
        "Same data as the story view, laid out for quick scanning. "
        "Useful when you need to compare two branches' "
        "probability / decision / key driver side-by-side."
    )
    rows = build_branch_comparison_rows(result)
    if not rows:
        st.info("No branches to compare.")
        return
    st.dataframe(rows, hide_index=True, use_container_width=True)


def _render_decision_timeline(
    result: ConsoleResult,
    user_input: dict[str, Any],
) -> None:
    """v4.16 P4 — Mermaid flowchart showing decision → branch leaves
    along the user's time horizon. Streamlit can render a fenced
    ```mermaid block on supported versions; older versions fall back
    to a code display."""
    st.subheader("Decision timeline")
    horizon = str(user_input.get("time_horizon", "decision horizon"))
    st.caption(
        f"How each decision option fans out into branches over {horizon}. "
        "🌟 = best-case anchor · 📊 = realistic · ⚠️ = worst-case anchor."
    )
    diagram = build_decision_timeline_mermaid(
        result, time_horizon_label=horizon,
    )
    # Streamlit 1.34+ renders ```mermaid code blocks natively in
    # st.markdown. On older versions the user still sees the syntax
    # rendered as a fenced code block — readable, just not graphical.
    st.markdown(f"```mermaid\n{diagram}\n```")


def _render_continuous_distribution(
    result: ConsoleResult,
    user_input: dict[str, Any],
) -> None:
    """v4.16 P3 — continuous density-over-time view of the discrete
    branch distribution. Each branch contributes a Gaussian kernel
    centered at a heuristic 'characteristic time' (wishful early,
    realistic mid, worst late); the chart sums them into a single
    density curve."""
    horizon_label = str(user_input.get("time_horizon", "6 months"))
    horizon_months = float(_parse_time_horizon_to_steps(horizon_label))
    chart = build_continuous_distribution(
        result, time_horizon_months=horizon_months,
    )
    if chart is None or chart.get("n_points", 0) < 2:
        st.info(
            "No branches to plot a continuous distribution for."
        )
        return

    st.subheader("Continuous probability density over time")
    st.caption(
        f"Each of {len(result.hypotheses)} branches contributes a "
        f"Gaussian kernel (σ ≈ {chart['sigma_months']:.1f} months) at "
        f"a heuristic characteristic time — wishful branches centered "
        f"around month {chart['horizon_months'] * 0.2:.1f}, realistic "
        f"around month {chart['horizon_months'] * 0.5:.1f}, worst "
        f"around month {chart['horizon_months'] * 0.7:.1f}. The "
        f"curve is the probability-weighted sum. Use this when the "
        f"discrete-branch table feels too engineering-shaped."
    )

    # Build chart data: a dict keyed by "Total density" + each branch
    # contribution. Streamlit's area_chart takes a dict of column
    # name → list of values and uses index for x-axis.
    chart_data: dict[str, list[float]] = {
        "Total density": chart["density"],
    }
    # Optional: include each branch's individual contribution to
    # the right of the legend so users can see where each kernel
    # peaks.
    for label, series in chart["per_branch_density"].items():
        chart_data[label] = series

    # Convert x-axis from index to "month N" labels via a pandas-free
    # workaround: just print the months alongside.
    st.area_chart(chart_data)
    st.caption(
        "x-axis = sample index 0…N along the time horizon; first "
        "sample is t=0 and last is t={:.0f} months.".format(
            chart["horizon_months"]
        )
    )

    # Per-branch characteristic-time summary table.
    summary_rows: list[dict[str, Any]] = []
    for label, mu in chart["characteristic_times"].items():
        hyp = next(
            (h for h in result.hypotheses if h.label == label), None,
        )
        if hyp is None:
            continue
        summary_rows.append({
            "Branch": label,
            "Type": hyp.branch_type,
            "Probability": f"{hyp.probability * 100:.1f}%",
            "Characteristic time": f"month {mu:.1f}",
        })
    if summary_rows:
        st.markdown("**Characteristic-time anchors**")
        st.dataframe(
            summary_rows, hide_index=True, use_container_width=True,
        )


def _render_drilldown_section(
    result: ConsoleResult,
    user_input: dict[str, Any],
    scenario: str,
    prediction_id: str,
) -> None:
    """v4.16 P2 — drill-down loop. Lets the user pick any branch and
    get an LLM-generated deep dive (3-paragraph narrative + concrete
    actions + conditional dependencies + sensitivity preview).

    Caches the LLM output in SQLite (branch_drilldowns table) keyed
    by (prediction_id, branch_label) so repeated clicks don't burn
    quota. Refresh button forces a re-call.
    """
    with st.expander("🔍 Drill down on one of these futures", expanded=False):
        st.caption(
            "Pick a branch you care about most — typically the wishful "
            "one if you want to plan toward it, or the worst-case if "
            "you want to plan around it — and the system will expand "
            "it into a 3-paragraph deeper narrative + concrete actions "
            "this week + dependencies that gate it + sensitivity preview."
        )

        # Sort hypotheses with the same reading order the story view uses.
        type_order = {"wishful": 0, "realistic": 1, "worst": 2}
        sorted_h = sorted(
            result.hypotheses,
            key=lambda h: (type_order.get(h.branch_type, 1), -h.probability),
        )
        labels = [h.label for h in sorted_h]
        label_to_hyp = {h.label: h for h in sorted_h}
        if not labels:
            st.info("No branches to drill into.")
            return

        chosen_label = st.selectbox(
            "Branch to drill into",
            options=labels,
            format_func=lambda lbl: (
                f"{_emoji_for_type(label_to_hyp[lbl].branch_type)} "
                f"{lbl} ({label_to_hyp[lbl].probability * 100:.0f}%)"
            ),
        )

        cached = storage.get_drilldown(prediction_id, chosen_label)
        cache_present = cached is not None

        col_a, col_b = st.columns([1, 1])
        with col_a:
            run = st.button(
                "Run drill-down" if not cache_present
                else "Show cached drill-down",
                use_container_width=True,
            )
        with col_b:
            refresh = st.button(
                "↻ Re-run (force refresh)",
                disabled=not cache_present,
                use_container_width=True,
                help=(
                    "Forces a fresh LLM call. Costs another API "
                    "request — only use if the cached output looks "
                    "wrong or outdated."
                ),
            )

        if refresh and cache_present:
            storage.delete_drilldown(prediction_id, chosen_label)
            cached = None
            cache_present = False

        chosen_hyp = label_to_hyp[chosen_label]

        if (run or refresh) and not cache_present:
            with st.spinner(
                f"Drilling into `{chosen_label}` via LLM…"
            ):
                try:
                    drilldown = compile_branch_drilldown(
                        branch_label=chosen_label,
                        branch_type=chosen_hyp.branch_type,
                        full_belief_program=_dump_program_for_drilldown(
                            chosen_hyp, result,
                        ),
                        user_input=user_input,
                        scenario=scenario,
                    )
                except Exception as exc:  # noqa: BLE001
                    st.error(f"Drill-down failed: {exc}")
                    return
            rec = storage.BranchDrilldown(
                drilldown_id=storage.new_drilldown_id(),
                prediction_id=prediction_id,
                branch_label=chosen_label,
                created_at=storage.now_unix(),
                drilldown_json=drilldown,
            )
            storage.save_drilldown(rec)
            cached = rec

        if cached is not None:
            _render_drilldown_body(cached, chosen_hyp)


def _emoji_for_type(branch_type: str) -> str:
    return {
        "wishful": "🌟",
        "worst": "⚠️",
        "realistic": "📊",
    }.get(branch_type, "•")


def _dump_program_for_drilldown(
    chosen_hyp: Any, result: ConsoleResult,
) -> dict[str, Any]:
    """Build a compact dict representation of the BeliefProgram for the
    drill-down LLM call — omits the wavefunction snapshots / Omytea
    runtime objects, only the user-facing data."""
    return {
        "scenario": result.scenario,
        "decision_options": list(result.decision_options),
        "chosen_branch": chosen_hyp.to_dict(),
        "all_branches": [h.to_dict() for h in result.hypotheses],
        "joint_offdiag": [o.to_dict() for o in result.joint_offdiag],
        "recommended_evidence": list(result.recommended_evidence),
    }


def _render_drilldown_body(
    cached: Any, chosen_hyp: Any,
) -> None:
    """Render the drill-down dict in a single nicely-organized block."""
    body = cached.drilldown_json
    st.markdown(
        f"### {_emoji_for_type(chosen_hyp.branch_type)} Drill-down: "
        f"`{cached.branch_label}` "
        f"({chosen_hyp.probability * 100:.1f}%)"
    )

    # Deeper narrative — 3 paragraphs.
    narrative = body.get("deeper_narrative") or []
    if narrative:
        st.subheader("Deeper narrative")
        for para in narrative:
            st.write(para)

    # Concrete actions this week.
    actions = body.get("concrete_actions_this_week") or []
    if actions:
        st.subheader("Concrete actions this week")
        for a in actions:
            with st.container(border=True):
                st.markdown(f"**{a.get('action', '')}**")
                effort = a.get("effort", "")
                if effort:
                    st.caption(f"Effort: {effort}")
                if a.get("expected_effect"):
                    st.caption(f"Expected effect: {a['expected_effect']}")

    # Conditional dependencies.
    deps = body.get("conditional_dependencies") or []
    if deps:
        st.subheader("Conditional dependencies")
        for d in deps:
            with st.container(border=True):
                st.markdown(f"**{d.get('condition', '')}**")
                cs = d.get("current_state", "")
                impact = d.get("impact_if_fails", "")
                if cs:
                    st.caption(f"Current state: {cs}")
                if impact:
                    st.caption(f"If this fails: {impact}")

    # Sensitivity preview.
    sens = body.get("sensitivity_preview") or []
    if sens:
        st.subheader("Sensitivity preview")
        st.caption(
            "What collecting each piece of evidence would do to this "
            "branch's probability specifically (in percentage points)."
        )
        for s in sens:
            with st.container(border=True):
                st.markdown(f"**{s.get('evidence_label', 'unknown')}**")
                up = s.get("if_positive_delta_p", 0)
                down = s.get("if_negative_delta_p", 0)
                cols = st.columns(2)
                with cols[0]:
                    st.metric(
                        "If signal supports",
                        f"+{int(round(float(up)))} pp",
                    )
                with cols[1]:
                    st.metric(
                        "If signal cuts against",
                        f"{int(round(float(down)))} pp",
                    )

    st.caption(
        f"Cached at {cached.created_at:.0f} (unix). Re-run with "
        f"the refresh button if context has changed materially."
    )


def _render_coherence_evolution(
    result: ConsoleResult,
    user_input: dict[str, Any],
) -> None:
    """Render the C1 'coherence over time' chart + summary table.

    Uses the user's `time_horizon` form field as the default evolution
    window and γ=0.05/month decoherence rate (the conservative default).
    Pure decay (no phase rotation) so the visual story is unambiguous:
    "this is how fast your correlations wash out into independent
    classical futures."
    """
    default_steps = _parse_time_horizon_to_steps(
        str(user_input.get("time_horizon", "6 months"))
    )

    chart = build_coherence_chart_data(
        result,
        time_horizon_months=default_steps,
        decoherence_rate_per_month=0.05,
        use_branch_energies=False,
    )
    if chart is None:
        return

    st.subheader("📉 Coherence decay over time")
    st.caption(
        "Off-diagonal magnitudes |ρ_ab| evolve under a Lindblad "
        "decoherence channel at γ=0.05/month (pure-decay; no phase "
        "rotation shown). When a pair's magnitude approaches zero, "
        "those two futures stop interfering and become independent — "
        "you've lost the window where they're 'coupled enough to "
        "reason about together.'"
    )

    # Line chart of all pairs over ticks. Streamlit's line_chart wants
    # a dict-of-lists (column → values) and infers x-axis from index.
    st.line_chart(chart["magnitude_series"])

    summary = chart["pairs_summary"]
    if summary:
        st.markdown(
            f"**Decay summary over {chart['n_steps']} months** "
            f"(γ={chart['decoherence_rate']:.2f}/month; analytic "
            f"reference ≈ {chart['expected_decay_ratio']:.2f}× of "
            f"initial)"
        )
        for row in summary:
            initial = row["initial"]
            final = row["final"]
            decay_pct = row["decay_pct"]
            with st.container(border=True):
                cols = st.columns([3, 1, 1, 1, 4])
                with cols[0]:
                    st.markdown(
                        f"`{row['pair_a']}` ↔ `{row['pair_b']}`"
                    )
                with cols[1]:
                    st.metric("|ρ| now", f"{initial:.2f}")
                with cols[2]:
                    st.metric(
                        f"|ρ| @ {chart['n_steps']}mo",
                        f"{final:.2f}",
                    )
                with cols[3]:
                    st.metric(
                        "Δ decay",
                        f"−{decay_pct:.0f}%",
                    )
                with cols[4]:
                    if row["rationale"]:
                        st.caption(row["rationale"])

    st.caption(
        "Interpretation: a strong, slowly-decaying coherence means "
        "you can still treat those two futures as 'linked' when "
        "planning. A coherence that has already collapsed by your "
        "decision horizon means the two are practically independent "
        "outcomes — preventive action against one no longer biases "
        "the other."
    )

    st.divider()


def _render_result(
    result: ConsoleResult,
    user_input: dict[str, Any],
    scenario: str,
    user_id: str,
    program: Any,
    prediction_id: str | None = None,
) -> None:
    """Render the prediction result + persist snapshot.

    v4.16 P2: prediction_id is supplied by the caller now (storage
    happens in render_new_prediction so the drill-down loop has a
    stable id to key the cache on). When prediction_id is None we
    fall back to inline-persistence (legacy path for tests that
    construct results directly)."""
    st.success("Prediction generated.")

    if prediction_id is None:
        rec = storage.PredictionRecord(
            prediction_id=storage.new_prediction_id(),
            user_id=user_id,
            scenario=scenario,
            created_at=storage.now_unix(),
            user_input=user_input,
            belief_program=program.raw,
            wavefunction_snapshot={
                "hypotheses": [h.to_dict() for h in result.hypotheses],
            },
            joint_offdiag={
                "entries": [o.to_dict() for o in result.joint_offdiag],
            },
            is_owner_bias_flagged=bool(
                user_input.get("is_owner_bias_flagged", False)
            ),
        )
        storage.save_prediction(rec)
        prediction_id = rec.prediction_id

    st.caption(
        f"Prediction ID (save this to come back later): `{prediction_id}`"
    )
    st.divider()

    # v4.16 P1+P4: partition by branch_type for visually distinct anchor
    # display + offer Story (default) vs Comparison-table view.
    wishful = [h for h in result.hypotheses if h.branch_type == "wishful"]
    worst = [h for h in result.hypotheses if h.branch_type == "worst"]
    realistic = [h for h in result.hypotheses
                 if h.branch_type not in ("wishful", "worst")]

    view_mode = st.radio(
        "View",
        options=(
            "Story (default)", "Comparison table",
            "Decision timeline", "Continuous distribution",
        ),
        horizontal=True,
        help=(
            "Story = each future as a paragraph. "
            "Comparison = side-by-side table. "
            "Timeline = decision-branch flowchart. "
            "Continuous = density over the time horizon (each branch "
            "gets a Gaussian kernel; smooth view of the discrete data)."
        ),
    )

    if view_mode == "Comparison table":
        _render_comparison_table(result)
    elif view_mode == "Decision timeline":
        _render_decision_timeline(result, user_input)
    elif view_mode == "Continuous distribution":
        _render_continuous_distribution(result, user_input)
    else:
        _render_story_view(wishful, realistic, worst, result.decision_options)

    # v4.16 P2: drill-down loop. Wrapped in an expander so it doesn't
    # dominate the page; once opened it persists across reruns via
    # session_state so the user can iterate without losing context.
    st.divider()
    _render_drilldown_section(result, user_input, scenario, prediction_id)

    st.divider()

    # Joint hypothesis off-diagonal
    if result.joint_offdiag:
        st.subheader("Joint hypothesis structure (off-diagonal coherence)")
        st.caption(
            "How different futures are correlated. Positive coherence = "
            "tend to co-occur. Negative = mutually exclusive."
        )
        for o in result.joint_offdiag:
            sign = "+" if o.coherence_strength > 0 else ""
            color = "green" if o.coherence_strength > 0 else "red"
            with st.container(border=True):
                cols = st.columns([2, 1, 2, 3])
                with cols[0]:
                    st.markdown(f"`{o.branch_a}`")
                with cols[1]:
                    st.markdown(f":{color}[{sign}{o.coherence_strength:.2f}]")
                with cols[2]:
                    st.markdown(f"`{o.branch_b}`")
                with cols[3]:
                    st.caption(o.rationale)

    st.divider()

    # ============================================================
    # C1 — Coherence evolution over time (Lindblad open-system decay)
    # ============================================================
    if result.used_omytea_substrate and result.joint_offdiag:
        _render_coherence_evolution(result, user_input)

    # v4.16 P5: recommended evidence in ΔP semantics (percentage-point shift)
    if result.recommended_evidence:
        st.subheader("Recommended evidence to collect")
        st.caption(
            "Each item shows the expected ±percentage-point shift in "
            "the most-likely branch's probability if you collect that "
            "evidence. Larger ΔP = more decision-relevant. (Values do "
            "not sum to 1 — each is an independent expected shift.)"
        )
        for e in normalize_evidence_list(result.recommended_evidence):
            with st.container(border=True):
                cols = st.columns([4, 1])
                with cols[0]:
                    st.markdown(f"**{e['evidence_label']}**")
                    if e.get("rationale"):
                        st.caption(e["rationale"])
                    if e.get("target_branch"):
                        st.caption(
                            f"Most affects: `{e['target_branch']}`"
                        )
                with cols[1]:
                    st.metric(
                        "Expected ΔP",
                        format_delta_p(e["expected_delta_p"]),
                    )

    st.divider()
    # Bug 2026-05-19 (first friend user hit this): the `rec` PredictionRecord
    # is only created inside the `if prediction_id is None:` branch above;
    # when the caller passes a non-None prediction_id (the v4.16 P2 path
    # that render_new_prediction takes), that local is unbound here. Use
    # the `prediction_id` parameter instead — it's guaranteed populated in
    # both branches (either passed in by caller, or reassigned to the
    # freshly-created record's id by the inline-persistence fallback
    # above). See tests/test_render_result_unbound_regression.py.
    st.info(
        f"📅 Come back in **{user_input.get('time_horizon', '6 months')}** to "
        f"report what actually happened. Use the **Measurement update** tab "
        f"with prediction ID `{prediction_id}`."
    )


# ============================================================
# Mode 2 — Measurement update
# ============================================================

def render_measurement_update() -> None:
    """User comes back, looks up prior prediction, reports actual outcome."""
    st.title("Measurement update")
    st.write(
        "Report what actually happened after a prior prediction. The system "
        "stores your observation, computes the calibration delta, and "
        "updates the cumulative calibration histogram."
    )

    user_id = st.text_input(
        "Your handle (same one you used when creating the prediction)",
    )
    if not user_id:
        return

    predictions = storage.list_user_predictions(user_id)
    if not predictions:
        st.warning(f"No predictions found for user `{user_id}`.")
        return

    pred_labels = [
        f"{i + 1}. [{p.scenario}] {p.prediction_id[:8]}… "
        f"({p.user_input.get('current_role', '<no role>')[:40]}…)"
        for i, p in enumerate(predictions)
    ]
    sel_idx = st.selectbox(
        "Select the prediction to update",
        options=range(len(predictions)),
        format_func=lambda i: pred_labels[i],
    )
    pred = predictions[sel_idx]

    st.divider()
    st.subheader("Original prediction branches")
    for h in pred.wavefunction_snapshot.get("hypotheses", []):
        st.markdown(f"- `{h['label']}` — {h['probability'] * 100:.1f}%: {h['narrative']}")

    st.divider()
    st.subheader("What actually happened?")
    st.caption(
        "For each branch, indicate how much it matched reality. 1.0 = "
        "fully materialized, 0.0 = didn't happen, intermediate values "
        "for partial matches. The values get auto-normalized."
    )

    actual_outcome: dict[str, float] = {}
    for h in pred.wavefunction_snapshot.get("hypotheses", []):
        v = st.slider(
            f"`{h['label']}`",
            min_value=0.0, max_value=1.0, value=0.0, step=0.1,
            help=h.get("narrative", ""),
        )
        actual_outcome[h["label"]] = v

    nps = st.slider(
        "How likely would you recommend this tool to a friend? (0-10 NPS)",
        min_value=0, max_value=10, value=5,
    )

    # v4.16 playbook-adopt: Sean Ellis disappointment test.
    # Anthropic founder's playbook §4 (MVP), canonical PMF indicator.
    # >40% "very disappointed" across active users = meaningful PMF.
    st.divider()
    st.markdown("**Sean Ellis disappointment test** (PMF indicator)")
    sean_ellis_label_map = {
        "very_disappointed": "Very disappointed",
        "somewhat_disappointed": "Somewhat disappointed",
        "not_disappointed": "Not disappointed",
    }
    sean_ellis_response = st.radio(
        "If you could no longer use this prediction tool, how would you feel?",
        options=list(sean_ellis_label_map.keys()),
        format_func=lambda k: sean_ellis_label_map[k],
        index=1,  # default to middle (somewhat) so we don't anchor anyone
        help=(
            "Standard PMF instrument. We tally the share of users who "
            "say 'very disappointed' — when that share crosses 40% "
            "across real (non-owner) users, that's a meaningful signal "
            "of product-market fit."
        ),
    )

    # v4.16 playbook-adopt: effort test (push → pull retention transition).
    st.markdown("**Effort test** (retention quality over the measurement window)")
    effort_label_map = {
        "self_returned": (
            "I came back to it on my own initiative "
            "(opened it without being reminded)"
        ),
        "needed_reminder": (
            "I came back only when reminded "
            "(the operator nudged me)"
        ),
        "did_not_return": "I did not return to the tool",
    }
    effort_test_response = st.radio(
        "Over the past 6 weeks, did you self-return to the tool?",
        options=list(effort_label_map.keys()),
        format_func=lambda k: effort_label_map[k],
        index=1,  # default to needed_reminder (the honest pre-PMF state)
        help=(
            "Pre-PMF retention requires founder energy pushing users; "
            "post-PMF, the product 'starts doing that work on its "
            "own' (per Anthropic founder's playbook §4)."
        ),
    )

    st.divider()
    notes = st.text_area("Notes (optional)")

    if st.button("Submit measurement update"):
        # Compute calibration delta
        from console import ConsoleHypothesis

        branches = [
            ConsoleHypothesis(
                label=h["label"],
                narrative=h.get("narrative", ""),
                probability=float(h["probability"]),
                key_uncertainty_driver=h.get("key_uncertainty_driver", ""),
                depends_on_decision=h.get("depends_on_decision"),
            )
            for h in pred.wavefunction_snapshot.get("hypotheses", [])
        ]
        cal = compute_calibration_delta(branches, actual_outcome)

        upd = storage.MeasurementUpdate(
            update_id=storage.new_update_id(),
            prediction_id=pred.prediction_id,
            user_id=user_id,
            observed_at=storage.now_unix(),
            actual_outcome=actual_outcome,
            calibration_delta=cal,
            user_satisfaction=nps,
            user_notes=notes,
            sean_ellis_response=sean_ellis_response,
            effort_test_response=effort_test_response,
        )
        storage.save_measurement(upd)

        st.success("Measurement saved.")
        st.json(cal)


# ============================================================
# Mode 3 — Calibration history
# ============================================================

def render_calibration_history() -> None:
    """Show aggregate calibration metrics with owner-bias breakdown."""
    st.title("Calibration history")
    st.write(
        "Aggregate calibration metrics across all measurement updates. "
        "Lower Brier / log-loss = better calibration."
    )

    user_id = st.text_input(
        "User handle (leave blank for global aggregate)", value="",
    )
    breakdown = storage.get_calibration_bias_breakdown(
        user_id=user_id if user_id else None,
    )

    aggregate = breakdown["all"]
    if not aggregate:
        st.info("No measurement updates recorded yet.")
        return

    cols = st.columns(3)
    with cols[0]:
        st.metric("Measurements", f"{int(aggregate.get('n_measurements', 0))}")
    with cols[1]:
        if "mean_brier" in aggregate:
            st.metric("Mean Brier", f"{aggregate['mean_brier']:.4f}")
    with cols[2]:
        if "mean_log_loss" in aggregate:
            st.metric("Mean log-loss", f"{aggregate['mean_log_loss']:.4f}")

    st.caption(
        "Brier score reference: 0 = perfect calibration; 1 = perfectly "
        "wrong (uniform-prior baseline ≈ 0.5 for 5-way categorical)."
    )

    st.divider()
    st.subheader("Owner-bias breakdown (v4.16 P8)")
    st.caption(
        "Some predictions are flagged as project-owner self-tests. The "
        "founder explicitly noted that owner data points may carry "
        "bias (NPS/utility scored higher than a neutral user would). "
        "This breakdown shows the same metrics computed with and "
        "without owner-flagged measurements."
    )

    excl = breakdown["exclude_owner"]
    own = breakdown["owner_only"]

    cmp_cols = st.columns(2)
    with cmp_cols[0]:
        st.markdown("**Real users only (owner excluded)**")
        if excl:
            st.metric("Measurements", f"{int(excl.get('n_measurements', 0))}")
            if "mean_brier" in excl:
                st.metric("Mean Brier", f"{excl['mean_brier']:.4f}")
            if "mean_log_loss" in excl:
                st.metric("Mean log-loss", f"{excl['mean_log_loss']:.4f}")
        else:
            st.info("No non-owner measurements yet.")
    with cmp_cols[1]:
        st.markdown("**Owner self-tests only**")
        if own:
            st.metric("Measurements", f"{int(own.get('n_measurements', 0))}")
            if "mean_brier" in own:
                st.metric("Mean Brier", f"{own['mean_brier']:.4f}")
            if "mean_log_loss" in own:
                st.metric("Mean log-loss", f"{own['mean_log_loss']:.4f}")
        else:
            st.info("No owner-flagged measurements yet.")

    # Highlight the delta when both sides have data.
    if excl and own and "mean_brier" in excl and "mean_brier" in own:
        delta = own["mean_brier"] - excl["mean_brier"]
        sign = "+" if delta >= 0 else ""
        st.caption(
            f"Δ (owner − non-owner) Brier = {sign}{delta:.4f}. "
            "Negative delta means owner self-test scored 'better calibrated' "
            "than the neutral sample — interpret as ownership bias."
        )


# ============================================================
# Main
# ============================================================

def render_pricing_and_preorder() -> None:
    """v4.16 P6 — pricing tier comparison + pre-order interest
    capture. Pre-revenue PMF research; no payment processor wired."""
    st.title("Pricing & pre-order interest")
    st.write(
        "We're not selling yet. This page exists so you can tell us "
        "what you'd pay for which tier — pre-order interest is "
        "captured for PMF research and helps prioritize the "
        "billing-integration work."
    )

    locale = st.session_state.get("user_locale", currency.DEFAULT_LOCALE)
    st.caption(f"Prices shown in: **{locale}** (canonical billing is USD)")

    # --- Tier comparison cards ---
    st.subheader("Tier comparison")
    cols = st.columns(len(pricing.PRICING_TIERS))
    for idx, tier in enumerate(pricing.PRICING_TIERS):
        with cols[idx]:
            with st.container(border=True):
                st.markdown(f"### {tier.display_name}")
                st.markdown(
                    f"**{pricing.format_tier_price(tier, locale=locale)}**"
                )
                st.caption(tier.one_line_pitch)
                if tier.bullet_features:
                    st.markdown("**Includes:**")
                    for feat in tier.bullet_features:
                        st.markdown(f"- {feat}")
                if tier.target_persona:
                    st.caption(f"*For:* {tier.target_persona}")
                if not tier.available_now:
                    st.warning("⏳ Not available for purchase yet")

    st.divider()

    # --- Pre-order interest capture ---
    st.subheader("Express pre-order interest")
    st.caption(
        "Tell us which tier interests you and how much you'd actually "
        "pay (USD). This is honest PMF research; we don't take payment "
        "or commit you to anything."
    )

    user_id = st.text_input(
        "Your handle (same one you used for predictions)",
        key="preorder_user_id",
    )
    tier_id = st.selectbox(
        "Which tier?",
        options=pricing.list_tier_ids(),
        format_func=lambda tid: pricing.get_tier(tid).display_name,
    )
    chosen_tier = pricing.get_tier(tier_id)

    # USD anchor selector + free-form override.
    anchor_choices = list(currency.PAY_WILLINGNESS_USD_ANCHORS) + [None]
    anchor = st.selectbox(
        "What would you pay (USD anchor)?",
        options=anchor_choices,
        format_func=lambda x: (
            "Custom (enter below)" if x is None
            else currency.format_price(x, locale=locale, approx=True)
        ),
    )
    custom_amount = 0.0
    if anchor is None:
        custom_amount = st.number_input(
            "Custom willing-to-pay (USD)",
            min_value=0.0, max_value=10000.0, value=0.0, step=1.0,
        )
    notes = st.text_area(
        "Notes (optional)",
        help=(
            "Why this number? What would make you pay more? What "
            "would make you walk away? Concrete the better."
        ),
    )

    if st.button("Submit pre-order interest", type="primary"):
        if not user_id.strip():
            st.error("Please provide your handle.")
            return
        willing = float(anchor) if anchor is not None else float(custom_amount)
        rec = storage.PreorderInterest(
            interest_id=storage.new_interest_id(),
            user_id=user_id.strip(),
            tier_id=tier_id,
            expressed_at=storage.now_unix(),
            willing_to_pay_usd=willing,
            locale=locale,
            notes=notes,
        )
        storage.save_preorder_interest(rec)
        st.success(
            f"Recorded: {currency.format_price(willing, locale)} "
            f"for {chosen_tier.display_name}. Thanks — this directly "
            f"feeds the v4.17 billing-integration prioritization."
        )

    st.divider()
    # --- Aggregate summary per tier ---
    st.subheader("Current pre-order signal")
    st.caption(
        "Aggregate willingness-to-pay across all submissions per tier. "
        "Helps the founder spot which tier has actual demand vs which "
        "is theoretical."
    )
    for tier in pricing.PRICING_TIERS:
        summary = storage.preorder_interest_summary(tier.tier_id)
        if not summary:
            st.markdown(
                f"**{tier.display_name}** — no pre-orders captured yet."
            )
            continue
        n = int(summary["n"])
        mean = summary["mean_usd"]
        median = summary["median_usd"]
        max_v = summary["max_usd"]
        st.markdown(
            f"**{tier.display_name}** — "
            f"{n} pre-order(s); mean "
            f"{currency.format_price(mean, locale)} · "
            f"median {currency.format_price(median, locale)} · "
            f"max {currency.format_price(max_v, locale)}."
        )


def render_video_query() -> None:
    """Mode 5 — Video Query: upload a video file, ask a question,
    get probabilistic predictions about the scene.

    Pipeline:
    1. User uploads mp4/mov/webm
    2. video_ingest samples N frames + runs perception (substrate's
       MotionFallbackDetector + IoUTracker)
    3. Sampled JPEG frames + tracked-entity summaries are sent to
       OllamaVisionBackend via compile_scene_query
    4. The resulting BeliefProgram is converted to the same
       ConsoleResult the New-prediction mode uses, so all
       existing visualization paths (story view / comparison
       table / decision timeline / continuous distribution /
       coherence decay / evidence ΔP) just work.

    Master plan §9 first-cut consumer surface for the video path.
    """
    st.title("🎥 Video query")
    st.write(
        "Upload a short video (mp4 / mov / webm). The system samples "
        "keyframes, runs local perception (substrate's tracked-entity "
        "detector), then asks a local vision-LLM to read the scene "
        "and emit calibrated future-scenario branches. No external "
        "API required — everything runs on your machine via Ollama."
    )

    # System status sub-block for video mode specifically
    with st.expander(
        "System status (local vision LLM check)", expanded=False,
    ):
        try:
            from llm_backends import OllamaVisionBackend
            vb = OllamaVisionBackend()
            if vb.is_available():
                st.success(
                    f"✓ Ollama vision backend ready · model: "
                    f"`{vb._get_model()}`"
                )
            else:
                st.warning(
                    f"⚠ Ollama vision backend not ready. "
                    f"Either start the Ollama daemon, or run: "
                    f"`ollama pull {vb._get_model()}`. "
                    f"If you want to test the flow without a vision "
                    f"model, set `OMYTEA_CONSOLE_MOCK=1` in your "
                    f"shell before running Streamlit."
                )
        except ImportError as exc:
            st.error(f"OllamaVisionBackend not importable: {exc}")

    uploaded = st.file_uploader(
        "Video file",
        type=["mp4", "mov", "webm", "avi", "mkv"],
        accept_multiple_files=False,
        help=(
            "Smaller files = faster processing. Recommended: <30 "
            "seconds, <50 MB. The first run may be slow as the "
            "vision model warms up."
        ),
    )

    user_query = st.text_area(
        "Your question about the scene",
        value="What might happen next? What are the most likely outcomes?",
        height=80,
        help=(
            "Ask anything about the future of the scene. Examples: "
            "'If the person on the left keeps walking, where will "
            "they be in 30 seconds?'  /  'What's the most likely "
            "next action?'  /  'What could go wrong here?'"
        ),
    )

    user_id = st.text_input(
        "Your handle (for measurement-update tracking)",
        help=(
            "Any string. Used to look up the prediction later via "
            "the Measurement update tab. No PII, no registration."
        ),
    )

    n_sample_frames = st.slider(
        "Number of sampled keyframes",
        min_value=2, max_value=12, value=3,
        help=(
            "More frames = better entity tracking but slower "
            "vision-LLM call. 3 is a fast default for CPU-only "
            "inference. Bump to 5-8 if your machine has a GPU."
        ),
    )

    submit = st.button("🚀 Analyze video", type="primary")

    if not submit:
        return

    if uploaded is None:
        st.error("Please upload a video file first.")
        return
    if not user_query.strip():
        st.error("Please enter a question about the scene.")
        return
    if not user_id.strip():
        st.error("Please provide a handle (any string).")
        return

    # Step 1: ingest video → sampled frames + tracked entities
    with st.spinner(
        "Step 1/3 — Sampling frames + running substrate perception…"
    ):
        from video_ingest import ingest_video_file

        file_bytes = uploaded.read()
        ingest_result = ingest_video_file(
            file_bytes=file_bytes,
            n_sample_frames=n_sample_frames,
        )

    if not ingest_result.available:
        st.error(
            f"Video ingestion failed: {ingest_result.reason}\n\n"
            f"If this says 'opencv-python or numpy not installed', "
            f"run: `pip install opencv-python-headless`. If it says "
            f"'mock mode enabled', unset `OMYTEA_CONSOLE_MOCK` in "
            f"your shell."
        )
        return

    st.success(
        f"✓ Sampled {ingest_result.sampled_count} frames · "
        f"{len(ingest_result.tracked_entities)} entities tracked · "
        f"detector: `{ingest_result.detector_used}` · "
        f"video duration: {ingest_result.duration_seconds:.1f}s @ "
        f"{ingest_result.fps:.0f}fps"
    )

    # Show a thumbnail strip of sampled frames so the user sees what
    # the model is looking at. Each frame gets detection bounding
    # box + trajectory polyline overlays for entities tracked on
    # or before that frame.
    if ingest_result.sampled_frames:
        st.markdown("**Sampled keyframes with detection overlays**")
        from visualization import render_frame_with_overlays
        entity_dicts_for_overlay = [
            {
                "object_id": e.object_id,
                "label": e.label,
                "trajectory": list(e.trajectory),
                "confidence": e.confidence,
            }
            for e in ingest_result.tracked_entities
        ]
        cols = st.columns(min(len(ingest_result.sampled_frames), 6))
        for i, sf in enumerate(ingest_result.sampled_frames):
            overlay_bytes = render_frame_with_overlays(
                image_bytes=sf.image_bytes,
                frame_idx=sf.frame_idx,
                tracked_entities=entity_dicts_for_overlay,
                frame_width=sf.width,
                frame_height=sf.height,
            )
            with cols[i % len(cols)]:
                st.image(
                    overlay_bytes,
                    caption=(
                        f"t={sf.timestamp_seconds:.1f}s "
                        f"(frame {sf.frame_idx})"
                    ),
                    use_container_width=True,
                )

    # Entity summary table
    if ingest_result.tracked_entities:
        st.markdown("**Tracked entities (top by track-length × confidence)**")
        entity_rows = []
        for e in ingest_result.tracked_entities:
            entity_rows.append({
                "Entity ID": e.object_id,
                "Label": e.label,
                "First frame": e.first_frame_idx,
                "Last frame": e.last_frame_idx,
                "Trajectory length": len(e.trajectory),
                "Confidence": f"{e.confidence:.2f}",
            })
        st.dataframe(
            entity_rows, hide_index=True, use_container_width=True,
        )

    # Step 2: scene-compile via vision LLM
    with st.spinner(
        f"Step 2/3 — Asking local vision LLM to read the scene ({n_sample_frames} frames)…"
    ):
        from compiler import compile_scene_query

        entity_summaries = [
            {
                "object_id": e.object_id,
                "label": e.label,
                "trajectory": list(e.trajectory),
                "confidence": e.confidence,
            }
            for e in ingest_result.tracked_entities
        ]
        try:
            program = compile_scene_query(
                user_query=user_query.strip(),
                sampled_frame_jpegs=[
                    sf.image_bytes for sf in ingest_result.sampled_frames
                ],
                tracked_entities_summary=entity_summaries,
            )
        except Exception as exc:  # noqa: BLE001
            st.error(f"Scene compilation failed: {exc}")
            return

    # Step 3: convert to ConsoleResult + persist + render via existing UI
    with st.spinner("Step 3/3 — Building belief state + applying quantum operator…"):
        from console import belief_program_to_console
        result = belief_program_to_console(program)

    # Surface fallback warning if the vision LLM timed out / failed.
    fallback_reason = program.raw.get("_fallback_reason", "")
    if fallback_reason:
        st.warning(
            f"⚠ Vision LLM fallback engaged. {fallback_reason}\n\n"
            f"The branches below come from a deterministic stub and "
            f"are NOT grounded in the specific video content. The "
            f"entity-tracking + quantum-operator evolution still "
            f"uses the real per-frame detections."
        )
    else:
        st.success("✓ Scene analysis complete.")

    st.divider()

    # Persist as a prediction (so it shows up in Measurement update later)
    rec = storage.PredictionRecord(
        prediction_id=storage.new_prediction_id(),
        user_id=user_id.strip(),
        scenario="video_scene_query",
        created_at=storage.now_unix(),
        user_input={
            "user_query": user_query.strip(),
            "n_sample_frames": n_sample_frames,
            "video_duration_seconds": ingest_result.duration_seconds,
            "n_entities": len(ingest_result.tracked_entities),
            "detector": ingest_result.detector_used,
            "is_owner_bias_flagged": False,
        },
        belief_program=program.raw,
        wavefunction_snapshot={
            "hypotheses": [h.to_dict() for h in result.hypotheses],
        },
        joint_offdiag={
            "entries": [o.to_dict() for o in result.joint_offdiag],
        },
        is_owner_bias_flagged=False,
    )
    storage.save_prediction(rec)
    st.caption(
        f"Prediction ID (save this for later measurement-update): "
        f"`{rec.prediction_id}`"
    )

    st.divider()
    # Render the per-entity quantum-state evolution alongside the
    # scene-level branches. This is the operator-algebra-level
    # quantum operator on a tracked-entity JointWaveFunction,
    # distinct from the scene-level branch coherence shown below.
    if ingest_result.tracked_entities:
        _render_entity_quantum_evolution(
            entity_summaries=entity_summaries,
            ingest_result=ingest_result,
        )
    st.divider()
    # Reuse the existing result-rendering machinery from
    # _render_result, including story view / comparison / timeline /
    # continuous-distribution / coherence-decay / evidence ΔP.
    user_input_proxy = {
        "time_horizon": "6 months",  # placeholder; the C1 UI uses this
        "user_query": user_query.strip(),
    }
    _render_result(
        result, user_input_proxy, "video_scene_query",
        rec.user_id, program,
        prediction_id=rec.prediction_id,
    )


def _render_entity_quantum_evolution(
    entity_summaries: list[dict[str, Any]],
    ingest_result: Any,
) -> None:
    """Build per-entity hypothesis bundles → JointWaveFunction → run
    LindbladOperator → visualize the off-diagonal coherence decay
    between entity-trajectory futures.

    This is the operator-algebra-level quantum operator applied to
    the actual tracked entities from the video, separate from the
    BeliefProgram branches the vision LLM emits.
    """
    import video_state

    st.subheader("⚛ Entity-trajectory quantum evolution")
    st.caption(
        "For each tracked entity, the system synthesizes three "
        "future-position hypotheses (continue / accelerate / "
        "decelerate). These are combined into a JointWaveFunction "
        "across up to 3 entities, then evolved under a Lindblad "
        "open-system operator over a short horizon. The decaying "
        "off-diagonal magnitudes below show how correlations "
        "between entity-trajectory futures wash out into "
        "independent classical outcomes."
    )

    bundles = video_state.build_entity_hypothesis_bundles(
        entity_summaries, max_entities=3,
    )

    if not bundles:
        st.info("No trackable entities to evolve.")
        return

    # Bundle preview table
    bundle_rows = []
    for b in bundles:
        bundle_rows.append({
            "Entity": f"{b.entity_id} ({b.label})",
            "Last x (norm)": f"{b.last_observed_cx:.2f}",
            "Last y (norm)": f"{b.last_observed_cy:.2f}",
            "Velocity x": f"{b.velocity_x:+.3f}",
            "Velocity y": f"{b.velocity_y:+.3f}",
            "Continue prior": f"{b.hypothesis_weights[0]:.0%}",
            "Accelerate prior": f"{b.hypothesis_weights[1]:.0%}",
            "Decelerate prior": f"{b.hypothesis_weights[2]:.0%}",
        })
    st.dataframe(
        bundle_rows, hide_index=True, use_container_width=True,
    )

    jwf = video_state.build_joint_wavefunction(bundles)
    if jwf is None:
        st.warning(
            "Substrate unavailable — cannot run quantum evolution. "
            "Install the parent WMDB package or set "
            "`OMYTEA_CONSOLE_MOCK=1` and try again with mock data."
        )
        return

    n_joint = len(jwf.hypotheses)
    n_offdiag_pairs = len(jwf.off_diagonal_couplings) // 2

    cols = st.columns(3)
    with cols[0]:
        st.metric("Joint hypotheses", n_joint)
    with cols[1]:
        st.metric("Off-diagonal pairs", n_offdiag_pairs)
    with cols[2]:
        st.metric("Entities evolved", len(bundles))

    if n_offdiag_pairs == 0:
        st.info(
            "No off-diagonal coherences generated (need ≥2 entities "
            "with informative trajectories). Skipping evolution."
        )
        return

    horizon_steps = st.slider(
        "Evolution horizon (Lindblad ticks)",
        min_value=2, max_value=12, value=6,
        help=(
            "Each tick = one unit of decoherence time. More ticks "
            "show fuller decay; fewer ticks = faster compute."
        ),
    )
    decoherence_rate = st.slider(
        "Decoherence rate γ (per tick)",
        min_value=0.02, max_value=0.30, value=0.08, step=0.02,
        help=(
            "Higher γ = faster coherence collapse. Lower γ = "
            "futures stay correlated longer."
        ),
    )

    evo = video_state.evolve_entity_joint(
        jwf,
        time_horizon_steps=horizon_steps,
        decoherence_rate=decoherence_rate,
    )

    if evo.get("skipped"):
        st.error(
            f"Evolution skipped: {evo.get('reason', 'unknown')}"
        )
        return

    # Per-pair magnitude over time → line chart
    snapshots = evo["snapshots"]
    if not snapshots:
        st.info("No evolution snapshots to display.")
        return

    # Build series: one line per off-diagonal pair (deduped by sorted i,j)
    seen_pairs: set[tuple[int, int]] = set()
    pair_series: dict[str, list[float]] = {}
    for snap in snapshots:
        for entry in snap["entries"]:
            i, j = entry["row"], entry["col"]
            key = (min(i, j), max(i, j))
            if key not in seen_pairs:
                # Find or initialize this pair's series across all
                # snapshots seen so far + this one
                seen_pairs.add(key)
                pair_series[f"(j{key[0]}, j{key[1]})"] = []

    # Now fill series consistently across all snapshots
    for snap in snapshots:
        pair_mags: dict[tuple[int, int], float] = {}
        for entry in snap["entries"]:
            i, j = entry["row"], entry["col"]
            key = (min(i, j), max(i, j))
            pair_mags[key] = max(
                pair_mags.get(key, 0.0), entry["magnitude"]
            )
        for key in seen_pairs:
            label = f"(j{key[0]}, j{key[1]})"
            pair_series[label].append(pair_mags.get(key, 0.0))

    st.line_chart(pair_series)
    st.caption(
        f"Off-diagonal magnitude |⟨joint_i | ρ | joint_j⟩| over "
        f"{horizon_steps} Lindblad ticks at γ={decoherence_rate:.2f}. "
        f"Each line = one joint-hypothesis pair. Lines converging to "
        f"zero = those two correlated futures have lost their "
        f"coherence and are now effectively independent classical "
        f"outcomes."
    )


# ============================================================
# Mode 6 — Live webcam (Tier 2)
# ============================================================


def render_live_webcam() -> None:
    """Mode 6 — Live webcam streaming with continuous quantum-state
    evolution.

    Pipeline:
    1. streamlit-webrtc opens a local WebRTC peer in the browser →
       camera frames stream into a callback running on a background
       thread (managed by aiortc).
    2. Each frame goes through ``WebcamSession.on_frame`` →
       substrate detector → IoUTracker → rolling trajectory dict.
    3. Every ``rebuild_every_n_frames`` frames, the joint
       wavefunction is rebuilt and evolved under the Lindblad
       operator. The snapshot of the joint state is cached in the
       session so the Streamlit main thread can read it without
       racing.
    4. A "Capture for prediction" button freezes the latest snapshot
       and asks the vision LLM about the current scene, returning
       a full ConsoleResult — same rendering as Mode 5 from there.

    Master plan §9 World Console direction — direct live perception
    rather than file upload. §2.9 negative scope — no biometric ID,
    no demographic features, no multi-camera fusion (single stream
    only).
    """
    st.title("📷 Live webcam")
    st.write(
        "Stream from your local camera. Frames are processed entirely "
        "on your machine — no upload, no cloud. The quantum operator "
        "rebuilds every few frames as new entity trajectories accumulate."
    )

    # Probe streamlit-webrtc availability up front
    import webcam_stream
    webrtc_mod, webrtc_err = webcam_stream._try_streamlit_webrtc()

    with st.expander("System status (live webcam)", expanded=False):
        if webrtc_mod is None:
            st.error(
                f"⚠ {webrtc_err}\n\n"
                "Live webcam mode needs streamlit-webrtc + its aiortc "
                "transitive deps (av, cffi, cryptography). To enable: "
                "`pip install 'streamlit-webrtc>=0.47,<1.0' 'av>=10.0'`"
            )
        else:
            st.success("✓ streamlit-webrtc available")
        sub_types, sub_err = webcam_stream._try_import_substrate()
        if sub_types is not None:
            st.success("✓ Omytea substrate (perception + quantum) available")
        else:
            st.warning(
                f"⚠ Omytea substrate not available: {sub_err}. "
                "Live mode will count frames but skip the quantum stage. "
                "Install the parent omytea package or unset "
                "OMYTEA_CONSOLE_MOCK to enable substrate."
            )

    if webrtc_mod is None:
        st.info(
            "Install the Tier 2 webcam extra and reload to enable this "
            "mode. Until then, Mode 5 \"Video query\" handles uploaded "
            "video files with the same pipeline."
        )
        return

    # Session-state object — persists across reruns and is the same
    # Python object the webrtc frame callback writes to.
    if "webcam_session" not in st.session_state:
        st.session_state.webcam_session = webcam_stream.WebcamSession()
    session: webcam_stream.WebcamSession = st.session_state.webcam_session

    # Tunable settings
    with st.expander("Tuning (advanced)", expanded=False):
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            new_rebuild = st.slider(
                "Rebuild every N frames",
                min_value=2, max_value=30,
                value=session.rebuild_every_n_frames,
                help=(
                    "How often the joint wavefunction is rebuilt + "
                    "evolved. Smaller = more reactive, more CPU."
                ),
            )
            session.rebuild_every_n_frames = new_rebuild
        with col_b:
            new_max_traj = st.slider(
                "Rolling-window size",
                min_value=10, max_value=120,
                value=session.max_trajectory_len,
                help="Max trajectory points kept per entity.",
            )
            session.max_trajectory_len = new_max_traj
        with col_c:
            new_decoh = st.slider(
                "Decoherence rate γ",
                min_value=0.02, max_value=0.30,
                value=session.decoherence_rate, step=0.02,
            )
            session.decoherence_rate = new_decoh

    # WebRTC streamer
    from streamlit_webrtc import RTCConfiguration, WebRtcMode, webrtc_streamer

    rtc_config = RTCConfiguration({
        "iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}],
    })

    def video_frame_callback(frame: Any) -> Any:
        """Background-thread callback. Converts av.VideoFrame → BGR
        ndarray and pushes into the WebcamSession. Returns the frame
        unchanged so the user still sees their video preview."""
        try:
            import numpy as np  # noqa: F401  # required by av's to_ndarray
            img = frame.to_ndarray(format="bgr24")
            h, w = img.shape[:2]
            session.on_frame(
                image_data=img, frame_width=w, frame_height=h,
                stream_id="streamlit_webrtc",
            )
        except Exception:
            # Honest-fail: never crash the WebRTC track loop —
            # the user would lose the video preview.
            pass
        return frame

    ctx = webrtc_streamer(
        key="omytea-live-webcam",
        mode=WebRtcMode.SENDRECV,
        rtc_configuration=rtc_config,
        video_frame_callback=video_frame_callback,
        media_stream_constraints={"video": True, "audio": False},
        async_processing=True,
    )

    # Live state panel (re-reads the snapshot every rerun)
    st.subheader("Live state")
    refresh_col, reset_col = st.columns([1, 1])
    with refresh_col:
        if st.button("🔄 Refresh state", use_container_width=True):
            st.rerun()
    with reset_col:
        if st.button("🧹 Reset session", use_container_width=True):
            session.reset()
            st.rerun()

    snap = session.snapshot()

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Frames processed", snap.frames_processed)
    m2.metric("Observed FPS", f"{snap.fps_observed:.1f}")
    m3.metric("Live entities", snap.n_entities)
    m4.metric("Joint hypotheses", snap.n_joint_hypotheses)

    if snap.entities_summary:
        st.markdown("**Tracked entities**")
        rows = [
            {
                "Entity": f"{e['object_id']} ({e['label']})",
                "Points": e["n_points"],
                "Last x": f"{e['last_cx']:.2f}",
                "Last y": f"{e['last_cy']:.2f}",
                "Vx": f"{e['velocity_x']:+.3f}",
                "Vy": f"{e['velocity_y']:+.3f}",
                "Confidence": f"{e['confidence']:.2f}",
            }
            for e in snap.entities_summary
        ]
        st.dataframe(rows, hide_index=True, use_container_width=True)
    else:
        st.caption(
            "No entities tracked yet. Start the webcam above and move "
            "something within the frame."
        )

    # Coherence-decay chart (last rebuild's snapshots)
    if snap.coherence_snapshots:
        # Build per-pair series like Mode 5 does, but from the live snapshot
        seen_pairs: set[tuple[int, int]] = set()
        pair_series: dict[str, list[float]] = {}
        for s_ in snap.coherence_snapshots:
            for entry in s_.get("entries", []):
                key = (min(entry["row"], entry["col"]),
                       max(entry["row"], entry["col"]))
                if key not in seen_pairs:
                    seen_pairs.add(key)
                    pair_series[f"(j{key[0]}, j{key[1]})"] = []
        for s_ in snap.coherence_snapshots:
            pair_mags: dict[tuple[int, int], float] = {}
            for entry in s_.get("entries", []):
                key = (min(entry["row"], entry["col"]),
                       max(entry["row"], entry["col"]))
                pair_mags[key] = max(
                    pair_mags.get(key, 0.0), entry["magnitude"]
                )
            for key in seen_pairs:
                lbl = f"(j{key[0]}, j{key[1]})"
                pair_series[lbl].append(pair_mags.get(key, 0.0))

        if pair_series:
            st.markdown("**Off-diagonal coherence decay (last rebuild)**")
            st.line_chart(pair_series)
            st.caption(
                f"Rebuilt at frame {snap.last_rebuild_at_frame}. "
                f"Each line = one joint-hypothesis pair magnitude over "
                f"Lindblad ticks. Lines decaying to 0 = correlated "
                f"futures losing coherence."
            )
    else:
        st.caption(
            "No joint quantum state yet. Coherence chart will appear "
            "after the first rebuild (every "
            f"{session.rebuild_every_n_frames} frames by default)."
        )

    # ----------------------------------------------------------------
    # Tier 3 — Capture & predict: freeze current state, ask vision LLM
    # ----------------------------------------------------------------

    st.divider()
    st.subheader("🎯 Ask vision LLM about the current scene")
    st.write(
        "Freeze the last few webcam frames + current entity tracks "
        "and run them through the same scene-understanding pipeline "
        "Mode 5 uses. Returns calibrated future branches you can "
        "score later in the Measurement update tab."
    )

    cap_query = st.text_area(
        "Your question about the current scene",
        value="What is most likely about to happen?",
        height=70,
        key="webcam_capture_query",
        help=(
            "Ask anything probabilistic about what's happening or "
            "about to happen. 'What's most likely?' works; "
            "'exactly when will X happen?' does not."
        ),
    )
    cap_user_id = st.text_input(
        "Your handle (for measurement-update tracking)",
        key="webcam_capture_user_id",
        help=(
            "Any string. Used to look up the prediction later via "
            "the Measurement update tab."
        ),
    )
    cap_n_frames = st.slider(
        "How many recent frames to include",
        min_value=1, max_value=session.frame_buffer_size, value=min(3, session.frame_buffer_size),
        help=(
            "More frames = more visual context for the vision LLM "
            "(better tracking) but slower inference. 2-3 is usually "
            "enough."
        ),
    )

    if st.button("📸 Capture & predict", type="primary", use_container_width=True):
        capture = session.snapshot_for_prediction(n_frames=cap_n_frames)
        if not capture["available"]:
            st.warning(
                f"Cannot capture yet: {capture['reason']}"
            )
        elif not cap_query.strip():
            st.error("Please type a question first.")
        elif not cap_user_id.strip():
            st.error("Please enter a handle (any string is fine).")
        else:
            with st.spinner("Asking vision LLM about the current scene…"):
                from compiler import compile_scene_query
                program = compile_scene_query(
                    user_query=cap_query.strip(),
                    sampled_frame_jpegs=capture["frames"],
                    tracked_entities_summary=capture["entities_summary"],
                )
            result = belief_program_to_console(program)

            # Persist via storage so the Measurement update tab can
            # surface this prediction later. Reuses the standard
            # PredictionRecord shape from Mode 5.
            prediction_id = storage.new_prediction_id()
            try:
                storage.save_prediction(storage.PredictionRecord(
                    prediction_id=prediction_id,
                    user_id=cap_user_id.strip(),
                    scenario="webcam_live_scene_query",
                    created_at=storage.now_unix(),
                    user_input={
                        "query": cap_query.strip(),
                        "n_frames_captured": len(capture["frames"]),
                        "n_entities_at_capture": len(
                            capture["entities_summary"]
                        ),
                    },
                    belief_program=program.raw,
                    wavefunction_snapshot={
                        "hypotheses": [
                            h.to_dict() for h in result.hypotheses
                        ],
                    },
                    joint_offdiag={
                        "entries": [
                            o.to_dict() for o in result.joint_offdiag
                        ],
                    },
                    is_owner_bias_flagged=False,
                ))
            except Exception as exc:
                # Storage failure is not fatal — the user still sees
                # the prediction on screen.
                st.warning(
                    f"Saved-prediction storage failed (prediction "
                    f"still shown below): {exc}"
                )

            # Reuse the Mode 5 / new-prediction result renderer so
            # the visualization stays consistent across modes.
            _render_result(
                result=result,
                user_input={
                    "query": cap_query.strip(),
                    "source": "live_webcam_capture",
                },
                scenario="webcam_live_scene_query",
                user_id=cap_user_id.strip(),
                program=program,
                prediction_id=prediction_id,
            )

    # Footer note
    st.caption(
        "Live mode runs entirely on your machine. Frames never leave "
        "your computer."
    )


def main() -> None:
    mode = render_sidebar()
    if mode == "New prediction":
        render_new_prediction()
    elif mode == "Video query":
        render_video_query()
    elif mode == "Live webcam":
        render_live_webcam()
    elif mode == "Measurement update":
        render_measurement_update()
    elif mode == "Calibration history":
        render_calibration_history()
    elif mode == "Pricing & pre-order":
        render_pricing_and_preorder()

    # Single, consistent footer rendered after the mode body so users
    # always see the version + GitHub + privacy links.
    st.divider()
    st.caption(_brand.footer_markdown())


if __name__ == "__main__":
    main()
