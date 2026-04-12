"""Workflow Builder — trigger-based automation with conditions and actions."""

import json
import os
import streamlit as st
from datetime import datetime

from core.settings import load_settings, save_settings


# Workflow storage file
WORKFLOWS_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "workflows.json",
)


def load_workflows():
    """Load saved workflows."""
    if os.path.exists(WORKFLOWS_FILE):
        try:
            with open(WORKFLOWS_FILE, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return []


def save_workflows(workflows):
    """Save workflows to file."""
    os.makedirs(os.path.dirname(WORKFLOWS_FILE), exist_ok=True)
    with open(WORKFLOWS_FILE, "w") as f:
        json.dump(workflows, f, indent=2)


TRIGGERS = {
    "new_lead": "New Lead Added",
    "reply_received": "Reply Received",
    "bounce_detected": "Bounce Detected",
    "score_above": "Lead Score Above Threshold",
    "status_changed": "Lead Status Changed",
}

CONDITIONS = {
    "niche_is": "Niche Is",
    "grade_is": "Lead Grade Is",
    "score_above": "Score Above",
    "source_is": "Source Is",
}

ACTIONS = {
    "add_to_campaign": "Add to Campaign",
    "change_status": "Change Lead Status",
    "add_tag": "Add Tag",
    "send_webhook": "Send Webhook Notification",
    "add_note": "Add Note",
}


def render(settings):
    st.markdown("## Workflow Builder")
    st.caption("Create automated workflows: When [trigger] happens, if [condition] is met, do [action].")

    tab1, tab2 = st.tabs(["My Workflows", "Create Workflow"])

    with tab1:
        _render_workflow_list()

    with tab2:
        _render_create_workflow()


def _render_workflow_list():
    """Show existing workflows."""
    workflows = load_workflows()

    if not workflows:
        st.info("No workflows yet. Create your first automation.")
        return

    for i, wf in enumerate(workflows):
        trigger_label = TRIGGERS.get(wf.get("trigger", ""), wf.get("trigger", ""))
        action_label = ACTIONS.get(wf.get("action", ""), wf.get("action", ""))
        active = wf.get("active", True)
        status = "Active" if active else "Paused"

        with st.expander(f"{wf.get('name', 'Workflow')} — {status}"):
            st.markdown(f"**Trigger:** {trigger_label}")
            if wf.get("trigger_value"):
                st.markdown(f"**Trigger Value:** {wf['trigger_value']}")

            if wf.get("condition"):
                cond_label = CONDITIONS.get(wf["condition"], wf["condition"])
                st.markdown(f"**Condition:** {cond_label} = {wf.get('condition_value', '')}")

            st.markdown(f"**Action:** {action_label}")
            if wf.get("action_value"):
                st.markdown(f"**Action Value:** {wf['action_value']}")

            # Toggle active
            col1, col2 = st.columns(2)
            with col1:
                if active:
                    if st.button("Pause", key=f"pause_wf_{i}", use_container_width=True):
                        workflows[i]["active"] = False
                        save_workflows(workflows)
                        st.rerun()
                else:
                    if st.button("Activate", key=f"act_wf_{i}", use_container_width=True):
                        workflows[i]["active"] = True
                        save_workflows(workflows)
                        st.rerun()

            with col2:
                if st.button("Delete", key=f"del_wf_{i}", use_container_width=True):
                    workflows.pop(i)
                    save_workflows(workflows)
                    st.rerun()


def _render_create_workflow():
    """Create new workflow form."""
    with st.form("create_workflow"):
        name = st.text_input("Workflow Name *", placeholder="e.g., Auto-assign high-score leads")

        st.markdown("---")
        st.markdown("**When this happens (Trigger):**")
        trigger = st.selectbox("Trigger", list(TRIGGERS.keys()), format_func=lambda x: TRIGGERS[x])

        trigger_value = ""
        if trigger == "score_above":
            trigger_value = str(st.number_input("Score threshold", 0, 100, 70, key="trig_score"))
        elif trigger == "status_changed":
            trigger_value = st.selectbox("To status", ["replied", "contacted", "won", "lost"], key="trig_status")

        st.markdown("---")
        st.markdown("**Only if (Condition — optional):**")
        use_condition = st.checkbox("Add condition")
        condition = ""
        condition_value = ""

        if use_condition:
            condition = st.selectbox("Condition", list(CONDITIONS.keys()), format_func=lambda x: CONDITIONS[x])
            if condition == "niche_is":
                condition_value = st.text_input("Niche", placeholder="dentist")
            elif condition == "grade_is":
                condition_value = st.selectbox("Grade", ["A", "B", "C", "D", "F"], key="cond_grade")
            elif condition == "score_above":
                condition_value = str(st.number_input("Score", 0, 100, 70, key="cond_score"))
            elif condition == "source_is":
                condition_value = st.text_input("Source", placeholder="DuckDuckGo")

        st.markdown("---")
        st.markdown("**Do this (Action):**")
        action = st.selectbox("Action", list(ACTIONS.keys()), format_func=lambda x: ACTIONS[x])

        action_value = ""
        if action == "change_status":
            from core.constants import LEAD_STATUSES
            action_value = st.selectbox("New status", LEAD_STATUSES, key="act_status")
        elif action == "add_tag":
            action_value = st.text_input("Tag name", placeholder="high-priority")
        elif action == "add_to_campaign":
            try:
                from core.campaigns import CampaignManager
                campaigns = CampaignManager.list_campaigns()
                if campaigns:
                    action_value = st.selectbox(
                        "Campaign",
                        [c.id for c in campaigns],
                        format_func=lambda x: next((c.name for c in campaigns if c.id == x), x),
                    )
                else:
                    st.caption("No campaigns available. Create one first.")
            except Exception:
                st.caption("Campaign system not available")
        elif action == "add_note":
            action_value = st.text_input("Note text", placeholder="Auto-tagged by workflow")
        elif action == "send_webhook":
            action_value = st.text_input("Custom message", placeholder="High-score lead found!")

        submitted = st.form_submit_button("Create Workflow", type="primary", use_container_width=True)

    if submitted:
        if not name:
            st.error("Please enter a workflow name")
            return

        workflow = {
            "name": name,
            "trigger": trigger,
            "trigger_value": trigger_value,
            "condition": condition,
            "condition_value": condition_value,
            "action": action,
            "action_value": action_value,
            "active": True,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

        workflows = load_workflows()
        workflows.append(workflow)
        save_workflows(workflows)
        st.success(f"Workflow '{name}' created!")
        st.rerun()


def execute_workflows(trigger_type, lead_data=None, context=None):
    """
    Execute matching workflows for a trigger event.
    Called from other modules when events happen.
    """
    workflows = load_workflows()
    active = [w for w in workflows if w.get("active") and w.get("trigger") == trigger_type]

    if not active or not lead_data:
        return

    for wf in active:
        # Check trigger value
        if trigger_type == "score_above":
            threshold = int(wf.get("trigger_value", 0) or 0)
            lead_score = float(lead_data.get("lead_score", 0) or 0)
            if lead_score < threshold:
                continue

        # Check condition
        if wf.get("condition"):
            if not _check_condition(wf, lead_data):
                continue

        # Execute action
        _execute_action(wf, lead_data)


def _check_condition(wf, lead_data):
    """Check if workflow condition is met."""
    condition = wf.get("condition", "")
    value = wf.get("condition_value", "")

    if condition == "niche_is":
        return str(lead_data.get("niche", "")).lower() == value.lower()
    elif condition == "grade_is":
        return str(lead_data.get("lead_grade", "")).upper() == value.upper()
    elif condition == "score_above":
        return float(lead_data.get("lead_score", 0) or 0) >= float(value or 0)
    elif condition == "source_is":
        return str(lead_data.get("source", "")).lower() == value.lower()

    return True


def _execute_action(wf, lead_data):
    """Execute a workflow action."""
    action = wf.get("action", "")
    value = wf.get("action_value", "")
    email = lead_data.get("email", "")

    try:
        if action == "change_status" and email:
            from core.database_v2 import update_lead_status
            update_lead_status(email, value)

        elif action == "add_to_campaign" and email and value:
            from core.campaigns import CampaignManager
            CampaignManager.assign_leads(value, [email])

        elif action == "add_tag" and email:
            from core.database_v2 import get_connection, _ensure_db
            _ensure_db()
            conn = get_connection()
            try:
                row = conn.execute("SELECT tags FROM leads WHERE email=?", (email,)).fetchone()
                if row:
                    existing = row["tags"] or ""
                    tags = set(t.strip() for t in existing.split(",") if t.strip())
                    tags.add(value)
                    conn.execute(
                        "UPDATE leads SET tags=? WHERE email=?",
                        (",".join(tags), email),
                    )
                    conn.commit()
            finally:
                conn.close()

        elif action == "send_webhook":
            from core.settings import load_settings
            settings = load_settings()
            from automation.webhooks import send_discord, send_slack
            msg = f"{value}: {lead_data.get('business_name', '')} ({email})"
            send_discord(settings.get("discord_webhook", ""), msg)
            send_slack(settings.get("slack_webhook", ""), msg)

        elif action == "add_note" and email:
            from core.database_v2 import get_connection, _ensure_db
            _ensure_db()
            conn = get_connection()
            try:
                row = conn.execute("SELECT notes FROM leads WHERE email=?", (email,)).fetchone()
                if row:
                    existing = row["notes"] or ""
                    new_notes = f"{existing}\n[Auto] {value}" if existing else f"[Auto] {value}"
                    conn.execute(
                        "UPDATE leads SET notes=? WHERE email=?",
                        (new_notes.strip(), email),
                    )
                    conn.commit()
            finally:
                conn.close()

    except Exception as e:
        print(f"Workflow action error: {e}")
