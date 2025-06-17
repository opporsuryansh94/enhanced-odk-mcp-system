"""
Data Encryption and GDPR Compliance System for ODK MCP System.
Provides field-level encryption, data anonymization, and privacy rights management.
"""

import os
import json
import uuid
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
import logging
from dataclasses import dataclass, asdict
from enum import Enum
import base64

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import sqlalchemy as sa
from sqlalchemy import create_engine, Column, String, Integer, DateTime, Boolean, Text, JSON, LargeBinary
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

from .config import ENCRYPTION, GDPR, AUDIT


# Database Models
Base = declarative_base()


class DataCategory(Enum):
    PERSONAL_IDENTIFIERS = "personal_identifiers"
    CONTACT_INFORMATION = "contact_information"
    DEMOGRAPHIC_DATA = "demographic_data"
    LOCATION_DATA = "location_data"
    BEHAVIORAL_DATA = "behavioral_data"
    TECHNICAL_DATA = "technical_data"
    USAGE_DATA = "usage_data"
    COMMUNICATION_DATA = "communication_data"


class ConsentStatus(Enum):
    GIVEN = "given"
    WITHDRAWN = "withdrawn"
    PENDING = "pending"
    EXPIRED = "expired"


class DataProcessingPurpose(Enum):
    SERVICE_PROVISION = "service_provision"
    ANALYTICS = "analytics"
    MARKETING = "marketing"
    RESEARCH = "research"
    LEGAL_COMPLIANCE = "legal_compliance"
    SECURITY = "security"


@dataclass
class EncryptionResult:
    success: bool
    encrypted_data: Optional[str] = None
    key_id: Optional[str] = None
    error_message: Optional[str] = None


@dataclass
class DecryptionResult:
    success: bool
    decrypted_data: Optional[str] = None
    error_message: Optional[str] = None


class EncryptionKey(Base):
    __tablename__ = 'encryption_keys'
    
    id = Column(String, primary_key=True)
    key_type = Column(String, nullable=False)  # symmetric, asymmetric
    algorithm = Column(String, nullable=False)
    key_data = Column(LargeBinary, nullable=False)
    public_key = Column(LargeBinary)  # For asymmetric keys
    
    # Key metadata
    purpose = Column(String)  # field_encryption, file_encryption, etc.
    version = Column(Integer, default=1)
    is_active = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime)
    rotated_at = Column(DateTime)


class DataConsent(Base):
    __tablename__ = 'data_consents'
    
    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False)
    data_category = Column(String, nullable=False)
    processing_purpose = Column(String, nullable=False)
    lawful_basis = Column(String, nullable=False)
    
    # Consent details
    status = Column(String, default=ConsentStatus.GIVEN.value)
    consent_text = Column(Text)
    consent_version = Column(String)
    
    # Timestamps
    given_at = Column(DateTime, default=datetime.utcnow)
    withdrawn_at = Column(DateTime)
    expires_at = Column(DateTime)
    
    # Metadata
    ip_address = Column(String)
    user_agent = Column(Text)
    consent_method = Column(String)  # web_form, api, etc.


class DataRetention(Base):
    __tablename__ = 'data_retention'
    
    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False)
    data_type = Column(String, nullable=False)
    data_identifier = Column(String, nullable=False)
    
    # Retention details
    retention_period_days = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    
    # Status
    is_deleted = Column(Boolean, default=False)
    deleted_at = Column(DateTime)
    deletion_method = Column(String)  # soft_delete, hard_delete, anonymize


class DataRequest(Base):
    __tablename__ = 'data_requests'
    
    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False)
    request_type = Column(String, nullable=False)  # access, portability, deletion, rectification
    
    # Request details
    status = Column(String, default='pending')  # pending, processing, completed, rejected
    description = Column(Text)
    requested_data_types = Column(JSON)
    
    # Processing
    processed_by = Column(String)
    processed_at = Column(DateTime)
    completion_notes = Column(Text)
    
    # Files
    export_file_path = Column(String)
    export_file_url = Column(String)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    due_date = Column(DateTime)  # Legal requirement: 30 days for GDPR


class EncryptionManager:
    """
    Comprehensive encryption and data protection system.
    """
    
    def __init__(self, database_url: str = "sqlite:///encryption.db"):
        """
        Initialize the encryption manager.
        
        Args:
            database_url: Database connection URL.
        """
        self.engine = create_engine(database_url)
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # Initialize encryption keys
        self._initialize_encryption_keys()
    
    def _initialize_encryption_keys(self):
        """Initialize default encryption keys if they don't exist."""
        with self.SessionLocal() as db:
            # Check if we have an active field encryption key
            existing_key = db.query(EncryptionKey).filter(
                EncryptionKey.purpose == 'field_encryption',
                EncryptionKey.is_active == True
            ).first()
            
            if not existing_key:
                # Generate new field encryption key
                key = Fernet.generate_key()
                
                encryption_key = EncryptionKey(
                    id=str(uuid.uuid4()),
                    key_type='symmetric',
                    algorithm='AES-256-GCM',
                    key_data=key,
                    purpose='field_encryption'
                )
                
                db.add(encryption_key)
                db.commit()
                
                self.logger.info("Generated new field encryption key")
    
    def encrypt_field(self, data: str, field_name: str = None) -> EncryptionResult:
        """
        Encrypt a field value.
        
        Args:
            data: Data to encrypt.
            field_name: Name of the field (for key selection).
            
        Returns:
            Encryption result.
        """
        try:
            if not ENCRYPTION["field_encryption_enabled"]:
                return EncryptionResult(
                    success=True,
                    encrypted_data=data,  # Return as-is if encryption disabled
                    key_id=None
                )
            
            with self.SessionLocal() as db:
                # Get active encryption key
                key_record = db.query(EncryptionKey).filter(
                    EncryptionKey.purpose == 'field_encryption',
                    EncryptionKey.is_active == True
                ).first()
                
                if not key_record:
                    return EncryptionResult(
                        success=False,
                        error_message="No active encryption key found"
                    )
                
                # Encrypt data
                fernet = Fernet(key_record.key_data)
                encrypted_data = fernet.encrypt(data.encode()).decode()
                
                return EncryptionResult(
                    success=True,
                    encrypted_data=encrypted_data,
                    key_id=key_record.id
                )
                
        except Exception as e:
            self.logger.error(f"Field encryption error: {str(e)}")
            return EncryptionResult(
                success=False,
                error_message=str(e)
            )
    
    def decrypt_field(self, encrypted_data: str, key_id: str = None) -> DecryptionResult:
        """
        Decrypt a field value.
        
        Args:
            encrypted_data: Encrypted data to decrypt.
            key_id: ID of the encryption key (optional).
            
        Returns:
            Decryption result.
        """
        try:
            if not ENCRYPTION["field_encryption_enabled"]:
                return DecryptionResult(
                    success=True,
                    decrypted_data=encrypted_data  # Return as-is if encryption disabled
                )
            
            with self.SessionLocal() as db:
                # Get encryption key
                if key_id:
                    key_record = db.query(EncryptionKey).filter(
                        EncryptionKey.id == key_id
                    ).first()
                else:
                    # Use active key
                    key_record = db.query(EncryptionKey).filter(
                        EncryptionKey.purpose == 'field_encryption',
                        EncryptionKey.is_active == True
                    ).first()
                
                if not key_record:
                    return DecryptionResult(
                        success=False,
                        error_message="Encryption key not found"
                    )
                
                # Decrypt data
                fernet = Fernet(key_record.key_data)
                decrypted_data = fernet.decrypt(encrypted_data.encode()).decode()
                
                return DecryptionResult(
                    success=True,
                    decrypted_data=decrypted_data
                )
                
        except Exception as e:
            self.logger.error(f"Field decryption error: {str(e)}")
            return DecryptionResult(
                success=False,
                error_message=str(e)
            )
    
    def encrypt_sensitive_fields(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Encrypt sensitive fields in a data dictionary.
        
        Args:
            data: Data dictionary.
            
        Returns:
            Data dictionary with encrypted sensitive fields.
        """
        encrypted_data = data.copy()
        
        for field_name in ENCRYPTION["encrypt_sensitive_fields"]:
            if field_name in encrypted_data and encrypted_data[field_name]:
                result = self.encrypt_field(str(encrypted_data[field_name]), field_name)
                if result.success:
                    encrypted_data[field_name] = result.encrypted_data
                    # Store key ID for decryption
                    encrypted_data[f"{field_name}_key_id"] = result.key_id
        
        return encrypted_data
    
    def decrypt_sensitive_fields(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Decrypt sensitive fields in a data dictionary.
        
        Args:
            data: Data dictionary with encrypted fields.
            
        Returns:
            Data dictionary with decrypted sensitive fields.
        """
        decrypted_data = data.copy()
        
        for field_name in ENCRYPTION["encrypt_sensitive_fields"]:
            if field_name in decrypted_data and decrypted_data[field_name]:
                key_id = decrypted_data.get(f"{field_name}_key_id")
                result = self.decrypt_field(decrypted_data[field_name], key_id)
                if result.success:
                    decrypted_data[field_name] = result.decrypted_data
                    # Remove key ID from result
                    decrypted_data.pop(f"{field_name}_key_id", None)
        
        return decrypted_data
    
    def rotate_encryption_keys(self) -> Dict[str, Any]:
        """
        Rotate encryption keys.
        
        Returns:
            Key rotation result.
        """
        try:
            with self.SessionLocal() as db:
                # Get current active key
                current_key = db.query(EncryptionKey).filter(
                    EncryptionKey.purpose == 'field_encryption',
                    EncryptionKey.is_active == True
                ).first()
                
                if not current_key:
                    return {
                        "success": False,
                        "error_message": "No active key found"
                    }
                
                # Generate new key
                new_key_data = Fernet.generate_key()
                
                new_key = EncryptionKey(
                    id=str(uuid.uuid4()),
                    key_type='symmetric',
                    algorithm='AES-256-GCM',
                    key_data=new_key_data,
                    purpose='field_encryption',
                    version=current_key.version + 1
                )
                
                # Deactivate old key
                current_key.is_active = False
                current_key.rotated_at = datetime.utcnow()
                
                db.add(new_key)
                db.commit()
                
                self.logger.info(f"Rotated encryption key from {current_key.id} to {new_key.id}")
                
                return {
                    "success": True,
                    "old_key_id": current_key.id,
                    "new_key_id": new_key.id
                }
                
        except Exception as e:
            self.logger.error(f"Key rotation error: {str(e)}")
            return {
                "success": False,
                "error_message": str(e)
            }
    
    def anonymize_data(self, data: Dict[str, Any], anonymization_rules: Dict[str, str] = None) -> Dict[str, Any]:
        """
        Anonymize personal data.
        
        Args:
            data: Data to anonymize.
            anonymization_rules: Rules for anonymization.
            
        Returns:
            Anonymized data.
        """
        if not GDPR["anonymization_enabled"]:
            return data
        
        anonymized_data = data.copy()
        
        # Default anonymization rules
        default_rules = {
            "email": "hash",
            "phone": "mask",
            "name": "pseudonym",
            "address": "generalize",
            "ip_address": "truncate"
        }
        
        rules = anonymization_rules or default_rules
        
        for field, method in rules.items():
            if field in anonymized_data and anonymized_data[field]:
                value = str(anonymized_data[field])
                
                if method == "hash":
                    # Hash the value
                    anonymized_data[field] = hashlib.sha256(value.encode()).hexdigest()[:16]
                elif method == "mask":
                    # Mask the value
                    if len(value) > 4:
                        anonymized_data[field] = value[:2] + "*" * (len(value) - 4) + value[-2:]
                    else:
                        anonymized_data[field] = "*" * len(value)
                elif method == "pseudonym":
                    # Generate pseudonym
                    hash_value = hashlib.md5(value.encode()).hexdigest()
                    anonymized_data[field] = f"User_{hash_value[:8]}"
                elif method == "generalize":
                    # Generalize the value
                    anonymized_data[field] = "Generalized Location"
                elif method == "truncate":
                    # Truncate IP address
                    if "." in value:  # IPv4
                        parts = value.split(".")
                        anonymized_data[field] = f"{parts[0]}.{parts[1]}.0.0"
                    elif ":" in value:  # IPv6
                        parts = value.split(":")
                        anonymized_data[field] = ":".join(parts[:4] + ["0000"] * 4)
        
        return anonymized_data


class GDPRComplianceManager:
    """
    GDPR compliance and privacy rights management system.
    """
    
    def __init__(self, database_url: str = "sqlite:///gdpr.db"):
        """
        Initialize the GDPR compliance manager.
        
        Args:
            database_url: Database connection URL.
        """
        self.engine = create_engine(database_url)
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # Initialize encryption manager
        self.encryption_manager = EncryptionManager(database_url)
    
    def record_consent(
        self,
        user_id: str,
        data_category: str,
        processing_purpose: str,
        lawful_basis: str,
        consent_text: str,
        consent_version: str = "1.0",
        ip_address: str = None,
        user_agent: str = None
    ) -> Dict[str, Any]:
        """
        Record user consent for data processing.
        
        Args:
            user_id: User ID.
            data_category: Category of data.
            processing_purpose: Purpose of processing.
            lawful_basis: Legal basis for processing.
            consent_text: Text of the consent.
            consent_version: Version of the consent.
            ip_address: User's IP address.
            user_agent: User's user agent.
            
        Returns:
            Consent recording result.
        """
        try:
            with self.SessionLocal() as db:
                consent_id = str(uuid.uuid4())
                
                consent = DataConsent(
                    id=consent_id,
                    user_id=user_id,
                    data_category=data_category,
                    processing_purpose=processing_purpose,
                    lawful_basis=lawful_basis,
                    consent_text=consent_text,
                    consent_version=consent_version,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    consent_method='web_form'
                )
                
                db.add(consent)
                db.commit()
                
                self.logger.info(f"Recorded consent {consent_id} for user {user_id}")
                
                return {
                    "success": True,
                    "consent_id": consent_id
                }
                
        except Exception as e:
            self.logger.error(f"Consent recording error: {str(e)}")
            return {
                "success": False,
                "error_message": str(e)
            }
    
    def withdraw_consent(self, user_id: str, consent_id: str) -> Dict[str, Any]:
        """
        Withdraw user consent.
        
        Args:
            user_id: User ID.
            consent_id: Consent ID to withdraw.
            
        Returns:
            Withdrawal result.
        """
        try:
            with self.SessionLocal() as db:
                consent = db.query(DataConsent).filter(
                    DataConsent.id == consent_id,
                    DataConsent.user_id == user_id
                ).first()
                
                if not consent:
                    return {
                        "success": False,
                        "error_message": "Consent not found"
                    }
                
                consent.status = ConsentStatus.WITHDRAWN.value
                consent.withdrawn_at = datetime.utcnow()
                
                db.commit()
                
                self.logger.info(f"Withdrew consent {consent_id} for user {user_id}")
                
                return {
                    "success": True
                }
                
        except Exception as e:
            self.logger.error(f"Consent withdrawal error: {str(e)}")
            return {
                "success": False,
                "error_message": str(e)
            }
    
    def create_data_request(
        self,
        user_id: str,
        request_type: str,
        description: str = None,
        requested_data_types: List[str] = None
    ) -> Dict[str, Any]:
        """
        Create a data subject request (access, portability, deletion, rectification).
        
        Args:
            user_id: User ID.
            request_type: Type of request.
            description: Request description.
            requested_data_types: Types of data requested.
            
        Returns:
            Request creation result.
        """
        try:
            with self.SessionLocal() as db:
                request_id = str(uuid.uuid4())
                due_date = datetime.utcnow() + timedelta(days=30)  # GDPR requirement
                
                data_request = DataRequest(
                    id=request_id,
                    user_id=user_id,
                    request_type=request_type,
                    description=description,
                    requested_data_types=requested_data_types or [],
                    due_date=due_date
                )
                
                db.add(data_request)
                db.commit()
                
                self.logger.info(f"Created data request {request_id} for user {user_id}")
                
                return {
                    "success": True,
                    "request_id": request_id,
                    "due_date": due_date.isoformat()
                }
                
        except Exception as e:
            self.logger.error(f"Data request creation error: {str(e)}")
            return {
                "success": False,
                "error_message": str(e)
            }
    
    def process_data_access_request(self, request_id: str) -> Dict[str, Any]:
        """
        Process a data access request.
        
        Args:
            request_id: Request ID.
            
        Returns:
            Processing result.
        """
        try:
            with self.SessionLocal() as db:
                request = db.query(DataRequest).filter(
                    DataRequest.id == request_id
                ).first()
                
                if not request:
                    return {
                        "success": False,
                        "error_message": "Request not found"
                    }
                
                if request.request_type != "access":
                    return {
                        "success": False,
                        "error_message": "Invalid request type"
                    }
                
                # Collect user data
                user_data = self._collect_user_data(request.user_id)
                
                # Create export file
                export_file_path = self._create_data_export(user_data, request.user_id)
                
                # Update request
                request.status = "completed"
                request.processed_at = datetime.utcnow()
                request.export_file_path = export_file_path
                
                db.commit()
                
                return {
                    "success": True,
                    "export_file_path": export_file_path
                }
                
        except Exception as e:
            self.logger.error(f"Data access request processing error: {str(e)}")
            return {
                "success": False,
                "error_message": str(e)
            }
    
    def process_data_deletion_request(self, request_id: str) -> Dict[str, Any]:
        """
        Process a data deletion request (right to be forgotten).
        
        Args:
            request_id: Request ID.
            
        Returns:
            Processing result.
        """
        try:
            with self.SessionLocal() as db:
                request = db.query(DataRequest).filter(
                    DataRequest.id == request_id
                ).first()
                
                if not request:
                    return {
                        "success": False,
                        "error_message": "Request not found"
                    }
                
                if request.request_type != "deletion":
                    return {
                        "success": False,
                        "error_message": "Invalid request type"
                    }
                
                # Perform data deletion/anonymization
                deletion_result = self._delete_user_data(request.user_id)
                
                # Update request
                request.status = "completed"
                request.processed_at = datetime.utcnow()
                request.completion_notes = f"Deleted {deletion_result['deleted_records']} records"
                
                db.commit()
                
                return {
                    "success": True,
                    "deleted_records": deletion_result['deleted_records']
                }
                
        except Exception as e:
            self.logger.error(f"Data deletion request processing error: {str(e)}")
            return {
                "success": False,
                "error_message": str(e)
            }
    
    def _collect_user_data(self, user_id: str) -> Dict[str, Any]:
        """Collect all user data for export."""
        # This would collect data from all relevant tables
        # Implementation depends on your specific data model
        user_data = {
            "user_id": user_id,
            "collection_date": datetime.utcnow().isoformat(),
            "data_categories": {}
        }
        
        # Add data from different categories
        # This is a simplified example
        user_data["data_categories"]["profile"] = {
            "description": "User profile information",
            "data": {}  # Actual profile data would go here
        }
        
        user_data["data_categories"]["forms"] = {
            "description": "Forms created by the user",
            "data": {}  # Actual form data would go here
        }
        
        user_data["data_categories"]["submissions"] = {
            "description": "Form submissions by the user",
            "data": {}  # Actual submission data would go here
        }
        
        return user_data
    
    def _create_data_export(self, user_data: Dict[str, Any], user_id: str) -> str:
        """Create a data export file."""
        export_dir = "/tmp/data_exports"
        os.makedirs(export_dir, exist_ok=True)
        
        export_file_path = os.path.join(export_dir, f"user_data_{user_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json")
        
        with open(export_file_path, 'w') as f:
            json.dump(user_data, f, indent=2, default=str)
        
        return export_file_path
    
    def _delete_user_data(self, user_id: str) -> Dict[str, Any]:
        """Delete or anonymize user data."""
        deleted_records = 0
        
        # This would delete/anonymize data from all relevant tables
        # Implementation depends on your specific data model
        
        # Example: Anonymize instead of hard delete for audit purposes
        with self.SessionLocal() as db:
            # Update user records to anonymized versions
            # This is a simplified example
            pass
        
        return {
            "deleted_records": deleted_records,
            "method": "anonymization"
        }
    
    def check_data_retention(self) -> Dict[str, Any]:
        """Check and enforce data retention policies."""
        try:
            with self.SessionLocal() as db:
                current_time = datetime.utcnow()
                
                # Find expired data
                expired_data = db.query(DataRetention).filter(
                    DataRetention.expires_at <= current_time,
                    DataRetention.is_deleted == False
                ).all()
                
                deleted_count = 0
                for retention_record in expired_data:
                    # Mark as deleted
                    retention_record.is_deleted = True
                    retention_record.deleted_at = current_time
                    retention_record.deletion_method = "automatic_retention"
                    
                    deleted_count += 1
                
                db.commit()
                
                return {
                    "success": True,
                    "expired_records": len(expired_data),
                    "deleted_records": deleted_count
                }
                
        except Exception as e:
            self.logger.error(f"Data retention check error: {str(e)}")
            return {
                "success": False,
                "error_message": str(e)
            }


# Create global instances
encryption_manager = EncryptionManager()
gdpr_manager = GDPRComplianceManager()

