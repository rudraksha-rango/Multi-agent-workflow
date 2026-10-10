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

    .synapse-header { text-align: center; padding: 1.5rem 0 0.5rem 0; }
    .synapse-header h1 {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 2.8rem; font-weight: 800; margin-bottom: 0;
    }
    .synapse-header p { color: #8899aa; font-size: 1rem; margin-top: 0.2rem; }

    .agent-badge {
        display: inline-block; padding: 2px 10px; border-radius: 12px;
        font-size: 0.75rem; font-weight: 600; color: white; margin-right: 6px;
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
        background: #1a1d23; border: 1px solid #2d333b;
        border-radius: 8px; padding: 12px 16px; margin-bottom: 8px;
    }
    .dag-step-header { display: flex; align-items: center; gap: 8px; margin-bottom: 4px; }
    .dag-step-id { color: #8b949e; font-family: monospace; font-size: 0.8rem; }
    .dag-step-desc { color: #c9d1d9; font-size: 0.9rem; }
    .dag-step-deps { color: #6e7681; font-size: 0.75rem; font-style: italic; }

    .timing-info {
        background: #161b22; border: 1px solid #30363d; border-radius: 6px;
        padding: 8px 12px; color: #8b949e; font-size: 0.85rem; text-align: center; margin: 8px 0;
    }
    .version-card {
        background: #1a1d23; border: 1px solid #2d333b; border-radius: 6px;
        padding: 10px 14px; margin-bottom: 6px;
    }
    .version-id { color: #667eea; font-weight: 700; font-size: 0.9rem; }
    .version-reason { color: #c9d1d9; font-size: 0.85rem; }
    .version-meta { color: #6e7681; font-size: 0.75rem; }

    .metric-card {
        background: #161b22; border: 1px solid #30363d; border-radius: 8px;
        padding: 14px; text-align: center;
    }
    .metric-value { font-size: 1.5rem; font-weight: 700; color: #10b981; }
    .metric-label { font-size: 0.75rem; color: #8b949e; margin-top: 2px; }

    .block-card {
        background: #1a1d23; border: 1px solid #2d333b; border-radius: 8px;
        padding: 12px 14px; margin-bottom: 8px; font-family: monospace; font-size: 0.78rem;
    }
    .block-index { color: #667eea; font-weight: 700; font-size: 0.9rem; }
    .block-hash { color: #10b981; }
    .block-prev { color: #8b949e; }
    .block-data { color: #c9d1d9; margin-top: 6px; }

    .node-card {
        background: #1a1d23; border: 1px solid #2d333b; border-radius: 8px;
        padding: 12px 16px; margin-bottom: 8px;
    }
    .node-leader { border-color: #667eea; }
    .node-id-label { font-weight: 700; color: #c9d1d9; }
    .node-role-leader { color: #667eea; font-weight: 700; }
    .node-role-follower { color: #8b949e; }

    .security-event-auth { color: #10b981; }
    .security-event-fail { color: #ef4444; }

    .history-card {
        background: #161b22; border: 1px solid #30363d; border-radius: 8px;
        padding: 10px 14px; margin-bottom: 8px; cursor: pointer;
    }
    .history-query {
        color: #c9d1d9; font-size: 0.85rem; font-weight: 600;
        white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
        max-width: 100%;
    }
    .history-meta {
        color: #6e7681; font-size: 0.72rem; margin-top: 3px;
    }
    .history-cost { color: #10b981; }
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
    return SynapseX(num_orchestrator_nodes=3)


def get_history(limit: int = 20):
    synapse = get_synapse()
    col = synapse.mongo_history.collection
    if col is None:
        return []
    try:
        docs = list(
            col.find({}, {
                "user_request": 1,
                "final_response": 1,
                "cost_summary": 1,
                "_timestamp": 1,
                "cluster_status": 1,
            })
            .sort("_timestamp", -1)
            .limit(limit)
        )
        return docs
    except Exception:
        return []


def run_async(coro):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        try:
            pending = asyncio.all_tasks(loop)
            if pending:
                loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        except Exception:
            pass
        loop.close()
        asyncio.set_event_loop(None)


# --- Session State Initialisation ---
if "conversation" not in st.session_state:
    st.session_state.conversation = []  # list of {query, response, cost, ts}
if "query_prefill" not in st.session_state:
    st.session_state.query_prefill = ""
if "input_key" not in st.session_state:
    st.session_state.input_key = 0  # increment to force text_input reset


st.markdown("""
<div class="synapse-header">
    <h1>Synapse-X</h1>
    <p>Self-Evolving DAG &bull; Cost-Aware Scheduling &bull; Zero Trust &bull; Blockchain Audit &bull; Decentralized Orchestration</p>
</div>
""", unsafe_allow_html=True)

st.divider()

# --- Conversation thread header ---
if st.session_state.conversation:
    c_left, c_right = st.columns([6, 1])
    with c_left:
        st.markdown(f"**Conversation thread** — {len(st.session_state.conversation)} turn(s)")
    with c_right:
        if st.button("New Chat", key="new_chat"):
            st.session_state.conversation = []
            st.session_state.query_prefill = ""
            st.session_state.input_key += 1
            st.rerun()

col1, col2 = st.columns([5, 1])
with col1:
    user_query = st.text_input(
        "Ask anything",
        placeholder="e.g. latest news from Tamil Nadu today",
        label_visibility="collapsed",
        value=st.session_state.query_prefill,
        key=f"query_input_{st.session_state.input_key}",
    )
    # Clear prefill so it doesn't persist after first render
    st.session_state.query_prefill = ""
with col2:
    run_btn = st.button("Run", use_container_width=True, type="primary")

if run_btn and user_query.strip():
    synapse = get_synapse()

    # Build context string from last 3 conversation turns
    context_prefix = ""
    if st.session_state.conversation:
        turns = st.session_state.conversation[-3:]
        context_parts = []
        for turn in turns:
            context_parts.append(
                f"Previous question: {turn['query']}\n"
                f"Previous answer (summary): {turn['response'][:400]}"
            )
        context_prefix = "[CONVERSATION CONTEXT — answer the new question in light of this]\n"
        context_prefix += "\n---\n".join(context_parts)
        context_prefix += "\n---\n\nNew question: "

    full_query = context_prefix + user_query.strip()

    with st.status("Planning and Executing...", expanded=True) as status_widget:
        st.write("**Phase 1:** Planning DAG...")
        st.write("**Phase 2:** Cost Scheduling...")
        st.write("**Phase 3:** Cluster Dispatch with Zero Trust & Blockchain...")
        start_time = time.time()
        result = run_async(synapse.process_request_detailed(full_query))
        total_time = time.time() - start_time

        if result.get("error"):
            status_widget.update(label="Pipeline Error", state="error")
            st.error(result["error"])
        else:
            status_widget.update(label=f"Completed in {total_time:.1f}s", state="complete")
            # Append this turn to the conversation thread
            st.session_state.conversation.append({
                "query": user_query.strip(),
                "response": result.get("final_response", ""),
                "cost": result.get("cost_summary", {}).get("used_cost", 0),
                "ts": time.strftime("%H:%M:%S"),
            })
            # Reset input after successful run
            st.session_state.input_key += 1

    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "DAG Plan", "Step Results", "DAG Versions",
        "Cost Dashboard", "Security", "Blockchain Ledger", "Final Response"
    ])

    # --- Tab 1: DAG Plan ---
    with tab1:
        st.markdown("### Execution Plan (DAG)")
        dag_plan = result.get("dag_plan", [])
        for step in dag_plan:
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
            </div>""", unsafe_allow_html=True)

        cost_summary = result.get("cost_summary", {})
        st.markdown(f"""
        <div class="timing-info">
            Total time: <strong>{total_time:.2f}s</strong> &nbsp;|&nbsp;
            Tasks: <strong>{len(dag_plan)}</strong> &nbsp;|&nbsp;
            LLM Calls: <strong>{cost_summary.get('used_llm_calls', 'N/A')}</strong> &nbsp;|&nbsp;
            Total Cost: <strong>${cost_summary.get('used_cost', 0):.6f}</strong> &nbsp;|&nbsp;
            Orchestrator Nodes: <strong>3</strong>
        </div>""", unsafe_allow_html=True)

    # --- Tab 2: Step Results ---
    with tab2:
        st.markdown("### Step-by-Step Results")
        task_results = result.get("task_results", {})
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
                    f'**{entry["task_id"]}** → <span style="color:{color};font-weight:600">{decision}</span> — {entry["reason"]}',
                    unsafe_allow_html=True
                )

    # --- Tab 3: DAG Versions ---
    with tab3:
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
                    <div class="version-meta">Parent: {parent} &nbsp;|&nbsp; Modified nodes: {modified} &nbsp;|&nbsp; {v.get('timestamp', '')}</div>
                </div>""", unsafe_allow_html=True)
        else:
            st.info("No DAG modifications occurred — the initial plan executed successfully.")

    # --- Tab 4: Cost Dashboard ---
    with tab4:
        st.markdown("### Cost Dashboard")
        cost_summary = result.get("cost_summary", {})
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">${cost_summary.get('used_cost', 0):.6f}</div>
                <div class="metric-label">Total Cost (Budget: ${cost_summary.get('max_cost', 1):.2f})</div>
            </div>""", unsafe_allow_html=True)
        with c2:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">{cost_summary.get('used_llm_calls', 0)}</div>
                <div class="metric-label">LLM Calls (Max: {cost_summary.get('max_llm_calls', 20)})</div>
            </div>""", unsafe_allow_html=True)
        with c3:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">{cost_summary.get('elapsed_runtime', 0):.1f}s</div>
                <div class="metric-label">Runtime (Max: {cost_summary.get('max_runtime', 120):.0f}s)</div>
            </div>""", unsafe_allow_html=True)

        scheduler_decisions = result.get("scheduler_decisions", [])
        if scheduler_decisions:
            st.markdown("### Scheduler Decisions")
            for dec in scheduler_decisions:
                st.markdown(
                    f"**{dec.get('selected_model')}** selected for: _{dec.get('task', '')}_  "
                    f"(score: `{dec.get('score', 0):.4f}`, complexity: `{dec.get('complexity', 'N/A')}`)"
                )

        model_stats = result.get("model_stats", {})
        if model_stats:
            st.markdown("### Model Performance History")
            for model_name, stats in model_stats.items():
                with st.expander(f"{model_name}", expanded=False):
                    sc1, sc2, sc3, sc4 = st.columns(4)
                    sc1.metric("Avg Cost", f"${stats.get('avg_cost', 0):.6f}")
                    sc2.metric("Avg Latency", f"{stats.get('avg_latency', 0):.0f}ms")
                    sc3.metric("Success Rate", f"{stats.get('success_rate', 0):.0%}")
                    sc4.metric("Total Calls", stats.get('total_calls', 0))

    # --- Tab 5: Security Dashboard ---
    with tab5:
        st.markdown("### Zero Trust Security Dashboard")
        metrics = result.get("security_metrics", {})
        cluster_status = result.get("cluster_status", {})

        s1, s2, s3, s4 = st.columns(4)
        with s1:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value" style="color:#10b981">{metrics.get('authenticated_requests', 0)}</div>
                <div class="metric-label">Authenticated Requests</div>
            </div>""", unsafe_allow_html=True)
        with s2:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value" style="color:#ef4444">{metrics.get('rejected_requests', 0)}</div>
                <div class="metric-label">Rejected Requests</div>
            </div>""", unsafe_allow_html=True)
        with s3:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value" style="color:#f59e0b">{metrics.get('unauthorized_attempts', 0)}</div>
                <div class="metric-label">Unauthorized Attempts</div>
            </div>""", unsafe_allow_html=True)
        with s4:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value" style="color:#ef4444">{metrics.get('signature_failures', 0)}</div>
                <div class="metric-label">Signature Failures</div>
            </div>""", unsafe_allow_html=True)

        st.markdown("### Orchestrator Cluster Status (Phase 3C)")
        all_nodes = cluster_status.get("nodes", [])
        active_nodes = cluster_status.get("active_nodes", [])
        leader = cluster_status.get("leader", "None")
        for node_id in all_nodes:
            is_leader = node_id == leader
            is_active = node_id in active_nodes
            role_label = "LEADER" if is_leader else ("FOLLOWER" if is_active else "OFFLINE")
            role_css = "node-role-leader" if is_leader else "node-role-follower"
            card_css = "node-card node-leader" if is_leader else "node-card"
            st.markdown(f"""
            <div class="{card_css}">
                <span class="node-id-label">{node_id}</span> &nbsp;
                <span class="{role_css}">[{role_label}]</span>
            </div>""", unsafe_allow_html=True)

    # --- Tab 6: Blockchain Ledger ---
    with tab6:
        st.markdown("### Blockchain Audit Ledger")
        chain = result.get("blockchain_ledger", [])

        valid_color = "#10b981"
        st.markdown(
            f'Chain integrity: <span style="color:{valid_color};font-weight:700">VALID</span>',
            unsafe_allow_html=True
        )
        st.caption(f"Total blocks: {len(chain)} | All blocks cryptographically chained via SHA-256")

        for block in chain:
            data = block.get("data", {})
            status = data.get("status", "")
            color = "#10b981" if status == "COMPLETED" else "#ef4444" if status == "FAILED" else "#8b949e"
            st.markdown(f"""
            <div class="block-card">
                <span class="block-index">Block #{block['index']}</span> &nbsp;
                <span style="color:{color}">&#9632; {status or 'GENESIS'}</span><br/>
                <span class="block-hash">Hash: {block['hash']}</span><br/>
                <span class="block-prev">Prev: {block['previous_hash']}</span><br/>
                <span style="color:#8b949e">{block['timestamp']}</span>
                <div class="block-data">
                    {f"Agent: {data.get('agent_id', '')} | Task: {data.get('task_hash', '')[:16]}... | Result: {data.get('result_hash', '')[:16]}..." if data.get('agent_id') else "Genesis block"}
                </div>
            </div>""", unsafe_allow_html=True)

    # --- Tab 7: Final Response ---
    with tab7:
        st.markdown("### Final Response")
        st.markdown(result.get("final_response", "No response generated."))

elif run_btn:
    st.warning("Please enter a query first.")

# --- Render conversation thread above input ---
if st.session_state.conversation:
    st.divider()
    st.markdown("### Conversation Thread")
    for turn_idx, turn in enumerate(st.session_state.conversation):
        with st.chat_message("user"):
            st.markdown(f"**Q{turn_idx + 1}:** {turn['query']}")
        with st.chat_message("assistant"):
            st.markdown(turn["response"])
            st.caption(f"Turn {turn_idx + 1} | Cost: ${turn['cost']:.4f} | {turn['ts']}")

with st.sidebar:
    st.markdown("## Synapse-X")
    st.markdown("""
    **Milestone 1 (30%):**
    - Planner Agent + DAG execution
    - Worker Agents (Web, Content, System)
    - LangSmith observability

    **Milestone 2 (50%):**
    - Self-Evolving DAG (runtime adaptation)
    - Cost-Aware Scheduler (multi-objective)
    - Budget management

    **Milestone 3 (100%):**
    - Zero Trust (Ed25519 signing)
    - Blockchain Audit Ledger (SHA-256)
    - Decentralized Orchestration (3 nodes, leader election)

    **LLM Pool:**
    - Groq (`openai/gpt-oss-20b`)
    - Gemini (`gemini-3.6-flash`)
    """)
    st.divider()
    st.markdown("[LangSmith Dashboard](https://smith.langchain.com/o/64648b6e-4dbc-4e49-a428-0072ca87be79/projects?view=new)")

    st.divider()
    st.markdown("### Chat History")

    col_h1, col_h2 = st.columns([3, 1])
    with col_h2:
        refresh_history = st.button("Refresh", key="refresh_history", use_container_width=True)

    history_docs = get_history(20)

    if not history_docs:
        st.caption("No chat history found. MongoDB may not be connected or no chats have been saved yet.")
    else:
        st.caption(f"{len(history_docs)} recent session(s) from MongoDB Atlas")
        for i, doc in enumerate(history_docs):
            query = doc.get("user_request", "Unknown query")
            response = doc.get("final_response", "")
            ts = doc.get("_timestamp")
            cost_info = doc.get("cost_summary", {})
            used_cost = cost_info.get("used_cost", 0)
            used_calls = cost_info.get("used_llm_calls", 0)
            ts_str = ts.strftime("%d %b %Y, %H:%M") if ts else "Unknown time"

            with st.expander(f"{query[:55]}..." if len(query) > 55 else query, expanded=False):
                st.markdown(f"""
<div class="history-meta">
    <span>{ts_str}</span> &nbsp;|
    <span class="history-cost"> ${used_cost:.4f}</span> &nbsp;|
    <span> {used_calls} LLM calls</span>
</div>""", unsafe_allow_html=True)
                st.divider()
                st.markdown("**Response:**")
                st.markdown(response[:600] + ("..." if len(response) > 600 else ""))
                st.divider()
                if st.button("Continue this chat", key=f"continue_{i}", use_container_width=True):
                    # Load this session as the first turn of a new conversation thread
                    # Strip any injected context prefix from stored queries
                    clean_query = query
                    if "New question: " in query:
                        clean_query = query.split("New question: ")[-1]
                    st.session_state.conversation = [{
                        "query": clean_query,
                        "response": response,
                        "cost": used_cost,
                        "ts": ts_str,
                    }]
                    st.session_state.query_prefill = ""
                    st.session_state.input_key += 1
                    st.rerun()

