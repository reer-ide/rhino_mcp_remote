# RhinoMCP System Architecture Design Document

**Version**: 1.0  
**Date**: December 2024  
**Status**: Beta Development

## Executive Summary

RhinoMCP is a remote Model Context Protocol (MCP) server that enables AI-assisted CAD modeling by connecting host applications (like Claude Desktop) with users' local Rhino CAD instances. This document outlines the system architecture for the beta launch on Google Cloud Run.

## System Overview

### Architecture Diagram

```
┌─────────────────┐         ┌──────────────────┐         ┌─────────────────┐
│  Host Apps      │         │  RhinoMCP Server │         │  Rhino Plugin   │
│  (Claude, etc)  │◄───────►│  (Cloud Run)     │◄───────►│  (Local CAD)    │
└─────────────────┘         └──────────────────┘         └─────────────────┘
        │                            │                            │
        │                            ▼                            │
        │                   ┌──────────────────┐                │
        │                   │   Redis Cluster   │                │
        │                   │  (Memorystore)    │                │
        │                   └──────────────────┘                │
        │                            │                            │
        │                            ▼                            │
        │                   ┌──────────────────┐                │
        └──────────────────►│   PostgreSQL     │◄───────────────┘
                           │  (Cloud SQL)      │
                           └──────────────────┘
```

### Core Components

1. **RhinoMCP Server** (Node.js/TypeScript on Cloud Run)
   - WebSocket server for bidirectional communication
   - MCP protocol implementation
   - Authentication and session management
   - Message routing for multiple CAD instances

2. **Redis Cluster** (Google Memorystore)
   - WebSocket session state storage
   - Real-time message pub/sub
   - Connection mapping (user → instances)
   - Temporary operation cache

3. **PostgreSQL Database** (Cloud SQL)
   - User profiles and authentication data
   - CAD project metadata
   - Operation history and audit logs
   - Configuration and settings

4. **Rhino Plugin** (Client-side)
   - WebSocket client implementation
   - MCP message handling
   - RhinoScriptSyntax command execution
   - Local state management

## Technical Stack

### Backend Technologies
- **Runtime**: Node.js 20.x with TypeScript 5.x
- **Framework**: FastMCP for MCP implementation
- **WebSocket**: ws library (production-ready, 100K connections)
- **Authentication**: JWT with OAuth 2.0
- **ORM**: Prisma for PostgreSQL
- **Redis Client**: ioredis with clustering support
- **Logging**: Winston with Google Cloud Logging
- **Monitoring**: Prometheus metrics export

### Infrastructure
- **Container**: Docker with multi-stage builds
- **Orchestration**: Google Cloud Run (auto-scaling)
- **Load Balancer**: Google Cloud Load Balancing
- **CDN**: Cloud CDN for static assets
- **Secrets**: Google Secret Manager

## Data Flow Architecture

### Connection Establishment Flow
```
1. User installs Rhino plugin and obtains auth token
2. Plugin initiates WebSocket connection to server
3. Server validates token in first message
4. Server creates session in Redis with instance mapping
5. Server acknowledges connection with session ID
6. Plugin ready for MCP commands
```

### Multi-Instance Message Routing
```
1. Host app sends MCP request with target instance_id
2. Server looks up instance in Redis session store
3. Server routes message to correct Rhino instance
4. Rhino executes command and returns response
5. Server correlates response with original request
6. Server returns response to host app
```

### State Synchronization
```
1. All state changes publish to Redis pub/sub
2. Relevant instances receive state updates
3. Conflict resolution via timestamp ordering
4. Periodic state snapshots to PostgreSQL
```

## Scalability Design

### Horizontal Scaling Strategy
- **Auto-scaling**: 1-10 Cloud Run instances based on:
  - CPU utilization > 70%
  - Concurrent connections > 80
  - Memory usage > 80%
- **Session Affinity**: Sticky sessions via connection ID
- **Load Distribution**: Round-robin with health checks

### Connection Limits
- **Per Instance**: 100 concurrent WebSocket connections
- **Per User**: 5 concurrent Rhino instances
- **Message Size**: 1MB maximum per MCP message
- **Timeout**: 30 minutes idle before disconnect

### Performance Targets
- **Connection Latency**: < 100ms establishment
- **Message Latency**: < 50ms routing overhead
- **Throughput**: 1000 messages/second per instance
- **Availability**: 99.5% uptime for beta

## Security Architecture

### Authentication Flow
```typescript
// Token structure
interface AuthToken {
  sub: string;          // User ID
  email: string;        // User email
  scope: string[];      // Permissions
  exp: number;          // Expiration timestamp
  instance_limit: number; // Max Rhino instances
}
```

### Security Measures
1. **TLS 1.3** for all WebSocket connections
2. **JWT tokens** with 24-hour expiration
3. **Rate limiting**: 100 requests/minute per user
4. **Input validation** for all MCP commands
5. **Audit logging** for sensitive operations

## Error Handling

### Retry Strategy
- **Connection failures**: Exponential backoff (1s, 2s, 4s, 8s, max 60s)
- **Message failures**: 3 retries with 1s delay
- **Database failures**: Circuit breaker pattern
- **Redis failures**: Fallback to local cache

### Error Codes
```
1000-1999: Authentication errors
2000-2999: Connection errors
3000-3999: MCP protocol errors
4000-4999: CAD operation errors
5000-5999: Server errors
```

## Monitoring and Observability

### Key Metrics
- **Business Metrics**:
  - Active users
  - CAD operations per minute
  - Average session duration
  - Instance utilization

- **Technical Metrics**:
  - WebSocket connections
  - Message latency p50/p95/p99
  - Error rates by category
  - Database query performance

### Logging Strategy
```typescript
// Structured logging format
{
  "timestamp": "2024-12-01T10:00:00Z",
  "level": "info",
  "service": "rhinomcp-server",
  "user_id": "user123",
  "instance_id": "rhino_001",
  "operation": "create_sphere",
  "duration_ms": 45,
  "status": "success"
}
```

## Development Considerations

### AI-Assisted Development
- **Code Structure**: Modular design for easy AI comprehension
- **Documentation**: Inline comments for context
- **Type Safety**: Comprehensive TypeScript interfaces
- **Testing**: Example-driven test cases for AI training

### Local Development Setup
```bash
# Docker Compose services
- rhinomcp-server (port 8080)
- redis (port 6379)
- postgres (port 5432)
- rhino-simulator (port 8081)
```

## Deployment Pipeline

### CI/CD Workflow
1. **Code Push** → GitHub repository
2. **Build** → Cloud Build triggers Docker build
3. **Test** → Automated unit and integration tests
4. **Deploy** → Cloud Run revision deployment
5. **Verify** → Health check and smoke tests
6. **Rollback** → Automatic on failure

### Environment Configuration
```yaml
# Beta environment variables
NODE_ENV: production
PORT: 8080
REDIS_URL: redis://memorystore-endpoint
DATABASE_URL: postgresql://cloudsql-endpoint
JWT_SECRET: (from Secret Manager)
MAX_CONNECTIONS_PER_INSTANCE: 100
MAX_INSTANCES_PER_USER: 5
```

## Migration and Rollback

### Database Migrations
- **Tool**: Prisma Migrate
- **Strategy**: Forward-only migrations
- **Rollback**: New migration to revert changes
- **Testing**: Migration dry-run in staging

### Service Rollback
- **Cloud Run**: Instant traffic shift to previous revision
- **Database**: Point-in-time recovery within 7 days
- **Redis**: Backup every 6 hours

## Future Considerations

### Post-Beta Enhancements
1. **Multi-region deployment** for global latency optimization
2. **Kubernetes migration** for advanced orchestration
3. **GraphQL API** for complex queries
4. **WebRTC** for direct peer-to-peer CAD streaming
5. **AI model integration** for intelligent command suggestions

### Technical Debt Items
1. Implement connection pooling optimization
2. Add comprehensive integration test suite
3. Enhance monitoring with distributed tracing
4. Implement advanced caching strategies
5. Add support for CAD file streaming

---

**Document Maintenance**: This architecture document should be updated with each significant system change. All modifications require team review and approval.