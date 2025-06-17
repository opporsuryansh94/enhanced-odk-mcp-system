# ODK MCP System

A comprehensive Open Data Kit (ODK) implementation using Model Context Protocol (MCP) with multi-agent architecture, Streamlit UI, and advanced analytics capabilities.

## Project Structure

```
odk_mcp_system/
├── mcps/                   # Model Context Protocol servers
│   ├── form_management/    # Form Definition & Management MCP
│   ├── data_collection/    # Data Collection & Synchronization MCP
│   └── data_aggregation/   # Data Aggregation & Analytics MCP
├── agents/                 # AI agents
│   ├── form_agent.py      # Form Management Agent
│   ├── collection_agent.py # Data Collection Agent
│   ├── aggregation_agent.py # Data Aggregation Agent
│   ├── cleaning_agent.py   # Data Cleaning & Preprocessing Agent
│   ├── descriptive_agent.py # Descriptive Analytics Agent
│   ├── inferential_agent.py # Inferential Statistics Agent
│   ├── exploration_agent.py # Data Exploration Agent
│   └── report_agent.py     # Report Generation Agent
├── ui/                     # Streamlit UI
│   └── streamlit_app.py    # Main Streamlit application
├── docs/                   # Documentation
├── tests/                  # Test files
├── requirements.txt        # Python dependencies
├── docker-compose.yml      # Docker composition for deployment
└── README.md              # This file
```

## Features

- **Project-based data management** with user authentication
- **Form management** with XLSForm support
- **Data collection simulation** with offline capabilities
- **Advanced analytics** including descriptive and inferential statistics
- **Interactive data exploration** and visualization
- **Automated report generation**
- **Flexible deployment** (local desktop, VM, AI tool integration)
- **Baserow integration** for enhanced data storage
- **Comprehensive security** with RBAC and data encryption

## Quick Start

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Start the MCP servers:
   ```bash
   # Start each MCP server in separate terminals
   cd mcps/form_management && python app.py
   cd mcps/data_collection && python app.py
   cd mcps/data_aggregation && python app.py
   ```

3. Launch the Streamlit UI:
   ```bash
   cd ui && streamlit run streamlit_app.py
   ```

## Documentation

See the `docs/` directory for comprehensive documentation including:
- Implementation guide
- API documentation
- Deployment instructions
- User manual

## License

MIT License

