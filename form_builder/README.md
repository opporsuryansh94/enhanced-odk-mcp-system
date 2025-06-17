# Smart Drag-and-Drop Form Builder for ODK MCP System

This directory contains the smart form builder component for the ODK MCP System, providing a user-friendly interface for creating and managing forms.

## Directory Structure

- `api/`: RESTful API endpoints for form builder operations
- `frontend/`: React-based frontend for the drag-and-drop interface
- `models/`: Data models for form components and templates
- `services/`: Business logic for form generation and validation
- `ai_integration/`: Integration with AI modules for smart suggestions
- `utils/`: Utility functions for form building

## Features

- Drag-and-drop interface for form creation
- Real-time form preview
- XLSForm and JSON schema auto-generation
- Error detection and validation
- Form templates and component library
- CSV upload with AI-powered field structure suggestions
- Form versioning and history

## Form Components

The form builder supports the following component types:

1. **Basic Components**:
   - Text input
   - Number input
   - Date/time picker
   - Select dropdown
   - Multi-select
   - Radio buttons
   - Checkboxes

2. **Advanced Components**:
   - GPS location
   - Image capture
   - Audio recording
   - Signature capture
   - Barcode/QR scanner
   - Rating scale
   - Matrix/grid questions

3. **Layout Components**:
   - Section dividers
   - Page breaks
   - Repeating groups
   - Conditional groups

## Integration Points

The form builder integrates with other components of the ODK MCP System:

1. **Form Management MCP**: To store and manage created forms
2. **AI Modules**: For smart field suggestions and form structure recommendations
3. **Subscription System**: To enforce form creation limits based on subscription tier

## Technologies

- React.js for the frontend interface
- react-dnd for drag-and-drop functionality
- Redux for state management
- Flask for backend API
- AI integration for smart suggestions

