# Cloud Asset Inventory Platform

An open-source Cloud Asset Intelligence Platform for AWS infrastructure with native LLM/Graph RAG integration. This tool serves as a CMDB and Asset Inventory to support the "Identify" function of the NIST Cybersecurity Framework.

## Project Status

**Current Phase:** Week 1 Foundation - Basic Asset Discovery via AWS Config ✅

### Completed Features

- ✅ Docker Compose environment (Neo4j + Redis)
- ✅ FastAPI backend with GraphQL API
- ✅ Neo4j graph database with schema
- ✅ AWS Config snapshot ingestion
- ✅ Core data models (Asset, Enrichment, Relationships)
- ✅ AWS profile-based authentication
- ✅ Australia/Sydney region configuration

## Architecture

```
┌─────────────────────────────────────────┐
│         FastAPI + GraphQL API            │
│     (Asset Queries & Collection)         │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│       Collection Service                 │
│  ┌────────────────────────────────────┐  │
│  │   AWS Config Collector             │  │
│  │   (S3 Snapshot Ingestion)          │  │
│  └────────────────────────────────────┘  │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│       Graph Service                      │
│  ┌────────────────────────────────────┐  │
│  │   Neo4j Graph Database             │  │
│  │   (Assets + Relationships)         │  │
│  └────────────────────────────────────┘  │
└─────────────────────────────────────────┘
```

## Prerequisites

- Docker & Docker Compose
- AWS CLI configured with appropriate profile
- AWS Config enabled with S3 bucket for snapshots
- Python 3.11+ (for local development)

## Quick Start

### 1. Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your AWS configuration
# Required settings:
# - AWS_REGION=ap-southeast-2 (already set)
# - AWS_PROFILE=your-aws-profile-name
# - AWS_CONFIG_BUCKET=your-config-bucket-name
```

### 2. Start Services

```bash
# Start all services
docker-compose up -d

# Check service health
docker-compose ps

# View logs
docker-compose logs -f backend
```

### 3. Verify Installation

**Check API Health:**
```bash
curl http://localhost:8000/health
```

**Access Neo4j Browser:**
- URL: http://localhost:7474
- Username: `neo4j`
- Password: `asset-inventory-dev`

**Access API Documentation:**
- Swagger UI: http://localhost:8000/docs
- GraphQL Playground: http://localhost:8000/graphql

## Usage

### Collect Assets from AWS Config

**Option 1: Trigger via API**
```bash
# Collect from latest snapshot
curl -X POST http://localhost:8000/api/collect/aws-config

# List available snapshots
curl http://localhost:8000/api/collect/snapshots

# Collect from specific snapshot
curl -X POST "http://localhost:8000/api/collect/aws-config?s3_key=AWSLogs/.../ConfigSnapshot.json.gz"
```

**Option 2: Using Python**
```python
import requests

# Trigger collection
response = requests.post("http://localhost:8000/api/collect/aws-config")
print(response.json())

# Expected output:
# {
#   "status": "completed",
#   "assets_collected": 150,
#   "assets_ingested": 150,
#   "duration_seconds": 12.5
# }
```

### Query Assets via GraphQL

**Get All Assets:**
```graphql
query GetAssets {
  assets(limit: 10) {
    id
    type
    name
    region
    accountId
    tags
    state
  }
}
```

**Filter Assets:**
```graphql
query FilteredAssets {
  assets(
    filter: {
      type: "ecs_service"
      region: "ap-southeast-2"
    }
    limit: 20
  ) {
    id
    name
    tags
    configuration
  }
}
```

**Get Database Stats:**
```graphql
query GetStats {
  stats {
    totalAssets
    totalEnrichments
    totalRelationships
  }
}
```

### Query Assets Directly in Neo4j

```cypher
// Get all assets
MATCH (a:Asset)
RETURN a
LIMIT 10

// Get assets by type
MATCH (a:Asset {type: 'ecs_service'})
RETURN a.name, a.region, a.state

// Get assets by region
MATCH (a:Asset {region: 'ap-southeast-2'})
RETURN a.type, count(*) as count
ORDER BY count DESC

// Get assets with specific tag
MATCH (a:Asset)
WHERE a.source_tags.Environment = 'production'
RETURN a.name, a.type
```

### Get Statistics

```bash
# Get database statistics
curl http://localhost:8000/stats

# Expected output:
# {
#   "total_assets": 150,
#   "total_enrichments": 0,
#   "total_relationships": 0,
#   "assets_by_type": [
#     {"type": "s3_bucket", "count": 45},
#     {"type": "ecs_service", "count": 30},
#     ...
#   ],
#   "assets_by_region": [
#     {"region": "ap-southeast-2", "count": 150}
#   ]
# }
```

## AWS Configuration

### Required IAM Permissions

Your AWS profile/role needs the following permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::your-config-bucket",
        "arn:aws:s3:::your-config-bucket/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "config:DescribeConfigurationRecorders",
        "config:DescribeDeliveryChannels"
      ],
      "Resource": "*"
    }
  ]
}
```

### AWS Config Setup

If AWS Config is not already enabled:

```bash
# Enable AWS Config (via AWS CLI)
aws configservice put-configuration-recorder \
  --configuration-recorder name=default,roleARN=arn:aws:iam::ACCOUNT:role/config-role \
  --recording-group allSupported=true,includeGlobalResourceTypes=true

# Set delivery channel
aws configservice put-delivery-channel \
  --delivery-channel name=default,s3BucketName=your-config-bucket

# Start recording
aws configservice start-configuration-recorder --configuration-recorder-name default
```

## Supported AWS Resource Types

Currently supported via AWS Config:

- **Compute:** ECS (Cluster, Service, Task Definition), EC2, Lambda
- **Storage:** S3, EFS, EBS
- **Database:** RDS, ElastiCache, DynamoDB
- **Networking:** VPC, Subnet, Security Group, NAT Gateway, Load Balancer
- **Security:** IAM (Role, Policy, User), KMS, WAF
- **Messaging:** SQS, SNS
- **Monitoring:** CloudWatch Alarms, Log Groups
- **CDN:** CloudFront

See `backend/app/models/enums.py` for complete list.

## Development

### Local Development (Without Docker)

```bash
# Install backend dependencies
cd backend
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -r requirements.txt

# Start Neo4j and Redis (via Docker)
docker-compose up -d neo4j redis

# Run backend
cd backend
uvicorn app.main:app --reload
```

### Running Tests

```bash
# Run backend tests
cd backend
pytest

# Run with coverage
pytest --cov=app tests/
```

### Database Management

**Clear all data:**
```bash
# Via Python
docker-compose exec backend python -c "from app.db import get_neo4j_client; get_neo4j_client().clear_database()"
```

**Backup database:**
```bash
# Stop Neo4j
docker-compose stop neo4j

# Backup data volume
docker run --rm -v asset-inventory_neo4j_data:/data -v $(pwd):/backup ubuntu tar czf /backup/neo4j-backup.tar.gz /data

# Restart Neo4j
docker-compose start neo4j
```

## Project Structure

```
asset-inventory/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   └── graphql/          # GraphQL schema & resolvers
│   │   ├── collectors/            # AWS data collectors
│   │   ├── db/                    # Database clients
│   │   ├── models/                # Data models
│   │   ├── services/              # Business logic
│   │   ├── config.py              # Configuration
│   │   └── main.py                # FastAPI app
│   ├── tests/
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/                       # (Coming in Week 5)
├── infrastructure/
│   └── terraform/                 # IaC (Coming later)
├── docs/
├── docker-compose.yml
├── .env.example
└── README.md
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `AWS_REGION` | AWS region | `ap-southeast-2` |
| `AWS_PROFILE` | AWS CLI profile | `default` |
| `AWS_CONFIG_BUCKET` | S3 bucket for AWS Config | *Required* |
| `AWS_AUTH_STRATEGY` | Auth method (`profile`, `roles_anywhere`, `iam_role`) | `profile` |
| `NEO4J_URI` | Neo4j connection URI | `bolt://localhost:7687` |
| `NEO4J_USER` | Neo4j username | `neo4j` |
| `NEO4J_PASSWORD` | Neo4j password | `asset-inventory-dev` |
| `REDIS_URL` | Redis connection URL | `redis://localhost:6379` |

## Troubleshooting

### Common Issues

**1. "Failed to connect to Neo4j"**
```bash
# Check if Neo4j is running
docker-compose ps neo4j

# Check Neo4j logs
docker-compose logs neo4j

# Restart Neo4j
docker-compose restart neo4j
```

**2. "AWS credentials not found"**
```bash
# Verify AWS profile
aws sts get-caller-identity --profile your-profile-name

# Check environment variables
docker-compose exec backend env | grep AWS
```

**3. "No assets collected from AWS Config"**
```bash
# Verify Config bucket access
aws s3 ls s3://your-config-bucket/AWSLogs/ --profile your-profile-name

# Check if Config is enabled
aws configservice describe-configuration-recorders --profile your-profile-name

# Check backend logs
docker-compose logs -f backend
```

**4. "Port already in use"**
```bash
# Change ports in docker-compose.yml
# Neo4j: 7474 -> 17474, 7687 -> 17687
# API: 8000 -> 18000
# Redis: 6379 -> 16379
```

## Roadmap

### Phase 1: Foundation (Current - Week 1) ✅
- [x] Basic asset collection from AWS Config
- [x] Graph database setup
- [x] GraphQL API
- [x] Docker environment

### Phase 2: Core CMDB (Weeks 2-4)
- [ ] Relationship mapping
- [ ] Graph visualization
- [ ] Web UI (React/Next.js)
- [ ] Multi-account support
- [ ] Direct API collectors (WAF, CloudFront)

### Phase 3: Enrichment Layer (Weeks 5-6)
- [ ] Local enrichment without AWS tag modification
- [ ] Rule-based enrichment engine
- [ ] Bulk enrichment operations
- [ ] Enrichment UI

### Phase 4: Compliance & NIST CSF (Weeks 7-8)
- [ ] NIST Cybersecurity Framework mapping
- [ ] Compliance dashboard
- [ ] Gap analysis

### Phase 5: LLM Integration (Weeks 9-10)
- [ ] Natural language queries
- [ ] Graph RAG implementation
- [ ] Automated documentation

## Contributing

This is currently in active development. Contributions welcome once we reach Phase 2!

## License

TBD - Planning Apache 2.0 or MIT for open source release.

## Support

For issues or questions, please create an issue in the GitHub repository.

## Authors

- Brenton O'Loughlin
