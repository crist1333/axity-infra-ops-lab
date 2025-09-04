# Axity Infrastructure Operations Lab

A comprehensive laboratory environment simulating modern infrastructure operations, integrating containerization, orchestration, monitoring, automation, and IT Service Management (ITSM) tools.

## 🎯 Overview

This project demonstrates a complete DevOps ecosystem featuring:
- **FastAPI applications** with health monitoring
- **Kubernetes orchestration** with k3d
- **Prometheus monitoring** and alerting 
- **GLPI ITSM integration** for incident management
- **Ansible automation** for infrastructure setup
- **CI/CD pipelines** with GitHub Actions

## 📋 Prerequisites

Ensure you have the following tools installed (preferably on WSL2 or Linux):

### Required Tools
- **Docker & Docker Compose**: Container runtime and orchestration
- **k3d**: Lightweight Kubernetes cluster (`curl -s https://raw.githubusercontent.com/k3d-io/k3d/main/install.sh | bash`)
- **kubectl**: Kubernetes command-line tool
- **Python 3.11+**: For running applications locally
- **Git**: Version control

### Optional Tools
- **Ansible**: For infrastructure automation playbooks
- **Helm**: Kubernetes package manager
- **curl/jq**: For API testing

## 🏗️ Project Structure

```
axity-infra-ops-lab/
├── infra/
│   ├── ansible/playbooks/          # Infrastructure automation
│   │   ├── docker_install.yml      # Docker CE installation
│   │   ├── k8s_tools.yml          # k3d, kubectl, helm setup
│   │   ├── os_patch.yml           # System updates
│   │   └── users.yml              # Service user creation
│   ├── docker/app/                # FastAPI demo application
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   └── app/main.py
│   ├── k8s/                       # Kubernetes manifests
│   │   ├── namespace.yaml
│   │   ├── deployment.yaml
│   │   ├── service.yaml
│   │   └── kustomization.yaml
│   └── monitoring/                # Monitoring stack
│       ├── prometheus.yml
│       ├── alert_rules.yml
│       ├── alertmanager.yml
│       └── docker-compose.yml
├── app/webhook_receiver/          # Alert webhook processor
│   ├── Dockerfile
│   ├── requirements.txt
│   └── main.py
├── scripts/                       # Utility scripts
│   ├── monitor_disk.sh           # Disk space monitoring
│   └── open_alert.py             # GLPI ticket creation
├── .github/workflows/            # CI/CD pipelines
├── diagrams/                     # Architecture documentation
└── docker-compose.glpi.yml      # GLPI ITSM stack
```

## 🚀 Quick Start Guide

### Step 1: Build Application Image

```bash
# Build the demo FastAPI application
docker build -t axity-lab-app:local -f infra/docker/app/Dockerfile infra/docker/app/
```

### Step 2: Deploy to Kubernetes

```bash
# Create k3d cluster
k3d cluster create axity-lab

# Import the local image to k3d
k3d image import axity-lab-app:local --cluster axity-lab

# Deploy application using Kustomize
kubectl apply -k infra/k8s/

# Verify deployment
kubectl get all -n axity
```

### Step 3: Start GLPI ITSM System

```bash
# Launch GLPI with MariaDB
docker compose -f docker-compose.glpi.yml up -d

# Wait for services to be ready (check logs)
docker compose -f docker-compose.glpi.yml logs -f
```

**GLPI Access:**
- URL: http://localhost:8080
- Default credentials: `glpi` / `glpi`

### Step 4: Configure GLPI API (Important!)

1. Access GLPI web interface at http://localhost:8080
2. Login with `glpi` / `glpi`
3. Go to **Setup > General > API**
4. Enable REST API
5. Create API credentials:
   - Go to **Setup > Dropdowns > API clients** → Add new client
   - Note the generated **App Token**
   - Go to user profile → **Settings** tab → **API tokens** → Generate token
   - Note the **User Token**

### Step 5: Launch Monitoring Stack

Before starting, update the GLPI tokens in `infra/monitoring/docker-compose.yml`:

```yaml
webhook:
  environment:
    GLPI_URL: http://glpi-app:80
    GLPI_APP_TOKEN: your_app_token_here
    GLPI_USER_TOKEN: your_user_token_here
```

```bash
# Create the GLPI network for inter-service communication
docker network create glpi-network

# Start monitoring services
docker compose -f infra/monitoring/docker-compose.yml up -d

# Check all services are running
docker compose -f infra/monitoring/docker-compose.yml ps
```

**Monitoring Access:**
- **Prometheus**: http://localhost:9090
- **AlertManager**: http://localhost:9093  
- **Webhook Receiver**: http://localhost:5000 (API only)
- **Demo App**: http://localhost:8000

## 🔥 Testing the Incident Flow

### Simulate Application Failure

```bash
# Stop the application (simulate downtime)
kubectl scale deployment axity-lab-app -n axity --replicas=0

# Or stop the Docker container
docker stop axity-lab-app
```

### Monitor the Alert Flow

1. **Prometheus Detection** (~30 seconds):
   - Go to http://localhost:9090/alerts
   - Watch for `AppDown` alert status: `Pending` → `Firing`

2. **AlertManager Notification** (~1 minute):
   - Check http://localhost:9093 for active alerts
   - View alert details and routing

3. **Webhook Processing**:
   ```bash
   # Check webhook receiver logs
   docker logs axity-webhook-receiver -f
   ```

4. **GLPI Ticket Creation**:
   - Login to GLPI at http://localhost:8080
   - Check **Assistance > Tickets** for new incident
   - Ticket should contain alert details and severity

### Restore Service

```bash
# Restore the application
kubectl scale deployment axity-lab-app -n axity --replicas=1

# Or restart Docker container
docker start axity-lab-app
```

The alert will automatically resolve and send a resolution notification.

## 🔧 Manual Testing & Troubleshooting

### Test Individual Components

```bash
# Test FastAPI app directly
curl http://localhost:8000/
curl http://localhost:8000/healthz

# Test webhook receiver
curl http://localhost:5000/health
curl -X POST http://localhost:5000/test

# Test GLPI connectivity from webhook
docker exec -it axity-webhook-receiver python -c "
from main import GLPIClient
client = GLPIClient()
print('Session init:', client.init_session())
"

# Test Kubernetes app (port-forward)
kubectl port-forward svc/axity-lab-app-service -n axity 8001:80
# Then access http://localhost:8001
```

### View Logs

```bash
# Application logs
kubectl logs -n axity deployment/axity-lab-app -f

# Monitoring stack logs
docker compose -f infra/monitoring/docker-compose.yml logs webhook -f
docker compose -f infra/monitoring/docker-compose.yml logs prometheus -f

# GLPI logs  
docker compose -f docker-compose.glpi.yml logs glpi -f
```

### Useful Scripts

```bash
# Test disk monitoring script
./scripts/monitor_disk.sh --help
DISK_THRESHOLD=50 ./scripts/monitor_disk.sh --info

# Test GLPI ticket creation script  
python3 scripts/open_alert.py --test
echo '{"alert_type":"test","severity":"critical","hostname":"test-server","message":"Test alert"}' | python3 scripts/open_alert.py --json
```

## 🏃 Running Ansible Playbooks

```bash
# Install Docker (requires sudo access)
ansible-playbook -i localhost, infra/ansible/playbooks/docker_install.yml -c local -K

# Install Kubernetes tools
ansible-playbook -i localhost, infra/ansible/playbooks/k8s_tools.yml -c local -K

# Update system packages
ansible-playbook -i localhost, infra/ansible/playbooks/os_patch.yml -c local -K

# Create service user
ansible-playbook -i localhost, infra/ansible/playbooks/users.yml -c local -K
```

## 🔄 CI/CD Pipeline

The GitHub Actions workflow (`.github/workflows/ci.yaml`) provides:

- **Automated testing** of Python applications
- **YAML validation** for Kubernetes and monitoring configs
- **Security scanning** with Trivy
- **Docker image building** and publishing to GitHub Container Registry
- **Multi-stage pipeline** with proper dependencies

### Secrets Required

Set these secrets in your GitHub repository:
- `GITHUB_TOKEN` (automatically provided)

### Registry Images

Successfully built images are published to:
- `ghcr.io/your-username/your-repo/axity-lab-app:latest`
- `ghcr.io/your-username/your-repo/axity-webhook-receiver:latest`

## 📊 Key Metrics & Monitoring

### Prometheus Metrics
- **Application uptime**: `up{job="axity-lab-app"}`  
- **Response time**: `http_request_duration_seconds`
- **Webhook processing**: `webhook_alerts_received_total`

### Alert Rules
- **AppDown**: Application unreachable for >30 seconds
- **HighResponseTime**: 95th percentile >500ms for >2 minutes  
- **WebhookReceiverDown**: Webhook service unavailable

### GLPI Integration
- Automatic ticket creation with severity mapping
- Structured alert information in ticket descriptions
- Resolution notifications when alerts clear

## 🔒 Security Considerations

- All services run in isolated containers
- GLPI uses database authentication
- No services exposed to external networks in lab setup
- GitHub Actions uses secure token authentication
- Webhook receiver validates alert payloads

## 📈 Scaling & Production Notes

While this is a lab environment, production considerations include:

- **High Availability**: Multiple replicas for all services
- **Persistent Storage**: Volumes for Prometheus metrics and GLPI data
- **TLS/SSL**: HTTPS for all service communications  
- **Resource Limits**: CPU and memory constraints on containers
- **Backup Strategy**: Regular database and configuration backups
- **Network Security**: Service mesh or network policies

## 🛠️ Troubleshooting Guide

### Common Issues

1. **k3d cluster creation fails**:
   ```bash
   # Check Docker daemon is running
   docker version
   # Delete existing cluster if needed
   k3d cluster delete axity-lab
   ```

2. **Image pull issues in k3d**:
   ```bash
   # Ensure image exists locally
   docker images axity-lab-app:local
   # Re-import if needed
   k3d image import axity-lab-app:local --cluster axity-lab
   ```

3. **GLPI tickets not created**:
   - Verify API is enabled in GLPI configuration
   - Check App Token and User Token are correct
   - Review webhook receiver logs for API errors

4. **Prometheus can't scrape targets**:
   - Verify network connectivity between containers
   - Check Docker Compose networks configuration
   - Ensure applications expose metrics endpoints

### Health Check Commands

```bash
# System health
docker ps                              # All containers status
kubectl get all -A                     # Kubernetes resources
docker network ls                      # Docker networks

# Service health
curl -f http://localhost:8000/healthz  # App health
curl -f http://localhost:5000/health   # Webhook health
curl -f http://localhost:9090/-/healthy # Prometheus health
```

## 🎯 Learning Objectives

This lab demonstrates:

- **Infrastructure as Code** with Docker and Kubernetes manifests
- **Configuration Management** with Ansible playbooks
- **Container Orchestration** with k3d/Kubernetes  
- **Monitoring & Alerting** with Prometheus/AlertManager
- **ITSM Integration** with automated ticket creation
- **CI/CD Automation** with GitHub Actions
- **Observability** with structured logging and metrics

## 📝 Next Steps

- Add Grafana dashboards for visualization
- Implement Helm charts for easier deployment
- Add automated testing with pytest
- Configure log aggregation with ELK stack
- Implement GitOps with ArgoCD
- Add service mesh with Istio

---

**🎉 Enjoy exploring the Axity Infrastructure Operations Lab!**

For questions or issues, please check the logs, review the architecture documentation in `/diagrams/`, and ensure all prerequisites are installed correctly.