import pandas as pd
import streamlit as st
from io import BytesIO
from datetime import date

st.set_page_config(page_title="Automation Project Tracker", layout="wide")
st.title("🛠️ Automation Project Tracker")

# Session state to persist task data
if "task_data" not in st.session_state:
    st.session_state.task_data = []
if "edit_index" not in st.session_state:
    st.session_state.edit_index = None

st.subheader("➕ Add or Edit Task")

with st.form("task_form"):
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        project = st.text_input("Project Name")
        phase = st.text_input("Phase Name")
        task = st.text_input("Task Name")
        assigned_to = st.text_input("Assigned To")
    with col2:
        phase_weight = st.number_input("Phase Weight", min_value=0.0, step=1.0)
        task_weight = st.number_input("Task Weight", min_value=0.0, step=1.0)
        dependency = st.text_input("Dependency (optional)")
    with col3:
        task_progress = st.slider("Task Progress (%)", min_value=0, max_value=100)
        comment = st.text_input("Comment")
    with col4:
        start_date = st.date_input("Start Date", value=date.today())
        end_date = st.date_input("End Date", value=date.today())

    submitted = st.form_submit_button("Save Task")

    if submitted and project and phase and task:
        duration = (end_date - start_date).days
        health = "Good" if task_progress >= 80 else "Warning" if task_progress >= 50 else "Critical"

        task_entry = {
            "Project": project,
            "Phase": phase,
            "Phase Weight": phase_weight,
            "Task": task,
            "Task Weight": task_weight,
            "Dependency": dependency,
            "Comment": comment,
            "Task Progress": task_progress,
            "Start Date": start_date,
            "End Date": end_date,
            "Duration": duration,
            "Health": health,
            "Assigned To": assigned_to
        }

        if st.session_state.edit_index is not None:
            st.session_state.task_data[st.session_state.edit_index] = task_entry
            st.session_state.edit_index = None
            st.success(f"Task '{task}' updated!")
        else:
            st.session_state.task_data.append(task_entry)
            st.success(f"Task '{task}' added to project '{project}'!")

# Show current task table
df = pd.DataFrame(st.session_state.task_data)

if not df.empty:
    # Compute progress metrics
    df["Phase Weight"] = df["Phase Weight"].ffill()

    phase_progress = df.groupby(["Project", "Phase"]).apply(
        lambda x: (x["Task Progress"] * x["Task Weight"]).sum() / x["Task Weight"].sum()
    ).reset_index(name="Phase Progress")

    df = df.merge(phase_progress, on=["Project", "Phase"], how="left")

    project_progress = df.groupby("Project").apply(
        lambda x: (x["Phase Progress"] * x["Phase Weight"]).sum() / x["Phase Weight"].sum()
    ).reset_index(name="Project Progress")

    df = df.merge(project_progress, on="Project", how="left")

    # Warning for missing values in progress metrics
    if df["Phase Progress"].isna().any() or df["Project Progress"].isna().any():
        st.warning("⚠️ Some tasks or phases have missing weights or progress. Defaulted to 0%.")

    # Format progress columns
    df["Phase Progress"] = df["Phase Progress"].fillna(0).round(2).astype(str) + "%"
    df["Project Progress"] = df["Project Progress"].fillna(0).round(2).astype(str) + "%"

    st.subheader("📊 Task Table")

    # Filter/sort options
    with st.expander("🔍 Filter/Sort Options"):
        selected_assignee = st.selectbox("Filter by Assignee", options=["All"] + sorted(df["Assigned To"].dropna().unique().tolist()))
        selected_health = st.selectbox("Filter by Health", options=["All", "Good", "Warning", "Critical"])
        sort_by = st.selectbox("Sort by", options=["None"] + df.columns.tolist())
        ascending = st.checkbox("Sort Ascending", value=True)

    filtered_df = df.copy()
    if selected_assignee != "All":
        filtered_df = filtered_df[filtered_df["Assigned To"] == selected_assignee]
    if selected_health != "All":
        filtered_df = filtered_df[filtered_df["Health"] == selected_health]
    if sort_by != "None":
        filtered_df = filtered_df.sort_values(by=sort_by, ascending=ascending)

    st.dataframe(filtered_df, use_container_width=True)

    # Edit and delete buttons
    for i, row in filtered_df.iterrows():
        idx = df[df["Task"] == row["Task"]].index[0]
        cols = st.columns([7, 1, 1])
        cols[0].markdown(f"**{row['Task']}** in project **{row['Project']}**, phase **{row['Phase']}** - Assigned to **{row['Assigned To']}**")
        if cols[1].button("✏️ Edit", key=f"edit_{idx}"):
            st.session_state.edit_index = idx
            st.rerun()
        if cols[2].button("🗑️ Delete", key=f"delete_{idx}"):
            st.session_state.task_data.pop(idx)
            st.success("Task deleted.")
            st.rerun()

    # Download button
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Project Tracker')
    output.seek(0)

    st.download_button(
        label="📅 Download Excel Report",
        data=output,
        file_name="project_tracker.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
else:
    st.info("Add some tasks to begin tracking your project.")
