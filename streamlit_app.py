import json
import pandas as pd
import streamlit as st
import plotly.express as px
import datetime
import re
import os

st.set_page_config(page_title="MGEN API Test Results Comparison", layout="wide")

st.markdown("""
    <style>
        .block-container {
            padding-top: 4rem;
            padding-bottom: 0rem;
        }
        section[data-testid="stSidebar"] {
            width: 400px !important;
        }
    </style>
""", unsafe_allow_html=True)

results_dir = os.path.join(os.path.dirname(__file__), "results")
json_files = []
if os.path.isdir(results_dir):
    json_files = [f for f in os.listdir(results_dir) if f.endswith('.json')]
json_files.sort()
options = ["-- None --"] + json_files

# Initialize session state from query params if not already set
if "primary_selection" not in st.session_state:
    qp_primary = st.query_params.get("primary")
    if qp_primary in options:
        st.session_state.primary_selection = qp_primary
    elif f"{qp_primary}.json" in options:
        st.session_state.primary_selection = f"{qp_primary}.json"
    else:
        st.session_state.primary_selection = options[0]

if "secondary_selection" not in st.session_state:
    qp_secondary = st.query_params.get("secondary")
    if qp_secondary in options:
        st.session_state.secondary_selection = qp_secondary
    elif f"{qp_secondary}.json" in options:
        st.session_state.secondary_selection = f"{qp_secondary}.json"
    else:
        st.session_state.secondary_selection = options[0]

def update_primary_param():
    val = st.session_state.primary_selection
    if val != "-- None --":
        st.query_params["primary"] = val
    elif "primary" in st.query_params:
        del st.query_params["primary"]

def update_secondary_param():
    val = st.session_state.secondary_selection
    if val != "-- None --":
        st.query_params["secondary"] = val
    elif "secondary" in st.query_params:
        del st.query_params["secondary"]

# Ensure URL immediately reflects the loaded state
update_primary_param()
update_secondary_param()

with st.sidebar:
    st.header("Result Sets")
    
    primary_selection = st.selectbox(
        "Select Primary Result JSON", 
        options, 
        key="primary_selection",
        on_change=update_primary_param
    )
    primary_file = os.path.join(results_dir, primary_selection) if primary_selection != "-- None --" else None
    primary_container = st.container()
    
    st.divider()
    
    secondary_selection = st.selectbox(
        "Select Secondary Result JSON", 
        options, 
        key="secondary_selection",
        on_change=update_secondary_param
    )
    secondary_file = os.path.join(results_dir, secondary_selection) if secondary_selection != "-- None --" else None
    secondary_container = st.container()

@st.cache_data
def load_and_parse_results(file_obj, dataset_name):
    if not file_obj:
        return pd.DataFrame(), [], {}
    
    if isinstance(file_obj, str):
        with open(file_obj, 'r', encoding='utf-8') as f:
            data = json.load(f)
    else:
        data = json.load(file_obj)
    channels = data.get("channels", [])
    
    metadata = {}
    config_defaults = data.get("config", {}).get("defaults", {})
    if config_defaults:
        metadata["System"] = config_defaults.get("system", "Unknown")
        metadata["Tenant"] = config_defaults.get("tenant", "Unknown")
        metadata["Environment"] = config_defaults.get("environment", "Unknown")
    
    start_time = data.get("run_start_time", 0)
    if start_time:
        try:
            metadata["Run Date"] = datetime.datetime.fromtimestamp(start_time).strftime('%Y-%m-%d %H:%M:%S')
        except Exception:
            metadata["Run Date"] = "Unknown"
            
    desc = data.get("dataset_description", "")
    if desc:
        metadata["Description"] = desc
        
    yaml_content = data.get("yaml_content", "")
    if yaml_content:
        metadata["YAML"] = yaml_content
    
    rows = []
    full_data_lookup = []
    
    base_time = pd.Timestamp("2020-01-01 00:00:00")
    
    for ch in channels:
        ch_name = ch.get("name", "Unknown Channel")
        ch_body = ch.get("body", {})
        
        for req in ch.get("requests", []):
            start_off = req.get("start_offset")
            end_off = req.get("end_offset")
            
            # If a request never finished or started properly, handle it gracefully
            if start_off is None:
                continue
            if end_off is None:
                end_off = start_off + req.get("elapsed_seconds", 0)
                if start_off == end_off:
                    end_off = start_off + 0.1 # Minimum visible width
            
            start_off = round(start_off, 3)
            end_off = round(end_off, 3)
            
            start_dt = base_time + pd.to_timedelta(start_off, unit="s")
            end_dt = base_time + pd.to_timedelta(end_off, unit="s")
            
            req_index = req.get("request_index", 0)
            task_name = f"{ch_name} (R{req_index+1:02d})"
            
            status = req.get("result", "Unknown")
            state = req.get("state", "Unknown")
            err_body = req.get("err_body", "")
            
            def format_hover_json(json_str):
                s = json_str.replace('<', '&lt;').replace('>', '&gt;')
                # Plotly SVG renderer strictly blocks inline CSS colors via customdata arrays (XSS filter).
                # We can only use basic structural tags like <b> to differentiate keys.
                s = re.sub(r'(".*?")(?=\s*:)', r'<b>\1</b>', s)
                return s.replace('\n', '<br>').replace('    ', '&nbsp;&nbsp;&nbsp;&nbsp;').replace(' ', '&nbsp;')

            # Format strings for HTML hover
            input_body_str = json.dumps(ch_body, indent=4)
            hover_input = format_hover_json(input_body_str)
            
            hover_output = err_body
            if err_body:
                try:
                    parsed_out = json.loads(err_body)
                    hover_output = format_hover_json(json.dumps(parsed_out, indent=4))
                except Exception:
                    hover_output = hover_output.replace('\n', '<br>').replace('    ', '&nbsp;&nbsp;&nbsp;&nbsp;').replace(' ', '&nbsp;')
            if not hover_output.strip():
                hover_output = "<i>Empty</i>"

            hover_text = f"<b>Task:</b> {task_name}<br>" \
                         f"<b>Dataset:</b> {dataset_name}<br>" \
                         f"<b>Status:</b> {status}<br>" \
                         f"<b>Duration:</b> {end_off - start_off:.3f}s<br><br>" \
                         f"<b>Input Body:</b><br><span style='font-family: monospace; font-size: 15px;'>{hover_input}</span><br><br>" \
                         f"<b>Output Body:</b><br><span style='font-family: monospace; font-size: 15px;'>{hover_output}</span>"
            
            unique_id = f"{dataset_name} | {task_name}"
            
            rows.append({
                "Unique_ID": unique_id,
                "Task": task_name,
                "Dataset": dataset_name,
                "Start": start_dt,
                "Finish": end_dt,
                "Status": status,
                "State": state,
                "Duration (s)": end_off - start_off,
                "Duration Text": f"{int((end_off - start_off) * 1000)} ms",
                "Hover HTML": hover_text
            })
            
            full_data_lookup.append({
                "Unique_ID": unique_id,
                "Task": task_name,
                "Dataset": dataset_name,
                "Status": status,
                "Input_Body": input_body_str,
                "Output_Body": err_body,
                "Duration": end_off - start_off
            })
            
    return pd.DataFrame(rows), full_data_lookup, metadata

primary_name = os.path.basename(primary_file).replace(".json", "") if primary_file else "Primary"
secondary_name = os.path.basename(secondary_file).replace(".json", "") if secondary_file else "Secondary"

df_primary, lookup_primary, meta_primary = load_and_parse_results(primary_file, primary_name)
df_secondary, lookup_secondary, meta_secondary = load_and_parse_results(secondary_file, secondary_name)

if primary_file and meta_primary:
    desc_html = f"<br><strong>Description:</strong> {meta_primary.get('Description')}" if "Description" in meta_primary else ""
    md = f"""
    <div style='background-color: #e6f2ff; padding: 15px; border-radius: 5px; border-left: 5px solid #1f77b4; margin-bottom: 10px;'>
        <strong>System:</strong> {meta_primary.get('System', 'N/A')}<br>
        <strong>Tenant:</strong> {meta_primary.get('Tenant', 'N/A')}<br>
        <strong>Env:</strong> {meta_primary.get('Environment', 'N/A')}<br>
        <strong>Date:</strong> {meta_primary.get('Run Date', 'N/A')}{desc_html}
    </div>
    """
    with primary_container:
        st.markdown(md, unsafe_allow_html=True)
        if meta_primary.get("YAML"):
            with st.expander("Configuration YAML", expanded=False):
                st.code(meta_primary["YAML"], language="yaml")

if secondary_file and meta_secondary:
    desc_html = f"<br><strong>Description:</strong> {meta_secondary.get('Description')}" if "Description" in meta_secondary else ""
    md = f"""
    <div style='background-color: #fff2e6; padding: 15px; border-radius: 5px; border-left: 5px solid #ff7f0e; margin-bottom: 10px;'>
        <strong>System:</strong> {meta_secondary.get('System', 'N/A')}<br>
        <strong>Tenant:</strong> {meta_secondary.get('Tenant', 'N/A')}<br>
        <strong>Env:</strong> {meta_secondary.get('Environment', 'N/A')}<br>
        <strong>Date:</strong> {meta_secondary.get('Run Date', 'N/A')}{desc_html}
    </div>
    """
    with secondary_container:
        st.markdown(md, unsafe_allow_html=True)
        if meta_secondary.get("YAML"):
            with st.expander("Configuration YAML", expanded=False):
                st.code(meta_secondary["YAML"], language="yaml")

df_all = pd.concat([df_primary, df_secondary], ignore_index=True)
lookup_all = lookup_primary + lookup_secondary

if df_all.empty:
    st.info("Please upload at least one JSON result file to visualize.")
    st.stop()

# We map datasets to distinct colors
color_map = {}
if primary_file:
    color_map[primary_name] = "#1f77b4" # Blue
if secondary_file:
    color_map[secondary_name] = "#ff7f0e" # Orange

fig = px.timeline(
    df_all, 
    x_start="Start", 
    x_end="Finish", 
    y="Task", 
    color="Dataset",
    text="Duration Text",
    custom_data=["Hover HTML", "Unique_ID"],
    color_discrete_map=color_map
)

# Calculate x-axis range to cut off below 0 and immediately after the last bar
global_base_time = pd.Timestamp("2020-01-01 00:00:00")
max_finish_time = df_all["Finish"].max()
buffer_sec = max(0.5, (max_finish_time - global_base_time).total_seconds() * 0.05)
x_range_end = max_finish_time + pd.to_timedelta(buffer_sec, unit='s')

# Improve layout
fig.update_yaxes(autorange="reversed") # tasks from top to bottom
fig.update_layout(
    xaxis_title="Time relative to start",
    yaxis_title=None,
    height=max(400, len(df_all["Task"].unique()) * (12 * df_all["Dataset"].nunique()) + 100),
    margin=dict(l=0, r=0, t=80, b=0),
    showlegend=True,
    legend=dict(
        orientation="h", 
        yanchor="bottom", 
        y=1.02, 
        xanchor="left", 
        x=0.0,
        title=dict(text="Dataset: ", side="left", font=dict(size=14)),
        font=dict(size=14)
    ),
    xaxis=dict(
        range=[global_base_time, x_range_end],
        tickformat="%M:%S", # Shows minutes, seconds
        dtick=1000,         # Tick every 1 second (1000 ms)
        showgrid=True,      # Show horizontal grid lines (on the vertical axis)
        gridcolor='lightgray', # Major line light gray
        gridwidth=1.5,      # Force thin rendering
        minor=dict(
            dtick=500,      # Minor tick every 500 ms
            showgrid=False,
            gridcolor='lightgray', # Minor line light gray instead of brown
            gridwidth=1.5      # Force thin rendering
        )
    ),
    yaxis=dict(
        dtick=1             # Force all category labels (channel names) to show when zoomed out
    ),
    barmode="group",
    bargap=0.1,
    hoverlabel=dict(font_size=18, align="left"),
    uniformtext_minsize=12,
    uniformtext_mode='show'
)

fig.update_traces(
    showlegend=True,
    textposition='outside', 
    textfont=dict(size=12, color="black"),
    insidetextfont=dict(size=12),
    outsidetextfont=dict(size=12),
    cliponaxis=False,
    hovertemplate="%{customdata[0]}<extra></extra>"
)

# Add horizontal lines to separate different channels
tasks_ordered = list(df_all["Task"].unique())
for i in range(len(tasks_ordered) - 1):
    current_channel = tasks_ordered[i].rsplit(" (R", 1)[0]
    next_channel = tasks_ordered[i+1].rsplit(" (R", 1)[0]
    if current_channel != next_channel:
        fig.add_hline(y=i + 0.5, line_width=2, line_dash="dash", line_color="gray", opacity=0.8)

event = st.plotly_chart(
    fig, 
    width="stretch", 
    on_select="rerun",
    selection_mode="points",
    config={
        'toImageButtonOptions': {
            'format': 'png',
            'scale': 2
        }
    }
)

points = []
try:
    if isinstance(event, dict) and "selection" in event:
        points = event["selection"].get("points", [])
    else:
        points = getattr(getattr(event, "selection", None), "points", [])
except Exception:
    pass

if points:
    point = points[0]
    if "customdata" in point and len(point["customdata"]) > 1:
        uid = point["customdata"][1]
        for item in lookup_all:
            if item["Unique_ID"] == uid:
                st.divider()
                st.subheader("Selected Request Details")
                st.markdown(f"**Task:** {item['Task']} &nbsp; | &nbsp; **Dataset:** {item['Dataset']} &nbsp; | &nbsp; **Status:** {item['Status']}")
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("**Input Payload:**")
                    st.code(item["Input_Body"], language="json")
                with col2:
                    st.markdown("**Output / Error Body:**")
                    out_body = item["Output_Body"]
                    if out_body:
                        try:
                            parsed = json.loads(out_body)
                            st.code(json.dumps(parsed, indent=4), language="json")
                        except Exception:
                            st.code(out_body, language="json")
                    else:
                        st.info("No output body returned.")
                break



