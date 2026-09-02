import asyncio
import streamlit as st
import time

st.set_page_config(
    page_title="Synapse-X",
    page_icon="S",
    layout="wide",
)

st.markdown("""
<style>
    .main { background-color: #0e1117; }
    
    .synapse-header {
        text-align: center;
        padding: 1.5rem 0 0.5rem 0;
    }
    .synapse-header h1 {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 2.8rem;
        font-weight: 800;
        margin-bottom: 0;
    }
    .synapse-header p {
        color: #8899aa;
        font-size: 1rem;
        margin-top: 0.2rem;
    }
    
    .agent-badge {
        display: inline-block;
        padding: 2px 10px;
        border-radius: 12px;
        font-size: 0.75rem;
        font-weight: 600;
        color: white;
        margin-right: 6px;
    }
    .agent-WebAgent { background: #2563eb; }
    .agent-ContentAgent { background: #7c3aed; }
    .agent-SystemAgent { background: #059669; }
    .agent-FileAgent { background: #d97706; }
    .agent-MemoryAgent { background: #dc2626; }
    
    .status-completed { color: #10b981; font-weight: 600; }
    .status-failed { color: #ef4444; font-weight: 600; }
    .status-running { color: #f59e0b; font-weight: 600; }
    
    .dag-step {
        background: #1a1d23;
        border: 1px solid #2d333b;
        border-radius: 8px;
        padding: 12px 16px;
        margin-bottom: 8px;
    }
    .dag-step-header {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 4px;
    }
    .dag-step-id { color: #8b949e; font-family: monospace; font-size: 0.8rem; }
    .dag-step-desc { color: #c9d1d9; font-size: 0.9rem; }
    .dag-step-deps { color: #6e7681; font-size: 0.75rem; font-style: italic; }
    
    .timing-info {
        background: #161b22;
        border: 1px solid #30363d;
        border-radius: 6px;
        padding: 8px 12px;
        color: #8b949e;
        font-size: 0.85rem;
        text-align: center;
        margin: 8px 0;
    }

    .version-card {
        background: #1a1d23;
        border: 1px solid #2d333b;
        border-radius: 6px;
        padding: 10px 14px;
        margin-bottom: 6px;
    }
    .version-id { color: #667eea; font-weight: 700; font-size: 0.9rem; }
    .version-reason { color: #c9d1d9; font-size: 0.85rem; }
    .version-meta { color: #6e7681; font-size: 0.75rem; }

    .cost-metric {
        background: #161b22;
        border: 1px solid #30363d;
        border-radius: 8px;
        padding: 12px;
        text-align: center;
    }
    .cost-metric-value { font-size: 1.4rem; font-weight: 700; color: #10b981; }
    .cost-metric-label { font-size: 0.75rem; color: #8b949e; margin-top: 2px; }
</style>
""", unsafe_allow_html=True)


def get_agent_badge(agent_type: str) -> str:
    return f'<span class="agent-badge agent-{agent_type}">{agent_type}</span>'

def get_status_badge(status: str) -> str:
    s = status.upper()
    css = "completed" if s == "COMPLETED" else "failed" if s == "FAILED" else "running"
    label = "[DONE]" if s == "COMPLETED" else "[FAIL]" if s == "FAILED" else "[...]"
    return f'<span class="status-{css}">{label} {s}</span>'

@st.cache_resource
def get_synapse():
    from synapse import SynapseX
    return SynapseX()

def run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


st.markdown("""
<div class="synapse-header">
    <h1>Synapse-X</h1>
    <p>Multi-Agent Orchestration System &mdash; Self-Evolving DAG + Cost-Aware Scheduling</p>
</div>
""", unsafe_allow_html=True)

st.divider()

col1, col2 = st.columns([5, 1])
with col1:
    user_query = st.text_input(
        "Ask anything",
        placeholder="e.g. latest news from Tamil Nadu today",
        label_visibility="collapsed",
    )
with col2:
    run_btn = st.button("Run", use_container_width=True, type="primary")

if run_btn and user_query.strip():
    synapse = get_synapse()
    
    with st.status("Planning and Executing...", expanded=True) as status_widget:
        st.write("**Phase 1:** Interpreting your request...")
        
        start_time = time.time()
        result = run_async(synapse.process_request_detailed(user_query.strip()))
        total_time = time.time() - start_time
        
        if result.get("error"):
            status_widget.update(label="Pipeline Error", state="error")
            st.error(result["error"])
        else:
            status_widget.update(label=f"Completed in {total_time:.1f}s", state="complete")
    
    tab_dag, tab_results, tab_versions, tab_cost, tab_response = st.tabs([
        "DAG Plan", "Step Results", "DAG Versions", "Cost Dashboard", "Final Response"
    ])

    with tab_dag:
        st.markdown("### Execution Plan (DAG)")
        dag_plan = result.get("dag_plan", [])
        if dag_plan:
            for i, step in enumerate(dag_plan):
                task_id = step["task_id"]
                agent = step["agent_type"]
                desc = step["description"]
                deps = step["dependencies"]
                task_result_entry = result.get("task_results", {}).get(desc, {})
                status = task_result_entry.get("status", "PENDING")
                dep_text = f"Depends on: {', '.join(deps)}" if deps else "No dependencies (root task)"
                st.markdown(f"""
                <div class="dag-step">
                    <div class="dag-step-header">
                        <span class="dag-step-id">{task_id}</span>
                        {get_agent_badge(agent)}
                        {get_status_badge(status)}
                    </div>
                    <div class="dag-step-desc">{desc}</div>
                    <div class="dag-step-deps">{dep_text}</div>
                </div>
                """, unsafe_allow_html=True)

        cost_summary = result.get("cost_summary", {})
        st.markdown(f"""
        <div class="timing-info">
            Total pipeline time: <strong>{total_time:.2f}s</strong> &nbsp;|&nbsp;
            Tasks: <strong>{len(dag_plan)}</strong> &nbsp;|&nbsp;
            LLM Calls: <strong>{cost_summary.get('used_llm_calls', 'N/A')}</strong> &nbsp;|&nbsp;
            Total Cost: <strong>${cost_summary.get('used_cost', 0):.6f}</strong>
        </div>
        """, unsafe_allow_html=True)

    with tab_results:
        st.markdown("### Step-by-Step Results")
        task_results = result.get("task_results", {})
        if task_results:
            for desc, info in task_results.items():
                status = info.get("status", "UNKNOWN")
                res = info.get("result", "No result")
                label = "[DONE]" if status == "COMPLETED" else "[FAIL]"
                with st.expander(f"{label} {desc}", expanded=False):
                    st.markdown(str(res))

        eval_log = result.get("evaluation_log", [])
        if eval_log:
            st.markdown("### DAG Evaluation Decisions")
            for entry in eval_log:
                decision = entry.get("decision", "")
                color = "#10b981" if decision == "CONTINUE" else "#f59e0b" if decision in ["ADD_TASK", "MODIFY"] else "#ef4444"
                st.markdown(
                    f'**{entry["task_id"]}** → '
                    f'<span style="color:{color};font-weight:600">{decision}</span> — {entry["reason"]}',
                    unsafe_allow_html=True
                )

    with tab_versions:
        st.markdown("### DAG Version History")
        dag_versions = result.get("dag_versions", [])
        if dag_versions:
            for v in dag_versions:
                parent = f"v{v['parent_version']}" if v.get("parent_version") else "initial"
                modified = ", ".join(v.get("modified_nodes", [])) or "none"
                st.markdown(f"""
                <div class="version-card">
                    <div class="version-id">Version {v['version_id']}</div>
                    <div class="version-reason">{v['reason']}</div>
                    <div class="version-meta">Parent: {parent} | Modified: {modified} | {v.get('timestamp', '')}</div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No DAG modifications occurred — the initial plan executed successfully.")

    with tab_cost:
        st.markdown("### Cost Dashboard")
        
        cost_summary = result.get("cost_summary", {})
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown(f"""
            <div class="cost-metric">
                <div class="cost-metric-value">${cost_summary.get('used_cost', 0):.6f}</div>
                <div class="cost-metric-label">Total Cost (of ${cost_summary.get('max_cost', 1.0):.2f} budget)</div>
            </div>
            """, unsafe_allow_html=True)
        with c2:
            st.markdown(f"""
            <div class="cost-metric">
                <div class="cost-metric-value">{cost_summary.get('used_llm_calls', 0)}</div>
                <div class="cost-metric-label">LLM Calls (of {cost_summary.get('max_llm_calls', 20)} max)</div>
            </div>
            """, unsafe_allow_html=True)
        with c3:
            st.markdown(f"""
            <div class="cost-metric">
                <div class="cost-metric-value">{cost_summary.get('elapsed_runtime', 0):.1f}s</div>
                <div class="cost-metric-label">Runtime (of {cost_summary.get('max_runtime', 120):.0f}s max)</div>
            </div>
            """, unsafe_allow_html=True)

        scheduler_decisions = result.get("scheduler_decisions", [])
        if scheduler_decisions:
            st.markdown("### Scheduler Decisions")
            for dec in scheduler_decisions:
                st.markdown(
                    f"**{dec.get('selected_model', 'N/A')}** selected for: _{dec.get('task', 'N/A')}_ "
                    f"(score: {dec.get('score', 0):.4f}, complexity: {dec.get('complexity', 'N/A')})"
                )

        model_stats = result.get("model_stats", {})
        if model_stats:
            st.markdown("### Model Performance Stats")
            for model_name, stats in model_stats.items():
                with st.expander(f"{model_name}", expanded=False):
                    sc1, sc2, sc3, sc4 = st.columns(4)
                    sc1.metric("Avg Cost", f"${stats.get('avg_cost', 0):.6f}")
                    sc2.metric("Avg Latency", f"{stats.get('avg_latency', 0):.0f}ms")
                    sc3.metric("Success Rate", f"{stats.get('success_rate', 0):.0%}")
                    sc4.metric("Total Calls", stats.get('total_calls', 0))

    with tab_response:
        st.markdown("### Final Response")
        st.markdown(result.get("final_response", "No response generated."))

elif run_btn:
    st.warning("Please enter a query first.")

with st.sidebar:
    st.markdown("## System Info")
    st.markdown("""
    **Architecture:**
    - **Planner Agent** -- Decomposes requests into a DAG
    - **WebAgent** -- DuckDuckGo web search
    - **ContentAgent** -- LLM-powered summarization
    - **SystemAgent** -- Data aggregation
    - **InteractionAgent** -- Final response generation
    
    **Milestone 2 Features:**
    - Self-Evolving DAG with runtime evaluation
    - Cost-Aware multi-objective scheduler
    - Budget management (cost / runtime / calls)
    - DAG versioning with full history
    
    **LLM Pool:**
    - Groq (`openai/gpt-oss-20b`)
    - Gemini (`gemini-2.0-flash`)
    - Dynamic selection via CostScheduler
    
    **Observability:**
    - LangSmith tracing enabled
    - Model stats persisted to JSON
    """)
    
    st.divider()
    st.markdown("### Links")
    st.markdown("[LangSmith Dashboard](https://smith.langchain.com/o/64648b6e-4dbc-4e49-a428-0072ca87be79/projects?view=new)")
