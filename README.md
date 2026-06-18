# MGEN API Test Results Comparison Visualizer

This Streamlit application provides an interactive Gantt chart visualization for comparing MGEN API test results. It parses JSON result files and displays the sequence, duration, and status of API requests across different channels.

## Features

- **Interactive Gantt Chart**: Visualizes API test execution timelines using Plotly.
- **Detailed Request Inspection**: Click on any task bar in the chart to view the full request input payload, output/error body, and status details.
- **Side-by-Side Comparison**: Load a Primary and Secondary JSON result set to visually compare performance and test results between different runs (e.g., different environments, tenants, or code versions).
- **Metadata Display**: Automatically extracts and displays run metadata, including System, Tenant, Environment, Run Date, and Configuration YAML.
- **High-Quality Export**: The chart is optimized for high-resolution PNG exports without text overlapping.

## Setup & Running

1. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Place your test result JSON files in the `results/` directory relative to the script.
3. Run the Streamlit application:
   ```bash
   streamlit run streamlit_app.py
   ```

## URL Link Sharing (Pre-loading Datasets)

You can easily share a specific comparison view with colleagues by appending URL query parameters to the Streamlit app URL. The app will automatically read these parameters and pre-select the correct datasets in the dropdown menus.

### URL Parameters
- `primary`: The filename of the primary dataset to load.
- `secondary`: The filename of the secondary dataset to load.

**Examples:**

*Load specific datasets for both primary and secondary views:*
```text
http://localhost:8502/?primary=260616_PRODAPP,VALIDAPP_PROD.json&secondary=260616_PRODAPP,VALIDAPP_1.json
```

*The `.json` extension is optional. You can just use the base names:*
```text
http://localhost:8502/?primary=260616_PRODAPP,VALIDAPP_PROD&secondary=260616_PRODAPP,VALIDAPP_1
```

*Load only a primary dataset:*
```text
http://localhost:8502/?primary=my_test_run.json
```

*Whenever you select new datasets using the sidebar dropdowns in the app, the URL in your browser's address bar will automatically update to reflect your choices. You can simply copy and paste that URL to share your exact view!*
