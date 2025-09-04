#!/usr/bin/env python3
"""
GLPI Ticket Creation Script for Axity Infrastructure Operations
Creates tickets in GLPI using REST API when alerts are triggered
"""

import os
import sys
import json
import requests
from datetime import datetime
from typing import Optional, Dict, Any

# GLPI Configuration
GLPI_URL = os.getenv("GLPI_URL", "http://localhost:8080")
GLPI_APP_TOKEN = os.getenv("GLPI_APP_TOKEN", "axity_lab_token")
GLPI_USER_TOKEN = os.getenv("GLPI_USER_TOKEN", "admin_token")
GLPI_USERNAME = os.getenv("GLPI_USERNAME", "glpi")
GLPI_PASSWORD = os.getenv("GLPI_PASSWORD", "glpi")

class GLPIClient:
    """GLPI API Client for ticket management"""
    
    def __init__(self):
        self.base_url = GLPI_URL.rstrip('/')
        self.session_token = None
        self.headers = {
            "Content-Type": "application/json",
            "App-Token": GLPI_APP_TOKEN,
        }
    
    def init_session(self) -> bool:
        """Initialize GLPI session"""
        url = f"{self.base_url}/apirest.php/initSession"
        
        # Try token-based authentication first
        if GLPI_USER_TOKEN != "admin_token":
            auth_headers = {**self.headers, "Authorization": f"user_token {GLPI_USER_TOKEN}"}
        else:
            # Fallback to username/password
            auth_headers = {**self.headers, "Authorization": f"Basic {GLPI_USERNAME}:{GLPI_PASSWORD}"}
        
        try:
            response = requests.get(url, headers=auth_headers, timeout=10)
            response.raise_for_status()
            
            session_data = response.json()
            self.session_token = session_data.get("session_token")
            
            if self.session_token:
                self.headers["Session-Token"] = self.session_token
                print(f"✓ GLPI session initialized successfully")
                return True
            else:
                print("✗ Failed to get session token from GLPI response")
                return False
                
        except requests.exceptions.RequestException as e:
            print(f"✗ Error initializing GLPI session: {e}")
            return False
        except json.JSONDecodeError as e:
            print(f"✗ Invalid JSON response from GLPI: {e}")
            return False
    
    def create_ticket(self, title: str, description: str, urgency: int = 3, priority: int = 3) -> Optional[Dict[Any, Any]]:
        """Create a ticket in GLPI"""
        if not self.session_token:
            print("✗ No active GLPI session. Cannot create ticket.")
            return None
        
        url = f"{self.base_url}/apirest.php/Ticket"
        
        # Map urgency levels: 1=Very Low, 2=Low, 3=Medium, 4=High, 5=Very High
        urgency_map = {
            "low": 2,
            "medium": 3,
            "high": 4,
            "critical": 5
        }
        
        payload = {
            "input": {
                "name": title,
                "content": description,
                "type": 1,           # 1 = Incident
                "status": 1,         # 1 = New
                "urgency": urgency,
                "priority": priority,
                "source": 6,         # 6 = Other (automated)
                "category": 0,       # 0 = None (can be customized)
                "_users_id_requester": 2,  # Assuming user ID 2 exists (usually admin)
            }
        }
        
        try:
            response = requests.post(url, headers=self.headers, json=payload, timeout=10)
            response.raise_for_status()
            
            result = response.json()
            ticket_id = result.get("id")
            
            if ticket_id:
                print(f"✓ GLPI ticket created successfully: ID #{ticket_id}")
                print(f"  Title: {title}")
                print(f"  URL: {self.base_url}/front/ticket.form.php?id={ticket_id}")
                return result
            else:
                print("✗ Failed to create ticket - no ID in response")
                print(f"Response: {result}")
                return None
                
        except requests.exceptions.RequestException as e:
            print(f"✗ Error creating GLPI ticket: {e}")
            return None
        except json.JSONDecodeError as e:
            print(f"✗ Invalid JSON response from GLPI: {e}")
            return None
    
    def close_session(self):
        """Close GLPI session"""
        if not self.session_token:
            return
        
        url = f"{self.base_url}/apirest.php/killSession"
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            if response.status_code == 200:
                print("✓ GLPI session closed")
        except requests.exceptions.RequestException:
            pass  # Ignore errors when closing session

def create_alert_ticket(alert_type: str, severity: str, hostname: str, message: str, **kwargs) -> bool:
    """Create an alert ticket with structured information"""
    
    # Generate detailed ticket content
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    title = f"[{severity.upper()}] {alert_type.replace('_', ' ').title()} Alert - {hostname}"
    
    description = f"""
ALERT DETAILS:
==============
Type: {alert_type}
Severity: {severity.upper()}
Hostname: {hostname}
Timestamp: {timestamp}
Message: {message}

ADDITIONAL INFORMATION:
=====================
"""
    
    # Add any additional information from kwargs
    for key, value in kwargs.items():
        description += f"{key.replace('_', ' ').title()}: {value}\n"
    
    description += f"""
RECOMMENDED ACTIONS:
===================
1. Verify the alert condition on the affected system
2. Check system resources and logs
3. Take corrective action if needed
4. Update this ticket with resolution details

This ticket was automatically created by the Axity Infrastructure Monitoring System.
"""
    
    # Map severity to urgency
    severity_urgency_map = {
        "low": 2,
        "medium": 3,
        "high": 4,
        "critical": 5
    }
    
    urgency = severity_urgency_map.get(severity.lower(), 3)
    
    # Create GLPI client and ticket
    client = GLPIClient()
    
    try:
        if not client.init_session():
            return False
        
        result = client.create_ticket(title, description, urgency=urgency, priority=urgency)
        return result is not None
        
    finally:
        client.close_session()

def main():
    """Main function - handle command line arguments or JSON input"""
    
    if len(sys.argv) < 2:
        print("""
Usage:
  python3 open_alert.py <title> <description>  # Simple ticket creation
  python3 open_alert.py --json                 # Read JSON from stdin
  python3 open_alert.py --test                 # Create test ticket
  
Environment Variables:
  GLPI_URL        - GLPI base URL (default: http://localhost:8080)
  GLPI_APP_TOKEN  - GLPI application token
  GLPI_USER_TOKEN - GLPI user token (preferred)
  GLPI_USERNAME   - GLPI username (fallback)
  GLPI_PASSWORD   - GLPI password (fallback)
""")
        sys.exit(1)
    
    if sys.argv[1] == "--test":
        # Create test ticket
        success = create_alert_ticket(
            alert_type="test_alert",
            severity="medium", 
            hostname="test-server",
            message="This is a test alert from the Axity monitoring system",
            test_parameter="test_value"
        )
        sys.exit(0 if success else 1)
    
    elif sys.argv[1] == "--json":
        # Read JSON alert data from stdin
        try:
            alert_data = json.load(sys.stdin)
            success = create_alert_ticket(**alert_data)
            sys.exit(0 if success else 1)
        except json.JSONDecodeError as e:
            print(f"✗ Error parsing JSON input: {e}")
            sys.exit(1)
        except Exception as e:
            print(f"✗ Error processing alert: {e}")
            sys.exit(1)
    
    elif len(sys.argv) >= 3:
        # Simple ticket creation with title and description
        title = sys.argv[1]
        description = sys.argv[2]
        
        client = GLPIClient()
        
        try:
            if not client.init_session():
                sys.exit(1)
            
            result = client.create_ticket(title, description)
            sys.exit(0 if result else 1)
            
        finally:
            client.close_session()
    
    else:
        print("✗ Invalid arguments. Use --help for usage information.")
        sys.exit(1)

if __name__ == "__main__":
    main()