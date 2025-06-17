# AI Modules for ODK MCP System

This directory contains the AI-powered intelligence layer for the ODK MCP System. These modules provide advanced capabilities such as anomaly detection, automatic insights, and smart form recommendations.

## Directory Structure

- `anomaly_detection/`: AI models and utilities for detecting anomalies in form submissions
- `data_insights/`: Automatic data summarization and insight generation
- `form_recommendations/`: Smart skip-logic and form structure recommendations
- `nlp/`: Natural Language Processing utilities for text analysis and multilingual support
- `rag/`: Retrieval-Augmented Generation system for the virtual assistant
- `utils/`: Shared utilities and helper functions

## Integration Points

These AI modules integrate with the core MCP system at several key points:

1. **Form Management MCP**: For smart form structure recommendations
2. **Data Collection MCP**: For real-time anomaly detection during submission
3. **Data Aggregation MCP**: For automatic insights and report generation
4. **Virtual Assistant**: For providing intelligent responses to user queries

## Dependencies

- scikit-learn
- transformers
- tensorflow or pytorch (based on deployment requirements)
- langchain (for RAG implementation)
- sentence-transformers
- openai (optional, for API integration)
- anthropic (optional, for Claude API integration)

## Configuration

AI module configuration is stored in `config.py` files within each module directory. Global settings are in the root `config.py` file.

