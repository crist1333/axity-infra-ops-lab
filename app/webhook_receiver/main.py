#!/usr/bin/env python3
"""
Axity Webhook Receiver for Alert Management
Receives alerts from Prometheus Alertmanager and creates GLPI tickets
"""

import os
import json
import logging
import traceback
from datetime import datetime
from typing import Dict, Any, List, Optional

import requests
import uvicorn
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.responses import Response
from pydantic import BaseModel, Field
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

# Configure logging
logging.basicConfig(
    level=getattr(logging, os.getenv('LOG_LEVEL', 'INFO').upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Prometheus metrics
alerts_received_total = Counter('webhook_alerts_received_total', 'Total alerts received', ['status', 'severity'])
tickets_created_total = Counter('webhook_tickets_created_total', 'Total tickets created', ['success'])
request_duration_seconds = Histogram('webhook_request_duration_seconds', 'Time spent processing requests')

# Configuration
GLPI_URL = os.getenv("GLPI_URL", "http://localhost:8080")
GLPI_APP_TOKEN = os.getenv("GLPI_APP_TOKEN", "axity_lab_token")
GLPI_USER_TOKEN = os.getenv("GLPI_USER_TOKEN", "admin_token")
GLPI_USERNAME = os.getenv("GLPI_USERNAME", "glpi")
GLPI_PASSWORD = os.getenv("GLPI_PASSWORD", "glpi")

app = FastAPI(
    title="Axity Webhook Receiver",
    description="Receives Prometheus alerts and creates GLPI tickets",
    version="1.0.0"
)

class AlertPayload(BaseModel):
    """Alertmanager webhook payload structure"""
    receiver: str
    status: str
    alerts: List[Dict[str, Any]]
    groupKey: Optional[str] = None
    truncatedAlerts: Optional[int] = 0
    groupLabels: Optional[Dict[str, str]] = {}
    commonLabels: Optional[Dict[str, str]] = {}
    commonAnnotations: Optional[Dict[str, str]] = {}
    externalURL: Optional[str] = None
    version: Optional[str] = "4"

class GLPIClient:
    """GLPI API Client"""
    
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
                logger.info("GLPI session initialized successfully")
                return True
            else:
                logger.error("Failed to get session token from GLPI response")
                return False
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Error initializing GLPI session: {e}")
            return False
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON response from GLPI: {e}")
            return False
    
    def create_ticket(self, title: str, description: str, urgency: int = 3, priority: int = 3) -> Optional[Dict[str, Any]]:
        """Create a ticket in GLPI"""
        if not self.session_token:
            logger.error("No active GLPI session. Cannot create ticket.")
            return None
        
        url = f"{self.base_url}/apirest.php/Ticket"
        
        payload = {
            "input": {
                "name": title,
                "content": description,
                "type": 1,           # 1 = Incident
                "status": 1,         # 1 = New
                "urgency": urgency,
                "priority": priority,
                "source": 6,         # 6 = Other (automated)
                "_users_id_requester": 2,  # Assuming user ID 2 exists
            }
        }
        
        try:
            response = requests.post(url, headers=self.headers, json=payload, timeout=10)
            response.raise_for_status()
            
            result = response.json()
            ticket_id = result.get("id")
            
            if ticket_id:
                logger.info(f"GLPI ticket created successfully: ID #{ticket_id}")
                return result
            else:
                logger.error(f"Failed to create ticket - no ID in response: {result}")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Error creating GLPI ticket: {e}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON response from GLPI: {e}")
            return None
    
    def close_session(self):
        """Close GLPI session"""
        if not self.session_token:
            return
        
        url = f"{self.base_url}/apirest.php/killSession"
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            if response.status_code == 200:
                logger.info("GLPI session closed")
        except requests.exceptions.RequestException:
            pass  # Ignore errors when closing session

async def process_alert_background(alert_data: Dict[str, Any]):
    """Process alert in background task"""
    try:
        client = GLPIClient()
        
        if not client.init_session():
            tickets_created_total.labels(success='false').inc()
            return
        
        # Extract alert information
        labels = alert_data.get('labels', {})
        annotations = alert_data.get('annotations', {})
        
        severity = labels.get('severity', 'unknown')
        service = labels.get('service', 'unknown')
        alertname = labels.get('alertname', 'Unknown Alert')
        
        title = f"[{severity.upper()}] {alertname} - {service}"
        
        # Build detailed description
        description = f"""
ALERT DETAILS:
==============
Alert: {alertname}
Service: {service}
Severity: {severity}
Status: {alert_data.get('status', 'unknown')}
Started: {alert_data.get('startsAt', 'unknown')}

SUMMARY:
{annotations.get('summary', 'No summary available')}

DESCRIPTION:
{annotations.get('description', 'No description available')}

LABELS:
{json.dumps(labels, indent=2)}

ANNOTATIONS:
{json.dumps(annotations, indent=2)}

This ticket was automatically created by the Axity Infrastructure Monitoring System.
For more information, check the Prometheus AlertManager at: http://localhost:9093
"""
        
        # Map severity to urgency
        urgency_map = {
            'critical': 5,
            'high': 4, 
            'warning': 3,
            'info': 2,
            'low': 1
        }
        urgency = urgency_map.get(severity.lower(), 3)
        
        result = client.create_ticket(title, description, urgency=urgency, priority=urgency)
        
        if result:
            tickets_created_total.labels(success='true').inc()
            logger.info(f"Successfully processed alert: {alertname}")
        else:
            tickets_created_total.labels(success='false').inc()
            logger.error(f"Failed to create ticket for alert: {alertname}")
            
    except Exception as e:
        logger.error(f"Error processing alert: {e}")
        logger.error(traceback.format_exc())
        tickets_created_total.labels(success='false').inc()
    finally:
        try:
            client.close_session()
        except:
            pass

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Axity Webhook Receiver",
        "version": "1.0.0",
        "status": "active"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.post("/alert")
async def receive_alert(payload: AlertPayload, background_tasks: BackgroundTasks):
    """Receive alerts from Alertmanager"""
    with request_duration_seconds.time():
        try:
            logger.info(f"Received alert payload with {len(payload.alerts)} alerts")
            logger.debug(f"Full payload: {payload.model_dump()}")
            
            processed_count = 0
            
            for alert in payload.alerts:
                status = alert.get('status', 'unknown')
                severity = alert.get('labels', {}).get('severity', 'unknown')
                
                # Count all received alerts
                alerts_received_total.labels(status=status, severity=severity).inc()
                
                # Only process firing alerts
                if status == 'firing':
                    background_tasks.add_task(process_alert_background, alert)
                    processed_count += 1
                else:
                    logger.info(f"Ignoring {status} alert")
            
            return {
                "status": "success",
                "message": f"Processed {processed_count} firing alerts out of {len(payload.alerts)} total alerts",
                "alerts_processed": processed_count,
                "alerts_total": len(payload.alerts)
            }
            
        except Exception as e:
            logger.error(f"Error processing webhook: {e}")
            logger.error(traceback.format_exc())
            raise HTTPException(status_code=500, detail=f"Error processing alert: {str(e)}")

@app.post("/test")
async def test_glpi():
    """Test GLPI connection and ticket creation"""
    try:
        client = GLPIClient()
        
        if not client.init_session():
            return {"status": "error", "message": "Failed to initialize GLPI session"}
        
        test_title = f"Test Ticket - {datetime.utcnow().isoformat()}"
        test_description = "This is a test ticket created by the Axity Webhook Receiver to verify GLPI connectivity."
        
        result = client.create_ticket(test_title, test_description)
        
        client.close_session()
        
        if result:
            return {"status": "success", "message": "Test ticket created successfully", "ticket": result}
        else:
            return {"status": "error", "message": "Failed to create test ticket"}
            
    except Exception as e:
        logger.error(f"Error in test endpoint: {e}")
        raise HTTPException(status_code=500, detail=f"Test failed: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=5000,
        log_level=os.getenv('LOG_LEVEL', 'info').lower(),
        reload=False
    )