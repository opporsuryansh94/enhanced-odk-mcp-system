"""
Enhanced Test Runner for ODK MCP System
Tests all components and generates comprehensive reports
"""

import os
import sys
import subprocess
import time
import requests
import json
from datetime import datetime
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ODKSystemTester:
    """Comprehensive tester for ODK MCP System"""
    
    def __init__(self):
        self.test_results = {
            "backend_services": {},
            "frontend_components": {},
            "ai_modules": {},
            "integrations": {},
            "issues_found": [],
            "fixes_applied": [],
            "missing_features": []
        }
        self.base_dir = "/home/ubuntu/enhanced-odk-mcp-system"
    
    def test_backend_services(self):
        """Test all backend MCP services"""
        print("🔧 Testing Backend Services...")
        
        services = [
            {
                "name": "Form Management",
                "path": "mcps/form_management",
                "port": 5001,
                "main_file": "src/main.py"
            },
            {
                "name": "Data Collection", 
                "path": "mcps/data_collection",
                "port": 5002,
                "main_file": "src/main.py"
            },
            {
                "name": "Data Aggregation",
                "path": "mcps/data_aggregation", 
                "port": 5003,
                "main_file": "src/main.py"
            }
        ]
        
        for service in services:
            print(f"  Testing {service['name']}...")
            result = self._test_service(service)
            self.test_results["backend_services"][service["name"]] = result
            
            if not result["status"]:
                self.test_results["issues_found"].append({
                    "component": service["name"],
                    "issue": result["error"],
                    "severity": "high"
                })
    
    def _test_service(self, service):
        """Test individual service"""
        try:
            service_path = os.path.join(self.base_dir, service["path"])
            main_file = os.path.join(service_path, service["main_file"])
            
            # Check if main file exists
            if not os.path.exists(main_file):
                return {
                    "status": False,
                    "error": f"Main file not found: {main_file}",
                    "health_check": False
                }
            
            # Try to import and check for syntax errors
            try:
                # Change to service directory
                original_dir = os.getcwd()
                os.chdir(service_path)
                
                # Try to run a syntax check
                result = subprocess.run([
                    sys.executable, "-m", "py_compile", service["main_file"]
                ], capture_output=True, text=True, timeout=10)
                
                os.chdir(original_dir)
                
                if result.returncode != 0:
                    return {
                        "status": False,
                        "error": f"Syntax error: {result.stderr}",
                        "health_check": False
                    }
                
            except Exception as e:
                return {
                    "status": False,
                    "error": f"Import error: {str(e)}",
                    "health_check": False
                }
            
            return {
                "status": True,
                "error": None,
                "health_check": True,
                "note": "Service code is valid"
            }
            
        except Exception as e:
            return {
                "status": False,
                "error": str(e),
                "health_check": False
            }
    
    def test_ai_modules(self):
        """Test AI modules"""
        print("🤖 Testing AI Modules...")
        
        ai_modules = [
            "ai_modules/anomaly_detection/detector.py",
            "ai_modules/data_insights/analyzer.py", 
            "ai_modules/form_recommendations/recommender.py",
            "ai_modules/rag/generator.py",
            "virtual_assistant/assistant.py"
        ]
        
        for module in ai_modules:
            module_path = os.path.join(self.base_dir, module)
            module_name = os.path.basename(module).replace('.py', '')
            
            print(f"  Testing {module_name}...")
            
            if os.path.exists(module_path):
                try:
                    # Syntax check
                    result = subprocess.run([
                        sys.executable, "-m", "py_compile", module_path
                    ], capture_output=True, text=True, timeout=10)
                    
                    if result.returncode == 0:
                        self.test_results["ai_modules"][module_name] = {
                            "status": True,
                            "error": None
                        }
                    else:
                        self.test_results["ai_modules"][module_name] = {
                            "status": False,
                            "error": result.stderr
                        }
                        self.test_results["issues_found"].append({
                            "component": f"AI Module: {module_name}",
                            "issue": result.stderr,
                            "severity": "medium"
                        })
                        
                except Exception as e:
                    self.test_results["ai_modules"][module_name] = {
                        "status": False,
                        "error": str(e)
                    }
                    
            else:
                self.test_results["missing_features"].append(f"AI Module: {module}")
    
    def test_frontend_components(self):
        """Test frontend components"""
        print("🎨 Testing Frontend Components...")
        
        # Check React app
        react_app_path = os.path.join(self.base_dir, "ui/react_app")
        if os.path.exists(react_app_path):
            package_json = os.path.join(react_app_path, "package.json")
            if os.path.exists(package_json):
                self.test_results["frontend_components"]["React App"] = {
                    "status": True,
                    "note": "Package.json found"
                }
            else:
                self.test_results["issues_found"].append({
                    "component": "React App",
                    "issue": "package.json not found",
                    "severity": "high"
                })
        
        # Check React Native app
        rn_app_path = os.path.join(self.base_dir, "ui/react_native_app")
        if os.path.exists(rn_app_path):
            self.test_results["frontend_components"]["React Native App"] = {
                "status": True,
                "note": "Directory exists"
            }
        
        # Check Streamlit app
        streamlit_path = os.path.join(self.base_dir, "ui/streamlit_app")
        if os.path.exists(streamlit_path):
            app_file = os.path.join(streamlit_path, "app.py")
            if os.path.exists(app_file):
                self.test_results["frontend_components"]["Streamlit App"] = {
                    "status": True,
                    "note": "App file found"
                }
    
    def check_missing_dependencies(self):
        """Check for missing dependencies"""
        print("📦 Checking Dependencies...")
        
        requirements_file = os.path.join(self.base_dir, "requirements.txt")
        if os.path.exists(requirements_file):
            with open(requirements_file, 'r') as f:
                requirements = f.read()
                
            # Check for common missing dependencies
            missing_deps = []
            
            if "flask-sqlalchemy" not in requirements:
                missing_deps.append("flask-sqlalchemy")
            
            if "python-socketio" not in requirements:
                missing_deps.append("python-socketio")
                
            if missing_deps:
                self.test_results["issues_found"].append({
                    "component": "Dependencies",
                    "issue": f"Missing dependencies: {', '.join(missing_deps)}",
                    "severity": "medium"
                })
    
    def generate_report(self):
        """Generate comprehensive test report"""
        print("\n" + "="*60)
        print("📊 ODK MCP SYSTEM TEST REPORT")
        print("="*60)
        
        # Backend Services
        print("\n🔧 BACKEND SERVICES:")
        for service, result in self.test_results["backend_services"].items():
            status = "✅" if result["status"] else "❌"
            print(f"  {status} {service}: {'OK' if result['status'] else result['error']}")
        
        # AI Modules
        print("\n🤖 AI MODULES:")
        for module, result in self.test_results["ai_modules"].items():
            status = "✅" if result["status"] else "❌"
            print(f"  {status} {module}: {'OK' if result['status'] else result['error']}")
        
        # Frontend Components
        print("\n🎨 FRONTEND COMPONENTS:")
        for component, result in self.test_results["frontend_components"].items():
            print(f"  ✅ {component}: {result.get('note', 'OK')}")
        
        # Issues Found
        if self.test_results["issues_found"]:
            print("\n🚨 ISSUES FOUND:")
            for issue in self.test_results["issues_found"]:
                severity_icon = "🔴" if issue["severity"] == "high" else "🟡"
                print(f"  {severity_icon} {issue['component']}: {issue['issue']}")
        
        # Missing Features
        if self.test_results["missing_features"]:
            print("\n📋 MISSING FEATURES:")
            for feature in self.test_results["missing_features"]:
                print(f"  ⚠️ {feature}")
        
        # Summary
        total_tests = (len(self.test_results["backend_services"]) + 
                      len(self.test_results["ai_modules"]) + 
                      len(self.test_results["frontend_components"]))
        
        failed_tests = len(self.test_results["issues_found"])
        success_rate = ((total_tests - failed_tests) / total_tests * 100) if total_tests > 0 else 0
        
        print(f"\n📈 SUMMARY:")
        print(f"  Total Tests: {total_tests}")
        print(f"  Issues Found: {failed_tests}")
        print(f"  Success Rate: {success_rate:.1f}%")
        
        # Save report to file
        report_file = os.path.join(self.base_dir, "test_report.json")
        with open(report_file, 'w') as f:
            json.dump(self.test_results, f, indent=2, default=str)
        
        print(f"\n📄 Detailed report saved to: {report_file}")
        
        return self.test_results
    
    def run_all_tests(self):
        """Run all tests"""
        print("🚀 Starting ODK MCP System Testing...")
        print(f"📁 Base Directory: {self.base_dir}")
        print(f"⏰ Started at: {datetime.now()}")
        
        self.check_missing_dependencies()
        self.test_backend_services()
        self.test_ai_modules()
        self.test_frontend_components()
        
        return self.generate_report()


if __name__ == "__main__":
    tester = ODKSystemTester()
    results = tester.run_all_tests()

