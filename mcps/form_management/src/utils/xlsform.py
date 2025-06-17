import pandas as pd
import json
import xml.etree.ElementTree as ET
from xml.dom import minidom
import uuid
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

class XLSFormProcessor:
    """Utility class for processing XLSForm files and converting to XForm XML"""
    
    def __init__(self):
        self.supported_question_types = {
            'text', 'integer', 'decimal', 'date', 'time', 'datetime',
            'select_one', 'select_multiple', 'note', 'geopoint', 'geotrace', 'geoshape',
            'image', 'audio', 'video', 'file', 'barcode', 'calculate', 'acknowledge'
        }
    
    def process_xlsform(self, xlsform_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process XLSForm data and convert to XForm XML
        
        Args:
            xlsform_data: Dictionary containing XLSForm sheets (survey, choices, settings)
        
        Returns:
            Dictionary containing processed form data and XForm XML
        """
        try:
            # Validate XLSForm structure
            self._validate_xlsform(xlsform_data)
            
            # Extract form metadata
            form_metadata = self._extract_form_metadata(xlsform_data)
            
            # Generate XForm XML
            xform_xml = self._generate_xform_xml(xlsform_data, form_metadata)
            
            return {
                'success': True,
                'form_metadata': form_metadata,
                'xform_xml': xform_xml,
                'xlsform_data': xlsform_data
            }
            
        except Exception as e:
            logger.error(f"Error processing XLSForm: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'xlsform_data': xlsform_data
            }
    
    def _validate_xlsform(self, xlsform_data: Dict[str, Any]) -> None:
        """Validate XLSForm structure and required fields"""
        
        # Check required sheets
        if 'survey' not in xlsform_data:
            raise ValueError("XLSForm must contain a 'survey' sheet")
        
        survey_sheet = xlsform_data['survey']
        if not survey_sheet:
            raise ValueError("Survey sheet cannot be empty")
        
        # Check required columns in survey sheet
        required_columns = ['type', 'name']
        for row in survey_sheet:
            for col in required_columns:
                if col not in row:
                    raise ValueError(f"Survey sheet must contain '{col}' column")
        
        # Validate question types
        for row in survey_sheet:
            question_type = row.get('type', '').split()[0]  # Handle "select_one list_name" format
            if question_type and question_type not in self.supported_question_types:
                logger.warning(f"Unsupported question type: {question_type}")
    
    def _extract_form_metadata(self, xlsform_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract form metadata from XLSForm"""
        
        settings = xlsform_data.get('settings', [{}])[0] if xlsform_data.get('settings') else {}
        
        form_id = settings.get('form_id') or f"form_{uuid.uuid4().hex[:8]}"
        form_title = settings.get('form_title') or settings.get('title') or form_id
        version = settings.get('version') or '1.0'
        
        return {
            'form_id': form_id,
            'title': form_title,
            'version': version,
            'instance_name': settings.get('instance_name'),
            'submission_url': settings.get('submission_url'),
            'default_language': settings.get('default_language', 'default')
        }
    
    def _generate_xform_xml(self, xlsform_data: Dict[str, Any], metadata: Dict[str, Any]) -> str:
        """Generate XForm XML from XLSForm data"""
        
        # Create root element
        root = ET.Element('h:html')
        root.set('xmlns', 'http://www.w3.org/2002/xforms')
        root.set('xmlns:h', 'http://www.w3.org/1999/xhtml')
        root.set('xmlns:ev', 'http://www.w3.org/2001/xml-events')
        root.set('xmlns:xsd', 'http://www.w3.org/2001/XMLSchema')
        root.set('xmlns:jr', 'http://openrosa.org/javarosa')
        
        # Create head section
        head = ET.SubElement(root, 'h:head')
        title = ET.SubElement(head, 'h:title')
        title.text = metadata['title']
        
        # Create model
        model = ET.SubElement(head, 'model')
        
        # Create instance
        instance = ET.SubElement(model, 'instance')
        data = ET.SubElement(instance, 'data')
        data.set('id', metadata['form_id'])
        data.set('version', metadata['version'])
        
        # Create bind elements and form controls
        survey_sheet = xlsform_data['survey']
        choices_sheet = xlsform_data.get('choices', [])
        
        # Process survey questions
        body = ET.SubElement(root, 'h:body')
        
        for row in survey_sheet:
            question_name = row.get('name')
            question_type = row.get('type', '')
            question_label = row.get('label', question_name)
            
            if not question_name:
                continue
            
            # Add to data instance
            field = ET.SubElement(data, question_name)
            
            # Create bind element
            bind = ET.SubElement(model, 'bind')
            bind.set('nodeset', f"/{metadata['form_id']}/{question_name}")
            bind.set('type', self._get_xform_type(question_type))
            
            # Add constraints if present
            if row.get('constraint'):
                bind.set('constraint', row['constraint'])
            if row.get('required') == 'yes':
                bind.set('required', 'true()')
            if row.get('readonly') == 'yes':
                bind.set('readonly', 'true()')
            if row.get('calculate'):
                bind.set('calculate', row['calculate'])
            
            # Create form control
            if question_type.startswith('select_one'):
                self._create_select_control(body, row, choices_sheet, single=True)
            elif question_type.startswith('select_multiple'):
                self._create_select_control(body, row, choices_sheet, single=False)
            elif question_type == 'note':
                self._create_note_control(body, row)
            else:
                self._create_input_control(body, row, question_type)
        
        # Convert to string with pretty formatting
        rough_string = ET.tostring(root, 'unicode')
        reparsed = minidom.parseString(rough_string)
        return reparsed.toprettyxml(indent="  ")
    
    def _get_xform_type(self, question_type: str) -> str:
        """Map XLSForm question type to XForm data type"""
        type_mapping = {
            'text': 'string',
            'integer': 'int',
            'decimal': 'decimal',
            'date': 'date',
            'time': 'time',
            'datetime': 'dateTime',
            'geopoint': 'geopoint',
            'geotrace': 'geotrace',
            'geoshape': 'geoshape',
            'image': 'binary',
            'audio': 'binary',
            'video': 'binary',
            'file': 'binary',
            'barcode': 'barcode',
            'calculate': 'string',
            'note': 'string',
            'acknowledge': 'string'
        }
        
        base_type = question_type.split()[0]
        return type_mapping.get(base_type, 'string')
    
    def _create_input_control(self, parent: ET.Element, row: Dict[str, Any], question_type: str) -> None:
        """Create input control for basic question types"""
        
        if question_type == 'note':
            return  # Notes are handled separately
        
        input_elem = ET.SubElement(parent, 'input')
        input_elem.set('ref', f"/{row.get('name')}")
        
        label = ET.SubElement(input_elem, 'label')
        label.text = row.get('label', row.get('name'))
        
        if row.get('hint'):
            hint = ET.SubElement(input_elem, 'hint')
            hint.text = row['hint']
    
    def _create_select_control(self, parent: ET.Element, row: Dict[str, Any], 
                             choices_sheet: List[Dict[str, Any]], single: bool = True) -> None:
        """Create select control for choice questions"""
        
        question_type = row.get('type', '')
        list_name = question_type.split()[-1] if len(question_type.split()) > 1 else None
        
        if not list_name:
            return
        
        # Find choices for this list
        choices = [choice for choice in choices_sheet 
                  if choice.get('list_name') == list_name]
        
        if not choices:
            return
        
        select_elem = ET.SubElement(parent, 'select1' if single else 'select')
        select_elem.set('ref', f"/{row.get('name')}")
        
        label = ET.SubElement(select_elem, 'label')
        label.text = row.get('label', row.get('name'))
        
        if row.get('hint'):
            hint = ET.SubElement(select_elem, 'hint')
            hint.text = row['hint']
        
        # Add choices
        for choice in choices:
            item = ET.SubElement(select_elem, 'item')
            
            choice_label = ET.SubElement(item, 'label')
            choice_label.text = choice.get('label', choice.get('name'))
            
            value = ET.SubElement(item, 'value')
            value.text = choice.get('name', '')
    
    def _create_note_control(self, parent: ET.Element, row: Dict[str, Any]) -> None:
        """Create note/display control"""
        
        output_elem = ET.SubElement(parent, 'output')
        output_elem.set('value', f"'{row.get('label', '')}'")
        
        label = ET.SubElement(output_elem, 'label')
        label.text = row.get('label', row.get('name'))

def parse_xlsform_file(file_content: bytes, filename: str) -> Dict[str, Any]:
    """
    Parse XLSForm file content into structured data
    
    Args:
        file_content: Raw file content as bytes
        filename: Original filename
    
    Returns:
        Dictionary containing parsed XLSForm data
    """
    try:
        # Read Excel file
        excel_data = pd.read_excel(file_content, sheet_name=None, engine='openpyxl')
        
        xlsform_data = {}
        
        # Process each sheet
        for sheet_name, df in excel_data.items():
            # Convert DataFrame to list of dictionaries
            # Replace NaN values with empty strings
            df = df.fillna('')
            xlsform_data[sheet_name.lower()] = df.to_dict('records')
        
        return xlsform_data
        
    except Exception as e:
        logger.error(f"Error parsing XLSForm file {filename}: {str(e)}")
        raise ValueError(f"Invalid XLSForm file: {str(e)}")

