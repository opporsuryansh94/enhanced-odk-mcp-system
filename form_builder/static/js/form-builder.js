// Smart Form Builder JavaScript

class SmartFormBuilder {
    constructor() {
        this.currentForm = {
            id: null,
            title: 'Untitled Form',
            description: '',
            fields: [],
            settings: {
                language: 'en',
                theme: 'default',
                auto_save: true
            }
        };
        
        this.selectedField = null;
        this.components = {};
        this.templates = {};
        this.autoSaveInterval = null;
        
        this.init();
    }
    
    async init() {
        await this.loadComponents();
        await this.loadTemplates();
        this.setupEventListeners();
        this.setupDragAndDrop();
        this.setupAutoSave();
        this.renderComponents();
    }
    
    async loadComponents() {
        try {
            const response = await fetch('/api/components');
            const data = await response.json();
            
            if (data.status === 'success') {
                this.components = data.components;
            }
        } catch (error) {
            console.error('Error loading components:', error);
            this.showError('Failed to load form components');
        }
    }
    
    async loadTemplates() {
        try {
            const response = await fetch('/api/templates');
            const data = await response.json();
            
            if (data.status === 'success') {
                this.templates = data.templates;
            }
        } catch (error) {
            console.error('Error loading templates:', error);
        }
    }
    
    setupEventListeners() {
        // Form title and description
        document.getElementById('formTitle').addEventListener('input', (e) => {
            this.currentForm.title = e.target.value;
            this.triggerAutoSave();
        });
        
        document.getElementById('formDescription').addEventListener('input', (e) => {
            this.currentForm.description = e.target.value;
            this.triggerAutoSave();
        });
        
        // Auto-save toggle
        document.getElementById('autoSave').addEventListener('change', (e) => {
            this.currentForm.settings.auto_save = e.target.checked;
            if (e.target.checked) {
                this.setupAutoSave();
            } else {
                this.clearAutoSave();
            }
        });
        
        // Component search
        document.getElementById('componentSearch').addEventListener('input', (e) => {
            this.filterComponents(e.target.value);
        });
        
        // CSV file input
        document.getElementById('csvFileInput').addEventListener('change', (e) => {
            if (e.target.files.length > 0) {
                this.analyzeCsv(e.target.files[0]);
            }
        });
        
        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if (e.ctrlKey || e.metaKey) {
                switch (e.key) {
                    case 's':
                        e.preventDefault();
                        this.saveForm();
                        break;
                    case 'p':
                        e.preventDefault();
                        this.previewForm();
                        break;
                    case 'z':
                        e.preventDefault();
                        this.undo();
                        break;
                    case 'y':
                        e.preventDefault();
                        this.redo();
                        break;
                }
            }
            
            if (e.key === 'Delete' && this.selectedField) {
                this.deleteField(this.selectedField.id);
            }
        });
    }
    
    setupDragAndDrop() {
        const container = document.getElementById('formFieldsContainer');
        
        // Make form fields sortable
        this.sortable = Sortable.create(container, {
            animation: 150,
            ghostClass: 'sortable-ghost',
            chosenClass: 'sortable-chosen',
            dragClass: 'sortable-drag',
            handle: '.drag-handle',
            onEnd: (evt) => {
                this.reorderFields(evt.oldIndex, evt.newIndex);
            }
        });
        
        // Drop zone for new components
        container.addEventListener('dragover', (e) => {
            e.preventDefault();
            container.classList.add('drag-over');
        });
        
        container.addEventListener('dragleave', (e) => {
            if (!container.contains(e.relatedTarget)) {
                container.classList.remove('drag-over');
            }
        });
        
        container.addEventListener('drop', (e) => {
            e.preventDefault();
            container.classList.remove('drag-over');
            
            const componentType = e.dataTransfer.getData('text/plain');
            if (componentType) {
                this.addFieldFromComponent(componentType);
            }
        });
    }
    
    setupAutoSave() {
        if (this.autoSaveInterval) {
            clearInterval(this.autoSaveInterval);
        }
        
        if (this.currentForm.settings.auto_save) {
            this.autoSaveInterval = setInterval(() => {
                this.saveForm(true); // Silent save
            }, 30000); // Save every 30 seconds
        }
    }
    
    clearAutoSave() {
        if (this.autoSaveInterval) {
            clearInterval(this.autoSaveInterval);
            this.autoSaveInterval = null;
        }
    }
    
    triggerAutoSave() {
        if (this.currentForm.settings.auto_save) {
            clearTimeout(this.autoSaveTimeout);
            this.autoSaveTimeout = setTimeout(() => {
                this.saveForm(true);
            }, 2000); // Save 2 seconds after last change
        }
    }
    
    renderComponents() {
        this.renderComponentCategory('basic', 'basicComponentsList');
        this.renderComponentCategory('advanced', 'advancedComponentsList');
        this.renderComponentCategory('layout', 'layoutComponentsList');
    }
    
    renderComponentCategory(category, containerId) {
        const container = document.getElementById(containerId);
        const components = this.components[category] || [];
        
        container.innerHTML = '';
        
        components.forEach(component => {
            const componentElement = this.createComponentElement(component);
            container.appendChild(componentElement);
        });
    }
    
    createComponentElement(component) {
        const div = document.createElement('div');
        div.className = 'component-item';
        div.draggable = true;
        div.dataset.componentType = component.type;
        
        div.innerHTML = `
            <i class="material-icons">${component.icon}</i>
            <span class="component-label">${component.label}</span>
        `;
        
        div.addEventListener('dragstart', (e) => {
            e.dataTransfer.setData('text/plain', component.type);
        });
        
        div.addEventListener('click', () => {
            this.addFieldFromComponent(component.type);
        });
        
        return div;
    }
    
    filterComponents(searchTerm) {
        const term = searchTerm.toLowerCase();
        const componentItems = document.querySelectorAll('.component-item');
        
        componentItems.forEach(item => {
            const label = item.querySelector('.component-label').textContent.toLowerCase();
            const type = item.dataset.componentType.toLowerCase();
            
            if (label.includes(term) || type.includes(term)) {
                item.style.display = 'flex';
            } else {
                item.style.display = 'none';
            }
        });
    }
    
    addFieldFromComponent(componentType) {
        const component = this.findComponent(componentType);
        if (!component) return;
        
        const field = {
            id: this.generateId(),
            type: componentType,
            name: `field_${this.currentForm.fields.length + 1}`,
            label: component.label,
            hint: '',
            required: false,
            properties: this.getDefaultProperties(componentType),
            validation: {},
            position: this.currentForm.fields.length
        };
        
        this.currentForm.fields.push(field);
        this.renderFormFields();
        this.selectField(field.id);
        this.triggerAutoSave();
        
        // Hide empty state
        document.getElementById('emptyState').style.display = 'none';
    }
    
    findComponent(type) {
        for (const category in this.components) {
            const component = this.components[category].find(c => c.type === type);
            if (component) return component;
        }
        return null;
    }
    
    getDefaultProperties(type) {
        const defaults = {
            text: { maxlength: '', placeholder: '' },
            number: { min: '', max: '', step: '1' },
            date: { min: '', max: '' },
            time: { min: '', max: '' },
            select_one: { options: [{ value: 'option1', label: 'Option 1' }] },
            select_multiple: { options: [{ value: 'option1', label: 'Option 1' }] },
            radio: { options: [{ value: 'option1', label: 'Option 1' }] },
            checkbox: { options: [{ value: 'option1', label: 'Option 1' }] },
            geopoint: { accuracy: '5' },
            image: { max_pixels: '1024' },
            audio: { quality: 'normal' },
            rating: { min: 1, max: 5, step: 1 }
        };
        
        return defaults[type] || {};
    }
    
    renderFormFields() {
        const container = document.getElementById('formFieldsContainer');
        const emptyState = document.getElementById('emptyState');
        
        if (this.currentForm.fields.length === 0) {
            emptyState.style.display = 'block';
            return;
        }
        
        emptyState.style.display = 'none';
        
        // Clear existing fields (except empty state)
        const existingFields = container.querySelectorAll('.form-field-wrapper');
        existingFields.forEach(field => field.remove());
        
        this.currentForm.fields.forEach(field => {
            const fieldElement = this.createFieldElement(field);
            container.appendChild(fieldElement);
        });
    }
    
    createFieldElement(field) {
        const wrapper = document.createElement('div');
        wrapper.className = 'form-field-wrapper';
        wrapper.dataset.fieldId = field.id;
        
        wrapper.innerHTML = `
            <div class="drag-handle">
                <i class="fas fa-grip-vertical"></i>
            </div>
            <div class="field-controls">
                <button class="field-control-btn" onclick="formBuilder.editField('${field.id}')" title="Edit">
                    <i class="fas fa-edit"></i>
                </button>
                <button class="field-control-btn" onclick="formBuilder.duplicateField('${field.id}')" title="Duplicate">
                    <i class="fas fa-copy"></i>
                </button>
                <button class="field-control-btn delete" onclick="formBuilder.deleteField('${field.id}')" title="Delete">
                    <i class="fas fa-trash"></i>
                </button>
            </div>
            <div class="field-preview">
                ${this.renderFieldPreview(field)}
            </div>
        `;
        
        wrapper.addEventListener('click', (e) => {
            if (!e.target.closest('.field-controls')) {
                this.selectField(field.id);
            }
        });
        
        return wrapper;
    }
    
    renderFieldPreview(field) {
        const requiredMark = field.required ? '<span class="required-mark">*</span>' : '';
        let preview = `
            <div class="field-label">${field.label}${requiredMark}</div>
        `;
        
        if (field.hint) {
            preview += `<div class="field-hint">${field.hint}</div>`;
        }
        
        switch (field.type) {
            case 'text':
                preview += `<input type="text" class="field-input" placeholder="${field.properties.placeholder || ''}" disabled>`;
                break;
                
            case 'number':
                preview += `<input type="number" class="field-input" min="${field.properties.min || ''}" max="${field.properties.max || ''}" disabled>`;
                break;
                
            case 'date':
                preview += `<input type="date" class="field-input" disabled>`;
                break;
                
            case 'time':
                preview += `<input type="time" class="field-input" disabled>`;
                break;
                
            case 'select_one':
                preview += `<select class="field-input" disabled>`;
                preview += `<option>Select an option</option>`;
                (field.properties.options || []).forEach(option => {
                    preview += `<option value="${option.value}">${option.label}</option>`;
                });
                preview += `</select>`;
                break;
                
            case 'radio':
                preview += `<div class="field-options">`;
                (field.properties.options || []).forEach(option => {
                    preview += `
                        <div class="field-option">
                            <input type="radio" name="${field.name}" value="${option.value}" disabled>
                            <label>${option.label}</label>
                        </div>
                    `;
                });
                preview += `</div>`;
                break;
                
            case 'checkbox':
            case 'select_multiple':
                preview += `<div class="field-options">`;
                (field.properties.options || []).forEach(option => {
                    preview += `
                        <div class="field-option">
                            <input type="checkbox" value="${option.value}" disabled>
                            <label>${option.label}</label>
                        </div>
                    `;
                });
                preview += `</div>`;
                break;
                
            case 'geopoint':
                preview += `<input type="text" class="field-input" placeholder="GPS coordinates will be captured" disabled>`;
                break;
                
            case 'image':
                preview += `<div class="field-input" style="padding: 20px; text-align: center; background: #f8f9fa;">
                    <i class="fas fa-camera fa-2x text-muted"></i><br>
                    <small class="text-muted">Image will be captured</small>
                </div>`;
                break;
                
            case 'audio':
                preview += `<div class="field-input" style="padding: 20px; text-align: center; background: #f8f9fa;">
                    <i class="fas fa-microphone fa-2x text-muted"></i><br>
                    <small class="text-muted">Audio will be recorded</small>
                </div>`;
                break;
                
            case 'rating':
                preview += `<div class="field-options" style="flex-direction: row;">`;
                const max = field.properties.max || 5;
                for (let i = 1; i <= max; i++) {
                    preview += `<i class="fas fa-star text-muted" style="margin-right: 4px;"></i>`;
                }
                preview += `</div>`;
                break;
                
            default:
                preview += `<input type="text" class="field-input" disabled>`;
        }
        
        return preview;
    }
    
    selectField(fieldId) {
        // Remove previous selection
        document.querySelectorAll('.form-field-wrapper.selected').forEach(el => {
            el.classList.remove('selected');
        });
        
        // Select new field
        const fieldElement = document.querySelector(`[data-field-id="${fieldId}"]`);
        if (fieldElement) {
            fieldElement.classList.add('selected');
            this.selectedField = this.currentForm.fields.find(f => f.id === fieldId);
            this.renderProperties();
        }
    }
    
    renderProperties() {
        const container = document.getElementById('propertiesContent');
        
        if (!this.selectedField) {
            container.innerHTML = `
                <div class="text-center text-muted py-4">
                    <i class="fas fa-mouse-pointer fa-2x mb-2"></i>
                    <p>Select a field to edit its properties</p>
                </div>
            `;
            return;
        }
        
        const field = this.selectedField;
        
        container.innerHTML = `
            <div class="property-group">
                <h6><i class="fas fa-info-circle me-2"></i>Basic Properties</h6>
                
                <div class="property-row">
                    <label class="form-label">Field Name</label>
                    <input type="text" class="form-control" id="prop-name" value="${field.name}">
                </div>
                
                <div class="property-row">
                    <label class="form-label">Label</label>
                    <input type="text" class="form-control" id="prop-label" value="${field.label}">
                </div>
                
                <div class="property-row">
                    <label class="form-label">Hint Text</label>
                    <input type="text" class="form-control" id="prop-hint" value="${field.hint}">
                </div>
                
                <div class="property-row">
                    <div class="form-check">
                        <input class="form-check-input" type="checkbox" id="prop-required" ${field.required ? 'checked' : ''}>
                        <label class="form-check-label" for="prop-required">
                            Required Field
                        </label>
                    </div>
                </div>
            </div>
            
            ${this.renderFieldSpecificProperties(field)}
            
            <div class="property-group">
                <h6><i class="fas fa-shield-alt me-2"></i>Validation</h6>
                
                <div class="property-row">
                    <label class="form-label">Constraint Expression</label>
                    <input type="text" class="form-control" id="prop-constraint" value="${field.validation.constraint || ''}" placeholder="e.g., . > 0">
                    <small class="text-muted">XLSForm constraint expression</small>
                </div>
                
                <div class="property-row">
                    <label class="form-label">Constraint Message</label>
                    <input type="text" class="form-control" id="prop-constraint-message" value="${field.validation.constraint_message || ''}" placeholder="Error message">
                </div>
                
                <div class="property-row">
                    <label class="form-label">Relevant Expression</label>
                    <input type="text" class="form-control" id="prop-relevant" value="${field.validation.relevant || ''}" placeholder="e.g., \${other_field} = 'yes'">
                    <small class="text-muted">Show this field only when condition is true</small>
                </div>
            </div>
        `;
        
        this.setupPropertyListeners();
    }
    
    renderFieldSpecificProperties(field) {
        let html = '<div class="property-group"><h6><i class="fas fa-cog me-2"></i>Field Properties</h6>';
        
        switch (field.type) {
            case 'text':
                html += `
                    <div class="property-row">
                        <label class="form-label">Placeholder</label>
                        <input type="text" class="form-control" id="prop-placeholder" value="${field.properties.placeholder || ''}">
                    </div>
                    <div class="property-row">
                        <label class="form-label">Max Length</label>
                        <input type="number" class="form-control" id="prop-maxlength" value="${field.properties.maxlength || ''}">
                    </div>
                `;
                break;
                
            case 'number':
                html += `
                    <div class="property-row">
                        <label class="form-label">Minimum Value</label>
                        <input type="number" class="form-control" id="prop-min" value="${field.properties.min || ''}">
                    </div>
                    <div class="property-row">
                        <label class="form-label">Maximum Value</label>
                        <input type="number" class="form-control" id="prop-max" value="${field.properties.max || ''}">
                    </div>
                    <div class="property-row">
                        <label class="form-label">Step</label>
                        <input type="number" class="form-control" id="prop-step" value="${field.properties.step || '1'}">
                    </div>
                `;
                break;
                
            case 'date':
            case 'time':
                html += `
                    <div class="property-row">
                        <label class="form-label">Minimum ${field.type === 'date' ? 'Date' : 'Time'}</label>
                        <input type="${field.type}" class="form-control" id="prop-min" value="${field.properties.min || ''}">
                    </div>
                    <div class="property-row">
                        <label class="form-label">Maximum ${field.type === 'date' ? 'Date' : 'Time'}</label>
                        <input type="${field.type}" class="form-control" id="prop-max" value="${field.properties.max || ''}">
                    </div>
                `;
                break;
                
            case 'select_one':
            case 'select_multiple':
            case 'radio':
            case 'checkbox':
                html += `
                    <div class="property-row">
                        <label class="form-label">Options</label>
                        <div class="options-editor" id="optionsEditor">
                            ${this.renderOptionsEditor(field.properties.options || [])}
                        </div>
                    </div>
                `;
                break;
                
            case 'rating':
                html += `
                    <div class="property-row">
                        <label class="form-label">Minimum Rating</label>
                        <input type="number" class="form-control" id="prop-min" value="${field.properties.min || '1'}">
                    </div>
                    <div class="property-row">
                        <label class="form-label">Maximum Rating</label>
                        <input type="number" class="form-control" id="prop-max" value="${field.properties.max || '5'}">
                    </div>
                    <div class="property-row">
                        <label class="form-label">Step</label>
                        <input type="number" class="form-control" id="prop-step" value="${field.properties.step || '1'}">
                    </div>
                `;
                break;
        }
        
        html += '</div>';
        return html;
    }
    
    renderOptionsEditor(options) {
        let html = '';
        
        options.forEach((option, index) => {
            html += `
                <div class="option-item" data-index="${index}">
                    <input type="text" class="form-control" placeholder="Value" value="${option.value}" onchange="formBuilder.updateOptionValue(${index}, this.value)">
                    <input type="text" class="form-control" placeholder="Label" value="${option.label}" onchange="formBuilder.updateOptionLabel(${index}, this.value)">
                    <button type="button" class="btn btn-outline-danger btn-sm" onclick="formBuilder.removeOption(${index})">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            `;
        });
        
        html += `
            <button type="button" class="btn btn-outline-primary btn-sm add-option-btn" onclick="formBuilder.addOption()">
                <i class="fas fa-plus me-1"></i>Add Option
            </button>
        `;
        
        return html;
    }
    
    setupPropertyListeners() {
        const propertyInputs = document.querySelectorAll('#propertiesContent input, #propertiesContent select, #propertiesContent textarea');
        
        propertyInputs.forEach(input => {
            input.addEventListener('input', () => {
                this.updateFieldProperty(input);
            });
        });
    }
    
    updateFieldProperty(input) {
        if (!this.selectedField) return;
        
        const property = input.id.replace('prop-', '');
        let value = input.type === 'checkbox' ? input.checked : input.value;
        
        // Convert numeric values
        if (input.type === 'number' && value !== '') {
            value = parseFloat(value);
        }
        
        // Update field property
        if (['name', 'label', 'hint', 'required'].includes(property)) {
            this.selectedField[property] = value;
        } else if (['constraint', 'constraint_message', 'relevant'].includes(property)) {
            this.selectedField.validation[property] = value;
        } else {
            this.selectedField.properties[property] = value;
        }
        
        // Re-render the field preview
        this.renderFormFields();
        this.selectField(this.selectedField.id);
        this.triggerAutoSave();
    }
    
    updateOptionValue(index, value) {
        if (!this.selectedField || !this.selectedField.properties.options) return;
        
        this.selectedField.properties.options[index].value = value;
        this.renderFormFields();
        this.selectField(this.selectedField.id);
        this.triggerAutoSave();
    }
    
    updateOptionLabel(index, label) {
        if (!this.selectedField || !this.selectedField.properties.options) return;
        
        this.selectedField.properties.options[index].label = label;
        this.renderFormFields();
        this.selectField(this.selectedField.id);
        this.triggerAutoSave();
    }
    
    addOption() {
        if (!this.selectedField || !this.selectedField.properties.options) return;
        
        const newOption = {
            value: `option${this.selectedField.properties.options.length + 1}`,
            label: `Option ${this.selectedField.properties.options.length + 1}`
        };
        
        this.selectedField.properties.options.push(newOption);
        this.renderProperties();
        this.renderFormFields();
        this.selectField(this.selectedField.id);
        this.triggerAutoSave();
    }
    
    removeOption(index) {
        if (!this.selectedField || !this.selectedField.properties.options) return;
        
        this.selectedField.properties.options.splice(index, 1);
        this.renderProperties();
        this.renderFormFields();
        this.selectField(this.selectedField.id);
        this.triggerAutoSave();
    }
    
    editField(fieldId) {
        this.selectField(fieldId);
    }
    
    duplicateField(fieldId) {
        const field = this.currentForm.fields.find(f => f.id === fieldId);
        if (!field) return;
        
        const duplicatedField = {
            ...JSON.parse(JSON.stringify(field)),
            id: this.generateId(),
            name: `${field.name}_copy`,
            position: this.currentForm.fields.length
        };
        
        this.currentForm.fields.push(duplicatedField);
        this.renderFormFields();
        this.selectField(duplicatedField.id);
        this.triggerAutoSave();
    }
    
    deleteField(fieldId) {
        const index = this.currentForm.fields.findIndex(f => f.id === fieldId);
        if (index === -1) return;
        
        this.currentForm.fields.splice(index, 1);
        
        // Update positions
        this.currentForm.fields.forEach((field, i) => {
            field.position = i;
        });
        
        this.renderFormFields();
        this.selectedField = null;
        this.renderProperties();
        this.triggerAutoSave();
    }
    
    reorderFields(oldIndex, newIndex) {
        const field = this.currentForm.fields.splice(oldIndex, 1)[0];
        this.currentForm.fields.splice(newIndex, 0, field);
        
        // Update positions
        this.currentForm.fields.forEach((field, i) => {
            field.position = i;
        });
        
        this.triggerAutoSave();
    }
    
    async saveForm(silent = false) {
        try {
            if (!silent) {
                this.showLoading('Saving form...');
            }
            
            let response;
            if (this.currentForm.id) {
                // Update existing form
                response = await fetch(`/api/form/${this.currentForm.id}`, {
                    method: 'PUT',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(this.currentForm)
                });
            } else {
                // Create new form
                response = await fetch('/api/form/new', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(this.currentForm)
                });
            }
            
            const data = await response.json();
            
            if (data.status === 'success') {
                if (data.form_id) {
                    this.currentForm.id = data.form_id;
                }
                
                if (!silent) {
                    this.showSuccess('Form saved successfully');
                }
            } else {
                throw new Error(data.message || 'Failed to save form');
            }
        } catch (error) {
            console.error('Error saving form:', error);
            this.showError('Failed to save form: ' + error.message);
        } finally {
            this.hideLoading();
        }
    }
    
    async previewForm() {
        try {
            this.showLoading('Generating preview...');
            
            if (!this.currentForm.id) {
                await this.saveForm(true);
            }
            
            const response = await fetch(`/api/form/${this.currentForm.id}/preview`);
            const data = await response.json();
            
            if (data.status === 'success') {
                document.getElementById('previewContent').innerHTML = data.preview_html;
                const modal = new bootstrap.Modal(document.getElementById('previewModal'));
                modal.show();
            } else {
                throw new Error(data.message || 'Failed to generate preview');
            }
        } catch (error) {
            console.error('Error generating preview:', error);
            this.showError('Failed to generate preview: ' + error.message);
        } finally {
            this.hideLoading();
        }
    }
    
    async exportForm() {
        const modal = new bootstrap.Modal(document.getElementById('exportModal'));
        modal.show();
    }
    
    async downloadForm() {
        try {
            const format = document.getElementById('exportFormat').value;
            const fileName = document.getElementById('exportFileName').value;
            
            if (!this.currentForm.id) {
                await this.saveForm(true);
            }
            
            this.showLoading('Exporting form...');
            
            let url;
            switch (format) {
                case 'xlsform':
                    url = `/api/form/${this.currentForm.id}/export/xlsform`;
                    break;
                case 'json':
                    url = `/api/form/${this.currentForm.id}/export/json`;
                    break;
                case 'xml':
                    url = `/api/form/${this.currentForm.id}/export/xml`;
                    break;
                default:
                    throw new Error('Invalid export format');
            }
            
            const response = await fetch(url);
            
            if (response.ok) {
                const blob = await response.blob();
                const downloadUrl = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = downloadUrl;
                a.download = `${fileName}.${format === 'xlsform' ? 'xlsx' : format}`;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                window.URL.revokeObjectURL(downloadUrl);
                
                this.showSuccess('Form exported successfully');
                bootstrap.Modal.getInstance(document.getElementById('exportModal')).hide();
            } else {
                throw new Error('Failed to export form');
            }
        } catch (error) {
            console.error('Error exporting form:', error);
            this.showError('Failed to export form: ' + error.message);
        } finally {
            this.hideLoading();
        }
    }
    
    async getAiSuggestions() {
        try {
            this.showLoading('Getting AI suggestions...');
            
            const response = await fetch('/api/ai/suggestions', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    description: this.currentForm.description,
                    current_fields: this.currentForm.fields,
                    user_plan: 'pro' // This would come from user session
                })
            });
            
            const data = await response.json();
            
            if (data.status === 'success') {
                this.renderAiSuggestions(data.recommendations);
                document.getElementById('aiSuggestionsPanel').style.display = 'block';
            } else {
                throw new Error(data.message || 'Failed to get AI suggestions');
            }
        } catch (error) {
            console.error('Error getting AI suggestions:', error);
            this.showError('Failed to get AI suggestions: ' + error.message);
        } finally {
            this.hideLoading();
        }
    }
    
    renderAiSuggestions(suggestions) {
        const container = document.getElementById('aiSuggestionsContent');
        
        if (!suggestions || suggestions.length === 0) {
            container.innerHTML = '<p class="text-muted">No suggestions available</p>';
            return;
        }
        
        let html = '';
        suggestions.forEach(suggestion => {
            html += `
                <div class="ai-suggestion-item" onclick="formBuilder.applySuggestion('${suggestion.form_id}')">
                    <div class="suggestion-title">${suggestion.title}</div>
                    <div class="suggestion-description">${suggestion.description}</div>
                    <div class="suggestion-confidence">Relevance: ${Math.round(suggestion.relevance_score * 100)}%</div>
                </div>
            `;
        });
        
        container.innerHTML = html;
    }
    
    async applySuggestion(suggestionId) {
        // Implementation for applying AI suggestions
        console.log('Applying suggestion:', suggestionId);
    }
    
    async analyzeCsv(file) {
        try {
            this.showLoading('Analyzing CSV file...');
            
            const formData = new FormData();
            formData.append('file', file);
            
            const response = await fetch('/api/csv/analyze', {
                method: 'POST',
                body: formData
            });
            
            const data = await response.json();
            
            if (data.status === 'success') {
                this.applyCsvAnalysis(data);
                this.showSuccess('CSV analysis complete. Form structure generated!');
            } else {
                throw new Error(data.message || 'Failed to analyze CSV');
            }
        } catch (error) {
            console.error('Error analyzing CSV:', error);
            this.showError('Failed to analyze CSV: ' + error.message);
        } finally {
            this.hideLoading();
        }
    }
    
    applyCsvAnalysis(analysis) {
        // Clear existing fields
        this.currentForm.fields = [];
        
        // Add fields from CSV analysis
        analysis.suggested_fields.forEach((fieldData, index) => {
            const field = {
                id: this.generateId(),
                type: fieldData.suggested_type,
                name: fieldData.name,
                label: fieldData.label,
                hint: '',
                required: fieldData.required,
                properties: fieldData.choices ? { options: fieldData.choices } : {},
                validation: fieldData.validation || {},
                position: index
            };
            
            this.currentForm.fields.push(field);
        });
        
        this.renderFormFields();
        this.triggerAutoSave();
    }
    
    async loadTemplate(templateId) {
        try {
            this.showLoading('Loading template...');
            
            const response = await fetch(`/api/template/${templateId}`);
            const data = await response.json();
            
            if (data.status === 'success') {
                const template = data.template;
                
                // Apply template to current form
                this.currentForm.title = template.title;
                this.currentForm.description = template.description;
                this.currentForm.fields = template.fields.map((field, index) => ({
                    ...field,
                    id: this.generateId(),
                    position: index
                }));
                
                // Update UI
                document.getElementById('formTitle').value = this.currentForm.title;
                document.getElementById('formDescription').value = this.currentForm.description;
                
                this.renderFormFields();
                this.triggerAutoSave();
                
                this.showSuccess(`Template "${template.title}" loaded successfully`);
            } else {
                throw new Error(data.message || 'Failed to load template');
            }
        } catch (error) {
            console.error('Error loading template:', error);
            this.showError('Failed to load template: ' + error.message);
        } finally {
            this.hideLoading();
        }
    }
    
    generateId() {
        return 'field_' + Math.random().toString(36).substr(2, 9);
    }
    
    showLoading(message = 'Loading...') {
        // Implementation for showing loading state
        console.log('Loading:', message);
    }
    
    hideLoading() {
        // Implementation for hiding loading state
        console.log('Loading complete');
    }
    
    showSuccess(message) {
        this.showNotification(message, 'success');
    }
    
    showError(message) {
        this.showNotification(message, 'error');
    }
    
    showNotification(message, type) {
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `${type}-message fade-in`;
        notification.innerHTML = `
            <i class="fas fa-${type === 'success' ? 'check-circle' : 'exclamation-circle'} me-2"></i>
            ${message}
        `;
        
        // Add to page
        document.body.appendChild(notification);
        
        // Position notification
        notification.style.position = 'fixed';
        notification.style.top = '20px';
        notification.style.right = '20px';
        notification.style.zIndex = '9999';
        notification.style.maxWidth = '400px';
        
        // Auto remove after 5 seconds
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 5000);
    }
}

// Global functions for HTML onclick handlers
let formBuilder;

function saveForm() {
    formBuilder.saveForm();
}

function previewForm() {
    formBuilder.previewForm();
}

function exportForm() {
    formBuilder.exportForm();
}

function downloadForm() {
    formBuilder.downloadForm();
}

function getAiSuggestions() {
    formBuilder.getAiSuggestions();
}

function analyzeCsv() {
    const fileInput = document.getElementById('csvFileInput');
    if (fileInput.files.length > 0) {
        formBuilder.analyzeCsv(fileInput.files[0]);
    }
}

function loadTemplate(templateId) {
    formBuilder.loadTemplate(templateId);
}

function showAddFieldModal() {
    const modal = new bootstrap.Modal(document.getElementById('addFieldModal'));
    modal.show();
}

function addNewField() {
    const type = document.getElementById('newFieldType').value;
    const name = document.getElementById('newFieldName').value || `field_${formBuilder.currentForm.fields.length + 1}`;
    const label = document.getElementById('newFieldLabel').value || 'New Field';
    const hint = document.getElementById('newFieldHint').value;
    const required = document.getElementById('newFieldRequired').checked;
    
    const field = {
        id: formBuilder.generateId(),
        type: type,
        name: name,
        label: label,
        hint: hint,
        required: required,
        properties: formBuilder.getDefaultProperties(type),
        validation: {},
        position: formBuilder.currentForm.fields.length
    };
    
    formBuilder.currentForm.fields.push(field);
    formBuilder.renderFormFields();
    formBuilder.selectField(field.id);
    formBuilder.triggerAutoSave();
    
    // Hide modal
    bootstrap.Modal.getInstance(document.getElementById('addFieldModal')).hide();
    
    // Clear form
    document.getElementById('newFieldType').value = 'text';
    document.getElementById('newFieldName').value = '';
    document.getElementById('newFieldLabel').value = '';
    document.getElementById('newFieldHint').value = '';
    document.getElementById('newFieldRequired').checked = false;
    
    // Hide empty state
    document.getElementById('emptyState').style.display = 'none';
}

// Initialize form builder when page loads
document.addEventListener('DOMContentLoaded', () => {
    formBuilder = new SmartFormBuilder();
});

