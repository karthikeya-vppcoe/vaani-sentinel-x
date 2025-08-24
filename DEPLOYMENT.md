# Vaani Sentinel X - Production Deployment Guide

## Quick Start (Production)

### 1. Prerequisites
- Docker & Docker Compose
- Python 3.8+ (for development)
- 4GB+ RAM recommended
- 10GB+ disk space

### 2. Production Deployment

```bash
# Clone and setup
git clone https://github.com/karthikeya-vppcoe/vaani-sentinel-x.git
cd vaani-sentinel-x

# Quick deployment with script
chmod +x scripts/deploy.sh
./scripts/deploy.sh
```

### 3. Manual Deployment

```bash
# 1. Environment configuration
cp .env.template .env
# Edit .env with your API keys and configuration

# 2. Install dependencies (for testing)
pip install -r requirements.txt

# 3. Run health check
python cli/command_center.py health

# 4. Test all agents
python scripts/test_agents.py

# 5. Build and deploy
docker-compose up -d
```

## Development Setup

```bash
# Install dependencies
make setup-dev

# Run health check
make health

# Test all agents
make test-agents

# Run development environment
make docker-dev
```

## System Health & Monitoring

### Health Check
```bash
# Command line health check
python cli/command_center.py health

# Or using make
make health
```

### Agent Testing
```bash
# Test all agents individually
python scripts/test_agents.py

# Or using make  
make test-agents
```

### Monitoring
- Prometheus metrics: http://localhost:9090
- Application logs: `docker-compose logs -f vaani-app`
- System metrics: `docker stats`

## Production Configuration

### Required Environment Variables
```bash
# Security (REQUIRED)
JWT_SECRET=your-jwt-secret-minimum-32-chars
SECRET_KEY=your-flask-secret-minimum-32-chars

# AI APIs (REQUIRED for full functionality)
GROQ_API_KEY=your-groq-api-key
GOOGLE_API_KEY=your-google-api-key

# Optional APIs
ELEVENLABS_API_KEY=your-elevenlabs-api-key
OPENAI_API_KEY=your-openai-api-key
```

### Security Hardening
1. **Change default passwords** in .env
2. **Enable SSL/TLS** in nginx configuration
3. **Configure firewall** rules
4. **Set up log monitoring**
5. **Regular security updates**

### Performance Tuning
1. **Resource limits** in docker-compose.yml
2. **Database optimization** for PostgreSQL
3. **Redis caching** configuration
4. **Nginx rate limiting**

## Troubleshooting

### Common Issues

1. **Health check fails**
   ```bash
   # Check dependencies
   pip install -r requirements.txt
   
   # Check directory permissions
   chmod 755 logs/ content/ data/
   ```

2. **Agent tests fail**
   ```bash
   # Check individual agent
   python agents/miner_sanitizer.py --help
   
   # Check logs
   cat logs/agent_tester.log
   ```

3. **Docker issues**
   ```bash
   # Rebuild image
   docker-compose down
   docker-compose build --no-cache
   docker-compose up -d
   ```

### Log Locations
- Application logs: `logs/`
- Docker logs: `docker-compose logs`
- Nginx logs: `docker volume inspect vaani_nginx_logs`

## API Endpoints

### Health Check
- `GET /health` - Basic health check
- `GET /cli-health` - Comprehensive health check

### Agent Management
- `POST /api/agents/run` - Run specific agent
- `POST /api/agents/pipeline` - Run full pipeline
- `GET /api/agents/status` - Get agent status

## Scaling & Production Considerations

### Horizontal Scaling
- Multiple application instances behind load balancer
- Shared Redis for session management
- Centralized PostgreSQL database

### Monitoring & Alerting
- Prometheus + Grafana for metrics
- ELK stack for log aggregation
- Health check monitoring
- Resource usage alerts

### Backup & Recovery
- Automated database backups
- Content archive backups
- Configuration backup
- Disaster recovery plan

## Support

For issues and support:
1. Check this deployment guide
2. Review logs for errors
3. Run health check and agent tests
4. Open GitHub issue with details