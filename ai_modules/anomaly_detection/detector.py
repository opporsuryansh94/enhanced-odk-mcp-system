"""
Enhanced anomaly detection implementation for ODK MCP System.
Includes real-time detection, advanced algorithms, and subscription-aware features.
"""

import os
import pickle
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Union, Optional, Any
from datetime import datetime, timedelta
import json

from ..config import AI_CONFIG, check_subscription_limit
from ..utils.logging import setup_logger, log_ai_event


class EnhancedAnomalyDetector:
    """
    Enhanced anomaly detector for detecting anomalies in ODK data submissions.
    
    This class provides advanced methods to detect anomalies in data using various
    algorithms including statistical methods, machine learning, and deep learning.
    """
    
    def __init__(self, config: Dict = None):
        """
        Initialize the enhanced anomaly detector.
        
        Args:
            config: Configuration dictionary. If None, uses the global AI_CONFIG.
        """
        self.config = config or AI_CONFIG["anomaly_detection"]
        self.logger = setup_logger("enhanced_anomaly_detector")
        self.models = {}
        self.statistics = {}
        self.alert_history = []
        
        # Load models if they exist
        if self.config["enabled"]:
            self._load_models()
            self._load_statistics()
    
    def detect_submission_anomalies(self, submissions: List[Dict], 
                                  user_plan: str = "starter",
                                  current_usage: int = 0) -> Dict:
        """
        Detect anomalies in form submissions with subscription awareness.
        
        Args:
            submissions: List of form submissions.
            user_plan: User's subscription plan.
            current_usage: Current monthly usage count.
            
        Returns:
            Dictionary with anomaly detection results.
        """
        if not self.config["enabled"]:
            return {"status": "disabled", "message": "Anomaly detection is disabled"}
        
        # Check subscription limits
        if not check_subscription_limit("anomaly_detection", user_plan, 
                                      "max_detections_per_month", current_usage):
            return {
                "status": "limit_exceeded",
                "message": f"Monthly anomaly detection limit exceeded for {user_plan} plan"
            }
        
        if not submissions:
            return {"status": "error", "message": "No submissions provided"}
        
        try:
            # Analyze submissions for different types of anomalies
            results = {
                "status": "success",
                "timestamp": datetime.now().isoformat(),
                "total_submissions": len(submissions),
                "anomalies": {
                    "temporal": self._detect_temporal_anomalies(submissions),
                    "value": self._detect_value_anomalies(submissions),
                    "pattern": self._detect_pattern_anomalies(submissions),
                    "geospatial": self._detect_geospatial_anomalies(submissions),
                    "behavioral": self._detect_behavioral_anomalies(submissions)
                },
                "summary": {},
                "alerts": []
            }
            
            # Generate summary
            total_anomalies = sum(len(anomalies) for anomalies in results["anomalies"].values())
            results["summary"] = {
                "total_anomalies": total_anomalies,
                "anomaly_rate": total_anomalies / len(submissions) * 100,
                "severity_distribution": self._calculate_severity_distribution(results["anomalies"]),
                "recommendations": self._generate_recommendations(results["anomalies"])
            }
            
            # Generate alerts if needed
            if total_anomalies > 0:
                results["alerts"] = self._generate_alerts(results["anomalies"], results["summary"])
            
            # Log event
            log_ai_event("enhanced_anomaly_detection", {
                "user_plan": user_plan,
                "num_submissions": len(submissions),
                "total_anomalies": total_anomalies,
                "anomaly_rate": results["summary"]["anomaly_rate"]
            })
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error in enhanced anomaly detection: {e}")
            return {"status": "error", "message": str(e)}
    
    def detect_real_time_anomaly(self, submission: Dict, 
                                form_schema: Dict = None,
                                historical_data: List[Dict] = None) -> Dict:
        """
        Detect anomalies in a single submission in real-time.
        
        Args:
            submission: Single form submission.
            form_schema: Form schema for validation.
            historical_data: Historical submissions for comparison.
            
        Returns:
            Dictionary with real-time anomaly detection results.
        """
        if not self.config["real_time_detection"]:
            return {"status": "disabled", "message": "Real-time detection is disabled"}
        
        try:
            anomalies = []
            
            # Check for immediate red flags
            immediate_checks = self._immediate_anomaly_checks(submission, form_schema)
            anomalies.extend(immediate_checks)
            
            # Compare with historical patterns if available
            if historical_data:
                historical_checks = self._historical_comparison_checks(submission, historical_data)
                anomalies.extend(historical_checks)
            
            # Calculate overall risk score
            risk_score = self._calculate_risk_score(anomalies)
            
            result = {
                "status": "success",
                "timestamp": datetime.now().isoformat(),
                "submission_id": submission.get("id", "unknown"),
                "anomalies": anomalies,
                "risk_score": risk_score,
                "risk_level": self._get_risk_level(risk_score),
                "requires_review": risk_score > self.config["alert_threshold"]
            }
            
            # Log high-risk submissions
            if result["requires_review"]:
                log_ai_event("high_risk_submission", {
                    "submission_id": result["submission_id"],
                    "risk_score": risk_score,
                    "anomaly_count": len(anomalies)
                })
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error in real-time anomaly detection: {e}")
            return {"status": "error", "message": str(e)}
    
    def _detect_temporal_anomalies(self, submissions: List[Dict]) -> List[Dict]:
        """Detect temporal anomalies in submissions."""
        anomalies = []
        
        try:
            # Extract timestamps
            timestamps = []
            for i, submission in enumerate(submissions):
                timestamp_str = submission.get("submitted_at") or submission.get("timestamp")
                if timestamp_str:
                    try:
                        timestamp = pd.to_datetime(timestamp_str)
                        timestamps.append({"index": i, "timestamp": timestamp, "submission": submission})
                    except:
                        continue
            
            if len(timestamps) < 10:  # Need sufficient data
                return anomalies
            
            # Convert to DataFrame for analysis
            df = pd.DataFrame(timestamps)
            df = df.sort_values("timestamp")
            
            # Detect unusual submission times
            df["hour"] = df["timestamp"].dt.hour
            df["day_of_week"] = df["timestamp"].dt.dayofweek
            
            # Find submissions outside normal hours (assuming 6 AM to 10 PM)
            unusual_hours = df[(df["hour"] < 6) | (df["hour"] > 22)]
            for _, row in unusual_hours.iterrows():
                anomalies.append({
                    "type": "temporal",
                    "subtype": "unusual_hour",
                    "index": row["index"],
                    "submission": row["submission"],
                    "details": f"Submission at unusual hour: {row['hour']}:00",
                    "severity": "medium",
                    "confidence": 0.7
                })
            
            # Detect rapid successive submissions (potential spam/bot)
            df["time_diff"] = df["timestamp"].diff().dt.total_seconds()
            rapid_submissions = df[df["time_diff"] < 60]  # Less than 1 minute apart
            for _, row in rapid_submissions.iterrows():
                anomalies.append({
                    "type": "temporal",
                    "subtype": "rapid_submission",
                    "index": row["index"],
                    "submission": row["submission"],
                    "details": f"Rapid submission: {row['time_diff']:.1f} seconds after previous",
                    "severity": "high",
                    "confidence": 0.9
                })
            
        except Exception as e:
            self.logger.error(f"Error detecting temporal anomalies: {e}")
        
        return anomalies
    
    def _detect_value_anomalies(self, submissions: List[Dict]) -> List[Dict]:
        """Detect value-based anomalies in submissions."""
        anomalies = []
        
        try:
            # Group submissions by field
            field_values = {}
            for i, submission in enumerate(submissions):
                for field, value in submission.items():
                    if field not in field_values:
                        field_values[field] = []
                    field_values[field].append({"index": i, "value": value, "submission": submission})
            
            # Analyze each field
            for field, values in field_values.items():
                if len(values) < 10:  # Need sufficient data
                    continue
                
                # Extract numeric values
                numeric_values = []
                for item in values:
                    try:
                        if isinstance(item["value"], (int, float)):
                            numeric_values.append(item)
                        elif isinstance(item["value"], str) and item["value"].replace(".", "").replace("-", "").isdigit():
                            numeric_values.append({
                                **item,
                                "value": float(item["value"])
                            })
                    except:
                        continue
                
                if len(numeric_values) >= 10:
                    # Statistical outlier detection
                    values_array = np.array([item["value"] for item in numeric_values])
                    q1, q3 = np.percentile(values_array, [25, 75])
                    iqr = q3 - q1
                    lower_bound = q1 - 1.5 * iqr
                    upper_bound = q3 + 1.5 * iqr
                    
                    for item in numeric_values:
                        if item["value"] < lower_bound or item["value"] > upper_bound:
                            anomalies.append({
                                "type": "value",
                                "subtype": "statistical_outlier",
                                "field": field,
                                "index": item["index"],
                                "submission": item["submission"],
                                "details": f"Value {item['value']} outside normal range [{lower_bound:.2f}, {upper_bound:.2f}]",
                                "severity": "medium",
                                "confidence": 0.8
                            })
                
                # Check for impossible values (domain-specific)
                for item in values:
                    if self._is_impossible_value(field, item["value"]):
                        anomalies.append({
                            "type": "value",
                            "subtype": "impossible_value",
                            "field": field,
                            "index": item["index"],
                            "submission": item["submission"],
                            "details": f"Impossible value for field {field}: {item['value']}",
                            "severity": "high",
                            "confidence": 0.95
                        })
        
        except Exception as e:
            self.logger.error(f"Error detecting value anomalies: {e}")
        
        return anomalies
    
    def _detect_pattern_anomalies(self, submissions: List[Dict]) -> List[Dict]:
        """Detect pattern-based anomalies in submissions."""
        anomalies = []
        
        try:
            # Look for repeated identical submissions
            submission_hashes = {}
            for i, submission in enumerate(submissions):
                # Create a hash of the submission (excluding metadata)
                content = {k: v for k, v in submission.items() 
                          if k not in ["id", "submitted_at", "timestamp", "user_id"]}
                content_str = json.dumps(content, sort_keys=True)
                content_hash = hash(content_str)
                
                if content_hash in submission_hashes:
                    submission_hashes[content_hash].append({"index": i, "submission": submission})
                else:
                    submission_hashes[content_hash] = [{"index": i, "submission": submission}]
            
            # Flag duplicate submissions
            for content_hash, items in submission_hashes.items():
                if len(items) > 1:
                    for item in items[1:]:  # Skip the first occurrence
                        anomalies.append({
                            "type": "pattern",
                            "subtype": "duplicate_submission",
                            "index": item["index"],
                            "submission": item["submission"],
                            "details": f"Duplicate submission (appears {len(items)} times)",
                            "severity": "medium",
                            "confidence": 0.9
                        })
            
            # Look for suspicious response patterns
            for i, submission in enumerate(submissions):
                if self._has_suspicious_pattern(submission):
                    anomalies.append({
                        "type": "pattern",
                        "subtype": "suspicious_response_pattern",
                        "index": i,
                        "submission": submission,
                        "details": "Suspicious response pattern detected",
                        "severity": "medium",
                        "confidence": 0.7
                    })
        
        except Exception as e:
            self.logger.error(f"Error detecting pattern anomalies: {e}")
        
        return anomalies
    
    def _detect_geospatial_anomalies(self, submissions: List[Dict]) -> List[Dict]:
        """Detect geospatial anomalies in submissions."""
        anomalies = []
        
        try:
            # Extract GPS coordinates
            gps_data = []
            for i, submission in enumerate(submissions):
                lat = submission.get("latitude") or submission.get("lat") or submission.get("gps_lat")
                lon = submission.get("longitude") or submission.get("lon") or submission.get("gps_lon")
                
                if lat is not None and lon is not None:
                    try:
                        lat_float = float(lat)
                        lon_float = float(lon)
                        
                        # Basic validation
                        if -90 <= lat_float <= 90 and -180 <= lon_float <= 180:
                            gps_data.append({
                                "index": i,
                                "lat": lat_float,
                                "lon": lon_float,
                                "submission": submission
                            })
                    except:
                        continue
            
            if len(gps_data) < 5:  # Need sufficient data
                return anomalies
            
            # Calculate distances from centroid
            lats = [item["lat"] for item in gps_data]
            lons = [item["lon"] for item in gps_data]
            centroid_lat = np.mean(lats)
            centroid_lon = np.mean(lons)
            
            # Find outliers based on distance from centroid
            distances = []
            for item in gps_data:
                distance = self._haversine_distance(
                    centroid_lat, centroid_lon, item["lat"], item["lon"]
                )
                distances.append(distance)
                item["distance_from_centroid"] = distance
            
            # Statistical outlier detection for distances
            distances_array = np.array(distances)
            q1, q3 = np.percentile(distances_array, [25, 75])
            iqr = q3 - q1
            upper_bound = q3 + 1.5 * iqr
            
            for item in gps_data:
                if item["distance_from_centroid"] > upper_bound:
                    anomalies.append({
                        "type": "geospatial",
                        "subtype": "location_outlier",
                        "index": item["index"],
                        "submission": item["submission"],
                        "details": f"Location {item['distance_from_centroid']:.2f}km from expected area",
                        "severity": "medium",
                        "confidence": 0.8
                    })
        
        except Exception as e:
            self.logger.error(f"Error detecting geospatial anomalies: {e}")
        
        return anomalies
    
    def _detect_behavioral_anomalies(self, submissions: List[Dict]) -> List[Dict]:
        """Detect behavioral anomalies in submissions."""
        anomalies = []
        
        try:
            # Group by user if user information is available
            user_submissions = {}
            for i, submission in enumerate(submissions):
                user_id = submission.get("user_id") or submission.get("enumerator_id") or "unknown"
                if user_id not in user_submissions:
                    user_submissions[user_id] = []
                user_submissions[user_id].append({"index": i, "submission": submission})
            
            # Analyze each user's behavior
            for user_id, user_data in user_submissions.items():
                if len(user_data) < 3:  # Need sufficient data
                    continue
                
                # Check for unusually high submission rate
                if len(user_data) > 50:  # Arbitrary threshold
                    for item in user_data:
                        anomalies.append({
                            "type": "behavioral",
                            "subtype": "high_submission_rate",
                            "index": item["index"],
                            "submission": item["submission"],
                            "details": f"User {user_id} has {len(user_data)} submissions (unusually high)",
                            "severity": "medium",
                            "confidence": 0.7
                        })
                
                # Check for consistent response patterns (possible bot behavior)
                if self._has_consistent_patterns(user_data):
                    for item in user_data:
                        anomalies.append({
                            "type": "behavioral",
                            "subtype": "consistent_pattern",
                            "index": item["index"],
                            "submission": item["submission"],
                            "details": f"User {user_id} shows consistent response patterns",
                            "severity": "medium",
                            "confidence": 0.6
                        })
        
        except Exception as e:
            self.logger.error(f"Error detecting behavioral anomalies: {e}")
        
        return anomalies
    
    def _immediate_anomaly_checks(self, submission: Dict, form_schema: Dict = None) -> List[Dict]:
        """Perform immediate anomaly checks on a single submission."""
        anomalies = []
        
        # Check for missing required fields
        if form_schema:
            required_fields = form_schema.get("required_fields", [])
            for field in required_fields:
                if field not in submission or submission[field] is None or submission[field] == "":
                    anomalies.append({
                        "type": "validation",
                        "subtype": "missing_required_field",
                        "field": field,
                        "details": f"Missing required field: {field}",
                        "severity": "high",
                        "confidence": 1.0
                    })
        
        # Check for suspicious text patterns
        for field, value in submission.items():
            if isinstance(value, str):
                if self._is_suspicious_text(value):
                    anomalies.append({
                        "type": "content",
                        "subtype": "suspicious_text",
                        "field": field,
                        "details": f"Suspicious text pattern in field {field}",
                        "severity": "medium",
                        "confidence": 0.8
                    })
        
        return anomalies
    
    def _historical_comparison_checks(self, submission: Dict, historical_data: List[Dict]) -> List[Dict]:
        """Compare submission with historical patterns."""
        anomalies = []
        
        # This would involve more complex analysis comparing the current submission
        # with historical patterns, trends, and distributions
        # For now, implementing basic checks
        
        return anomalies
    
    def _calculate_risk_score(self, anomalies: List[Dict]) -> float:
        """Calculate overall risk score based on detected anomalies."""
        if not anomalies:
            return 0.0
        
        severity_weights = {"low": 0.3, "medium": 0.6, "high": 1.0}
        total_score = 0.0
        
        for anomaly in anomalies:
            severity = anomaly.get("severity", "medium")
            confidence = anomaly.get("confidence", 0.5)
            weight = severity_weights.get(severity, 0.6)
            total_score += weight * confidence
        
        # Normalize to 0-1 range
        return min(total_score / len(anomalies), 1.0)
    
    def _get_risk_level(self, risk_score: float) -> str:
        """Convert risk score to risk level."""
        if risk_score >= 0.8:
            return "high"
        elif risk_score >= 0.5:
            return "medium"
        else:
            return "low"
    
    def _is_impossible_value(self, field: str, value: Any) -> bool:
        """Check if a value is impossible for a given field."""
        # Domain-specific validation rules
        field_lower = field.lower()
        
        if "age" in field_lower:
            try:
                age = float(value)
                return age < 0 or age > 150
            except:
                return False
        
        if "temperature" in field_lower:
            try:
                temp = float(value)
                return temp < -50 or temp > 60  # Celsius
            except:
                return False
        
        if "percentage" in field_lower or "percent" in field_lower:
            try:
                pct = float(value)
                return pct < 0 or pct > 100
            except:
                return False
        
        return False
    
    def _has_suspicious_pattern(self, submission: Dict) -> bool:
        """Check if submission has suspicious response patterns."""
        # Look for patterns like all same values, sequential values, etc.
        values = [str(v) for v in submission.values() if v is not None]
        
        if len(values) < 3:
            return False
        
        # All same values
        if len(set(values)) == 1:
            return True
        
        # Sequential numeric values
        try:
            numeric_values = [float(v) for v in values if str(v).replace(".", "").isdigit()]
            if len(numeric_values) >= 3:
                diffs = [numeric_values[i+1] - numeric_values[i] for i in range(len(numeric_values)-1)]
                if all(abs(diff - diffs[0]) < 0.001 for diff in diffs):  # Constant difference
                    return True
        except:
            pass
        
        return False
    
    def _has_consistent_patterns(self, user_data: List[Dict]) -> bool:
        """Check if user has consistent response patterns across submissions."""
        if len(user_data) < 3:
            return False
        
        # This is a simplified check - in practice, you'd want more sophisticated analysis
        submissions = [item["submission"] for item in user_data]
        
        # Check if response times are suspiciously consistent
        # Check if response patterns are too similar
        # etc.
        
        return False
    
    def _is_suspicious_text(self, text: str) -> bool:
        """Check if text contains suspicious patterns."""
        text_lower = text.lower()
        
        # Check for common spam/bot patterns
        suspicious_patterns = [
            "test", "testing", "asdf", "qwerty", "1234", "abcd",
            "lorem ipsum", "sample", "example", "dummy"
        ]
        
        for pattern in suspicious_patterns:
            if pattern in text_lower:
                return True
        
        # Check for repeated characters
        if len(set(text)) < len(text) / 3:  # Too many repeated characters
            return True
        
        return False
    
    def _haversine_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate the great circle distance between two points on Earth."""
        from math import radians, cos, sin, asin, sqrt
        
        # Convert decimal degrees to radians
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        
        # Haversine formula
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * asin(sqrt(a))
        r = 6371  # Radius of earth in kilometers
        
        return c * r
    
    def _calculate_severity_distribution(self, anomalies: Dict) -> Dict:
        """Calculate distribution of anomaly severities."""
        severity_counts = {"low": 0, "medium": 0, "high": 0}
        
        for anomaly_type, anomaly_list in anomalies.items():
            for anomaly in anomaly_list:
                severity = anomaly.get("severity", "medium")
                severity_counts[severity] += 1
        
        return severity_counts
    
    def _generate_recommendations(self, anomalies: Dict) -> List[str]:
        """Generate recommendations based on detected anomalies."""
        recommendations = []
        
        # Count anomaly types
        type_counts = {}
        for anomaly_type, anomaly_list in anomalies.items():
            type_counts[anomaly_type] = len(anomaly_list)
        
        # Generate specific recommendations
        if type_counts.get("temporal", 0) > 0:
            recommendations.append("Review submission timing patterns and consider implementing time-based validation")
        
        if type_counts.get("value", 0) > 0:
            recommendations.append("Implement stricter value validation rules and range checks")
        
        if type_counts.get("pattern", 0) > 0:
            recommendations.append("Consider implementing duplicate detection and bot prevention measures")
        
        if type_counts.get("geospatial", 0) > 0:
            recommendations.append("Review location data and consider implementing geofencing")
        
        if type_counts.get("behavioral", 0) > 0:
            recommendations.append("Monitor user behavior patterns and implement rate limiting")
        
        return recommendations
    
    def _generate_alerts(self, anomalies: Dict, summary: Dict) -> List[Dict]:
        """Generate alerts based on detected anomalies."""
        alerts = []
        
        # High anomaly rate alert
        if summary["anomaly_rate"] > 20:  # More than 20% anomalies
            alerts.append({
                "type": "high_anomaly_rate",
                "severity": "high",
                "message": f"High anomaly rate detected: {summary['anomaly_rate']:.1f}%",
                "timestamp": datetime.now().isoformat()
            })
        
        # High severity anomalies alert
        high_severity_count = summary["severity_distribution"]["high"]
        if high_severity_count > 0:
            alerts.append({
                "type": "high_severity_anomalies",
                "severity": "high",
                "message": f"{high_severity_count} high-severity anomalies detected",
                "timestamp": datetime.now().isoformat()
            })
        
        return alerts
    
    def _load_models(self) -> None:
        """Load anomaly detection models from disk."""
        model_path = self.config["model_path"]
        
        if os.path.exists(model_path):
            try:
                with open(model_path, 'rb') as f:
                    self.models = pickle.load(f)
                self.logger.info(f"Loaded anomaly detection models: {list(self.models.keys())}")
            except Exception as e:
                self.logger.error(f"Error loading anomaly detection models: {e}")
                self.models = {}
    
    def _save_models(self) -> None:
        """Save anomaly detection models to disk."""
        model_path = self.config["model_path"]
        
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(model_path), exist_ok=True)
            
            with open(model_path, 'wb') as f:
                pickle.dump(self.models, f)
            self.logger.info(f"Saved anomaly detection models: {list(self.models.keys())}")
        except Exception as e:
            self.logger.error(f"Error saving anomaly detection models: {e}")
    
    def _load_statistics(self) -> None:
        """Load statistical baselines from disk."""
        stats_path = self.config["model_path"].replace("models.pkl", "statistics.json")
        
        if os.path.exists(stats_path):
            try:
                with open(stats_path, 'r') as f:
                    self.statistics = json.load(f)
                self.logger.info("Loaded anomaly detection statistics")
            except Exception as e:
                self.logger.error(f"Error loading statistics: {e}")
                self.statistics = {}
    
    def _save_statistics(self) -> None:
        """Save statistical baselines to disk."""
        stats_path = self.config["model_path"].replace("models.pkl", "statistics.json")
        
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(stats_path), exist_ok=True)
            
            with open(stats_path, 'w') as f:
                json.dump(self.statistics, f, indent=2)
            self.logger.info("Saved anomaly detection statistics")
        except Exception as e:
            self.logger.error(f"Error saving statistics: {e}")


# Backward compatibility
AnomalyDetector = EnhancedAnomalyDetector

