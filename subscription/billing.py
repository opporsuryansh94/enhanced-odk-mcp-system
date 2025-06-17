"""
Billing and Invoice Management for ODK MCP System.
Handles invoice generation, PDF creation, and billing automation.
"""

import os
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from decimal import Decimal
import logging
from io import BytesIO

from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER
from reportlab.lib import colors
from jinja2 import Template
import pdfkit

from .config import BILLING, SUBSCRIPTION_PLANS


class BillingManager:
    """
    Comprehensive billing and invoice management system.
    """
    
    def __init__(self):
        """Initialize the billing manager."""
        self.logger = logging.getLogger(__name__)
        
        # Invoice counter for generating invoice numbers
        self.invoice_counter = 1000
        
        # Company details (should be configurable)
        self.company_details = {
            "name": "ODK MCP Systems Pvt. Ltd.",
            "address": "123 Tech Park, Bangalore, Karnataka 560001",
            "phone": "+91 80 1234 5678",
            "email": "billing@odkmcp.com",
            "website": "https://odkmcp.com",
            "gstin": "29ABCDE1234F1Z5",  # Sample GSTIN
            "pan": "ABCDE1234F"
        }
    
    def generate_invoice_number(self) -> str:
        """Generate a unique invoice number."""
        self.invoice_counter += 1
        return f"{BILLING['invoice_prefix']}{self.invoice_counter:06d}"
    
    def create_invoice(
        self,
        user_details: Dict[str, Any],
        subscription_details: Dict[str, Any],
        line_items: List[Dict[str, Any]],
        billing_period: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        Create a new invoice.
        
        Args:
            user_details: User/customer details.
            subscription_details: Subscription information.
            line_items: List of billing line items.
            billing_period: Billing period information.
            
        Returns:
            Invoice data dictionary.
        """
        invoice_id = str(uuid.uuid4())
        invoice_number = self.generate_invoice_number()
        
        # Calculate totals
        subtotal = sum(Decimal(str(item.get('amount', 0))) for item in line_items)
        tax_rate = Decimal(str(BILLING['tax_rate'])) / 100
        tax_amount = subtotal * tax_rate
        total_amount = subtotal + tax_amount
        
        # Create invoice data
        invoice_data = {
            "id": invoice_id,
            "invoice_number": invoice_number,
            "user_details": user_details,
            "subscription_details": subscription_details,
            "company_details": self.company_details,
            "line_items": line_items,
            "billing_period": billing_period,
            "subtotal": float(subtotal),
            "tax_rate": BILLING['tax_rate'],
            "tax_amount": float(tax_amount),
            "total_amount": float(total_amount),
            "currency": BILLING['default_currency'],
            "issue_date": datetime.now().strftime("%Y-%m-%d"),
            "due_date": (datetime.now() + timedelta(days=BILLING['invoice_due_days'])).strftime("%Y-%m-%d"),
            "status": "draft"
        }
        
        return invoice_data
    
    def generate_subscription_invoice(
        self,
        user_details: Dict[str, Any],
        subscription: Dict[str, Any],
        usage_details: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate invoice for subscription billing.
        
        Args:
            user_details: User/customer details.
            subscription: Subscription details.
            usage_details: Optional usage-based billing details.
            
        Returns:
            Generated invoice data.
        """
        plan = SUBSCRIPTION_PLANS[subscription['plan_id']]
        
        # Create line items
        line_items = []
        
        # Base subscription fee
        if subscription['billing_cycle'] == 'yearly':
            amount = plan['price_yearly']
            description = f"{plan['name']} Plan - Annual Subscription"
            period = "Annual"
        else:
            amount = plan['price_monthly']
            description = f"{plan['name']} Plan - Monthly Subscription"
            period = "Monthly"
        
        line_items.append({
            "description": description,
            "quantity": 1,
            "unit_price": amount,
            "amount": amount
        })
        
        # Add usage-based charges if applicable
        if usage_details and subscription['plan_id'] in ['pro', 'enterprise']:
            for usage_type, usage_data in usage_details.items():
                if usage_data.get('overage_amount', 0) > 0:
                    line_items.append({
                        "description": f"Additional {usage_type.replace('_', ' ').title()}",
                        "quantity": usage_data['overage_quantity'],
                        "unit_price": usage_data['overage_rate'],
                        "amount": usage_data['overage_amount']
                    })
        
        # Billing period
        billing_period = {
            "start": subscription['current_period_start'],
            "end": subscription['current_period_end'],
            "type": period
        }
        
        return self.create_invoice(user_details, subscription, line_items, billing_period)
    
    def generate_invoice_pdf(self, invoice_data: Dict[str, Any]) -> BytesIO:
        """
        Generate PDF invoice using ReportLab.
        
        Args:
            invoice_data: Invoice data dictionary.
            
        Returns:
            BytesIO object containing the PDF.
        """
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=0.5*inch)
        
        # Styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=HexColor('#2c3e50'),
            spaceAfter=30,
            alignment=TA_CENTER
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=HexColor('#34495e'),
            spaceAfter=12
        )
        
        normal_style = styles['Normal']
        normal_style.fontSize = 10
        
        # Build PDF content
        content = []
        
        # Header
        content.append(Paragraph("INVOICE", title_style))
        content.append(Spacer(1, 20))
        
        # Company and customer details
        company_customer_data = [
            [
                Paragraph(f"<b>{self.company_details['name']}</b><br/>"
                         f"{self.company_details['address']}<br/>"
                         f"Phone: {self.company_details['phone']}<br/>"
                         f"Email: {self.company_details['email']}<br/>"
                         f"GSTIN: {self.company_details['gstin']}", normal_style),
                Paragraph(f"<b>Bill To:</b><br/>"
                         f"{invoice_data['user_details']['name']}<br/>"
                         f"{invoice_data['user_details'].get('organization', '')}<br/>"
                         f"{invoice_data['user_details']['email']}<br/>"
                         f"{invoice_data['user_details'].get('phone', '')}", normal_style)
            ]
        ]
        
        company_customer_table = Table(company_customer_data, colWidths=[3*inch, 3*inch])
        company_customer_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ]))
        
        content.append(company_customer_table)
        content.append(Spacer(1, 30))
        
        # Invoice details
        invoice_details_data = [
            ['Invoice Number:', invoice_data['invoice_number']],
            ['Issue Date:', invoice_data['issue_date']],
            ['Due Date:', invoice_data['due_date']],
            ['Billing Period:', f"{invoice_data['billing_period']['start']} to {invoice_data['billing_period']['end']}"],
        ]
        
        invoice_details_table = Table(invoice_details_data, colWidths=[2*inch, 2*inch])
        invoice_details_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        
        content.append(invoice_details_table)
        content.append(Spacer(1, 30))
        
        # Line items
        content.append(Paragraph("Invoice Details", heading_style))
        
        line_items_data = [['Description', 'Quantity', 'Unit Price', 'Amount']]
        
        for item in invoice_data['line_items']:
            line_items_data.append([
                item['description'],
                str(item['quantity']),
                f"{invoice_data['currency']} {item['unit_price']:.2f}",
                f"{invoice_data['currency']} {item['amount']:.2f}"
            ])
        
        # Add totals
        line_items_data.extend([
            ['', '', 'Subtotal:', f"{invoice_data['currency']} {invoice_data['subtotal']:.2f}"],
            ['', '', f'Tax ({invoice_data["tax_rate"]}%):', f"{invoice_data['currency']} {invoice_data['tax_amount']:.2f}"],
            ['', '', 'Total Amount:', f"{invoice_data['currency']} {invoice_data['total_amount']:.2f}"]
        ])
        
        line_items_table = Table(line_items_data, colWidths=[3*inch, 1*inch, 1.5*inch, 1.5*inch])
        line_items_table.setStyle(TableStyle([
            # Header row
            ('BACKGROUND', (0, 0), (-1, 0), HexColor('#34495e')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            
            # Data rows
            ('FONTNAME', (0, 1), (-1, -4), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -4), 10),
            ('ROWBACKGROUNDS', (0, 1), (-1, -4), [colors.beige, colors.white]),
            
            # Total rows
            ('FONTNAME', (0, -3), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, -3), (-1, -1), 10),
            ('BACKGROUND', (0, -1), (-1, -1), HexColor('#ecf0f1')),
            
            # General styling
            ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        
        content.append(line_items_table)
        content.append(Spacer(1, 30))
        
        # Payment terms
        content.append(Paragraph("Payment Terms", heading_style))
        payment_terms = f"""
        • Payment is due within {BILLING['invoice_due_days']} days of invoice date<br/>
        • Late payments may incur additional charges<br/>
        • For any billing queries, contact {self.company_details['email']}<br/>
        • Thank you for your business!
        """
        content.append(Paragraph(payment_terms, normal_style))
        
        # Build PDF
        doc.build(content)
        buffer.seek(0)
        
        return buffer
    
    def generate_invoice_html(self, invoice_data: Dict[str, Any]) -> str:
        """
        Generate HTML invoice template.
        
        Args:
            invoice_data: Invoice data dictionary.
            
        Returns:
            HTML string for the invoice.
        """
        html_template = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Invoice {{ invoice_number }}</title>
            <style>
                body {
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    margin: 0;
                    padding: 20px;
                    color: #333;
                    line-height: 1.6;
                }
                .invoice-container {
                    max-width: 800px;
                    margin: 0 auto;
                    background: white;
                    padding: 40px;
                    box-shadow: 0 0 20px rgba(0,0,0,0.1);
                }
                .header {
                    text-align: center;
                    margin-bottom: 40px;
                    border-bottom: 3px solid #2c3e50;
                    padding-bottom: 20px;
                }
                .header h1 {
                    color: #2c3e50;
                    font-size: 2.5em;
                    margin: 0;
                }
                .company-customer {
                    display: flex;
                    justify-content: space-between;
                    margin-bottom: 40px;
                }
                .company-details, .customer-details {
                    flex: 1;
                }
                .customer-details {
                    text-align: right;
                }
                .invoice-details {
                    background: #ecf0f1;
                    padding: 20px;
                    margin-bottom: 30px;
                    border-radius: 5px;
                }
                .invoice-details table {
                    width: 100%;
                }
                .invoice-details td {
                    padding: 5px 0;
                }
                .invoice-details td:first-child {
                    font-weight: bold;
                    width: 150px;
                }
                .line-items {
                    margin-bottom: 30px;
                }
                .line-items table {
                    width: 100%;
                    border-collapse: collapse;
                    margin-top: 20px;
                }
                .line-items th {
                    background: #34495e;
                    color: white;
                    padding: 15px;
                    text-align: left;
                }
                .line-items td {
                    padding: 12px 15px;
                    border-bottom: 1px solid #ddd;
                }
                .line-items tr:nth-child(even) {
                    background: #f8f9fa;
                }
                .totals {
                    text-align: right;
                    margin-top: 20px;
                }
                .totals table {
                    margin-left: auto;
                    width: 300px;
                }
                .totals td {
                    padding: 8px 15px;
                    border-bottom: 1px solid #ddd;
                }
                .totals .total-row {
                    background: #2c3e50;
                    color: white;
                    font-weight: bold;
                    font-size: 1.2em;
                }
                .payment-terms {
                    margin-top: 40px;
                    padding: 20px;
                    background: #f8f9fa;
                    border-left: 4px solid #3498db;
                }
                .payment-terms h3 {
                    color: #2c3e50;
                    margin-top: 0;
                }
                .footer {
                    text-align: center;
                    margin-top: 40px;
                    padding-top: 20px;
                    border-top: 1px solid #ddd;
                    color: #7f8c8d;
                }
                @media print {
                    body { margin: 0; padding: 0; }
                    .invoice-container { box-shadow: none; }
                }
            </style>
        </head>
        <body>
            <div class="invoice-container">
                <div class="header">
                    <h1>INVOICE</h1>
                </div>
                
                <div class="company-customer">
                    <div class="company-details">
                        <h3>{{ company_details.name }}</h3>
                        <p>
                            {{ company_details.address }}<br>
                            Phone: {{ company_details.phone }}<br>
                            Email: {{ company_details.email }}<br>
                            GSTIN: {{ company_details.gstin }}
                        </p>
                    </div>
                    <div class="customer-details">
                        <h3>Bill To:</h3>
                        <p>
                            <strong>{{ user_details.name }}</strong><br>
                            {% if user_details.organization %}{{ user_details.organization }}<br>{% endif %}
                            {{ user_details.email }}<br>
                            {% if user_details.phone %}{{ user_details.phone }}{% endif %}
                        </p>
                    </div>
                </div>
                
                <div class="invoice-details">
                    <table>
                        <tr>
                            <td>Invoice Number:</td>
                            <td>{{ invoice_number }}</td>
                        </tr>
                        <tr>
                            <td>Issue Date:</td>
                            <td>{{ issue_date }}</td>
                        </tr>
                        <tr>
                            <td>Due Date:</td>
                            <td>{{ due_date }}</td>
                        </tr>
                        <tr>
                            <td>Billing Period:</td>
                            <td>{{ billing_period.start }} to {{ billing_period.end }}</td>
                        </tr>
                    </table>
                </div>
                
                <div class="line-items">
                    <h3>Invoice Details</h3>
                    <table>
                        <thead>
                            <tr>
                                <th>Description</th>
                                <th>Quantity</th>
                                <th>Unit Price</th>
                                <th>Amount</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for item in line_items %}
                            <tr>
                                <td>{{ item.description }}</td>
                                <td>{{ item.quantity }}</td>
                                <td>{{ currency }} {{ "%.2f"|format(item.unit_price) }}</td>
                                <td>{{ currency }} {{ "%.2f"|format(item.amount) }}</td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                    
                    <div class="totals">
                        <table>
                            <tr>
                                <td>Subtotal:</td>
                                <td>{{ currency }} {{ "%.2f"|format(subtotal) }}</td>
                            </tr>
                            <tr>
                                <td>Tax ({{ tax_rate }}%):</td>
                                <td>{{ currency }} {{ "%.2f"|format(tax_amount) }}</td>
                            </tr>
                            <tr class="total-row">
                                <td>Total Amount:</td>
                                <td>{{ currency }} {{ "%.2f"|format(total_amount) }}</td>
                            </tr>
                        </table>
                    </div>
                </div>
                
                <div class="payment-terms">
                    <h3>Payment Terms</h3>
                    <ul>
                        <li>Payment is due within {{ invoice_due_days }} days of invoice date</li>
                        <li>Late payments may incur additional charges</li>
                        <li>For any billing queries, contact {{ company_details.email }}</li>
                        <li>Thank you for your business!</li>
                    </ul>
                </div>
                
                <div class="footer">
                    <p>This is a computer-generated invoice. No signature required.</p>
                    <p>{{ company_details.website }}</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        template = Template(html_template)
        
        # Add invoice due days to template context
        invoice_data['invoice_due_days'] = BILLING['invoice_due_days']
        
        return template.render(**invoice_data)
    
    def save_invoice_pdf(self, invoice_data: Dict[str, Any], file_path: str) -> str:
        """
        Save invoice as PDF file.
        
        Args:
            invoice_data: Invoice data dictionary.
            file_path: Path to save the PDF file.
            
        Returns:
            Path to the saved PDF file.
        """
        pdf_buffer = self.generate_invoice_pdf(invoice_data)
        
        with open(file_path, 'wb') as f:
            f.write(pdf_buffer.getvalue())
        
        return file_path
    
    def calculate_usage_overage(
        self,
        plan_limits: Dict[str, int],
        current_usage: Dict[str, int],
        overage_rates: Dict[str, float]
    ) -> Dict[str, Dict[str, float]]:
        """
        Calculate overage charges for usage-based billing.
        
        Args:
            plan_limits: Plan limits for each metric.
            current_usage: Current usage for each metric.
            overage_rates: Overage rates per unit for each metric.
            
        Returns:
            Dictionary with overage calculations.
        """
        overage_details = {}
        
        for metric, limit in plan_limits.items():
            if limit == -1:  # Unlimited
                continue
                
            usage = current_usage.get(metric, 0)
            if usage > limit:
                overage_quantity = usage - limit
                overage_rate = overage_rates.get(metric, 0)
                overage_amount = overage_quantity * overage_rate
                
                overage_details[metric] = {
                    "limit": limit,
                    "usage": usage,
                    "overage_quantity": overage_quantity,
                    "overage_rate": overage_rate,
                    "overage_amount": overage_amount
                }
        
        return overage_details
    
    def generate_usage_report(
        self,
        user_details: Dict[str, Any],
        usage_data: Dict[str, Any],
        plan_details: Dict[str, Any],
        period: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        Generate usage report for a billing period.
        
        Args:
            user_details: User details.
            usage_data: Usage metrics.
            plan_details: Subscription plan details.
            period: Billing period.
            
        Returns:
            Usage report data.
        """
        report_data = {
            "user_details": user_details,
            "plan_details": plan_details,
            "period": period,
            "usage_summary": [],
            "total_usage_score": 0
        }
        
        total_score = 0
        for metric, usage in usage_data.items():
            limit = plan_details["limits"].get(metric, 0)
            
            if limit == -1:  # Unlimited
                usage_percentage = 0
                status = "unlimited"
            elif limit == 0:  # Not allowed
                usage_percentage = 0 if usage == 0 else 100
                status = "not_allowed" if usage > 0 else "within_limit"
            else:
                usage_percentage = (usage / limit) * 100
                if usage_percentage <= 50:
                    status = "low"
                elif usage_percentage <= 80:
                    status = "moderate"
                elif usage_percentage <= 100:
                    status = "high"
                else:
                    status = "exceeded"
            
            report_data["usage_summary"].append({
                "metric": metric,
                "usage": usage,
                "limit": limit,
                "usage_percentage": usage_percentage,
                "status": status
            })
            
            total_score += usage_percentage
        
        report_data["total_usage_score"] = total_score / len(usage_data) if usage_data else 0
        
        return report_data


# Create a global instance
billing_manager = BillingManager()

