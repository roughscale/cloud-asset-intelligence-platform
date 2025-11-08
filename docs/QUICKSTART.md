# Quick Start Guide

Get your Cloud Asset Inventory Platform running in 5 minutes!

## Prerequisites Checklist

- [ ] Docker and Docker Compose installed
- [ ] AWS CLI configured with a profile
- [ ] AWS Config enabled with S3 bucket
- [ ] IAM permissions for S3 read access to Config bucket

## Step-by-Step Setup

### 1. Clone and Configure (2 minutes)

```bash
cd /home/boloughlin/projects/roughscale/asset_inventory

# Create .env file from template
cp .env.example .env
```

Edit `.env` and set:
```bash
AWS_PROFILE=your-aws-profile-name
AWS_CONFIG_BUCKET=your-aws-config-bucket-name
```

### 2. Start the Platform (2 minutes)

```bash
# Start all services
docker-compose up -d

# Wait for services to be healthy (30-60 seconds)
docker-compose ps

# Check logs
docker-compose logs -f backend
```

You should see:
```
✓ Neo4j connection verified
✓ Redis connection verified
✓ Database stats: 0 assets
```

### 3. Verify Installation (1 minute)

**Test API:**
```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "version": "0.1.0",
  "services": {
    "neo4j": "healthy",
    "redis": "healthy"
  }
}
```

**Access Neo4j Browser:**
- Open http://localhost:7474
- Username: `neo4j`
- Password: `asset-inventory-dev`

**Access API Docs:**
- Swagger: http://localhost:8000/docs
- GraphQL: http://localhost:8000/graphql

### 4. Collect Your First Assets (30 seconds)

```bash
# Trigger collection from AWS Config
curl -X POST http://localhost:8000/api/collect/aws-config

# Or use Python
python3 << EOF
import requests
response = requests.post("http://localhost:8000/api/collect/aws-config")
print(response.json())
EOF
```

Expected output:
```json
{
  "status": "completed",
  "assets_collected": 150,
  "assets_ingested": 150,
  "assets_failed": 0,
  "duration_seconds": 12.5
}
```

### 5. Query Your Assets

**Via REST API:**
```bash
# Get statistics
curl http://localhost:8000/stats

# Expected output shows assets by type and region
```

**Via GraphQL:**

Visit http://localhost:8000/graphql and run:

```graphql
query {
  assets(limit: 5) {
    id
    type
    name
    region
    tags
  }

  stats {
    totalAssets
  }
}
```

**Via Neo4j Browser:**

Open http://localhost:7474 and run:

```cypher
MATCH (a:Asset)
RETURN a.type, count(*) as count
ORDER BY count DESC
```

## What You've Built

Congratulations! You now have:

✅ **Graph Database** - Neo4j storing your AWS infrastructure
✅ **Asset Collection** - Automated ingestion from AWS Config
✅ **GraphQL API** - Query your assets programmatically
✅ **REST API** - Trigger collections and get stats
✅ **Data Models** - Assets with enrichment support

## Next Steps

1. **Explore Your Assets:**
   - Browse in Neo4j Browser
   - Query via GraphQL Playground
   - Check out the API docs

2. **Schedule Regular Collections:**
   - Set up a cron job or Lambda to trigger `/api/collect/aws-config`
   - Or use Celery (already configured) for scheduled tasks

3. **Customize for Your Environment:**
   - Add more AWS resource types
   - Create enrichment rules
   - Build custom queries

4. **Move to Phase 2:**
   - Add relationship mapping
   - Build the web UI
   - Implement direct API collectors

## Troubleshooting

### Services won't start
```bash
# Check for port conflicts
lsof -i :7474  # Neo4j
lsof -i :7687  # Neo4j Bolt
lsof -i :6379  # Redis
lsof -i :8000  # API

# Or change ports in docker-compose.yml
```

### Can't connect to AWS
```bash
# Test AWS access
aws sts get-caller-identity --profile your-profile-name

# Test S3 access
aws s3 ls s3://your-config-bucket/AWSLogs/ --profile your-profile-name
```

### No assets collected
```bash
# Check if AWS Config has data
aws s3 ls s3://your-config-bucket/AWSLogs/ --recursive | grep ConfigSnapshot

# Check backend logs
docker-compose logs backend | grep -i error
```

## Stopping the Platform

```bash
# Stop all services
docker-compose down

# Stop and remove all data (careful!)
docker-compose down -v
```

## Getting Help

- Check the main [README.md](../README.md)
- Review [architecture docs](./architecture.md) (coming soon)
- Check backend logs: `docker-compose logs backend`
- Check Neo4j logs: `docker-compose logs neo4j`

---

**Estimated Setup Time:** 5 minutes
**Estimated Time to First Assets:** 6 minutes

Happy asset discovering! 🚀
