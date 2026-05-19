# Roadmap

## Completed Phases

- Phase 1: Foundation Setup
- Phase 2: Policy and Risk Engine
- Phase 3: Terraform Modules
- Phase 4: Remote State Backend
- Phase 5: CLI Wizard
- Phase 6: First Real Deployment
- Phase 7: Drift Detection
- Phase 8: CI/CD Pipeline
- Phase 9: Templates and Documentation
- Phase 10: Serverless Database Expansion (DynamoDB)
- Phase 11: Drift Remediation
- Phase 12: Multi-User Collaboration (RBAC, approval workflows, audit trail)
- Phase 12.5: Role-Based CLI Authentication (GitHub token auth)
- Phase 13: OPA Integration (Rego policies, Python wrapper)
- Phase 14: Web UI Dashboard (FastAPI + Next.js, 7 pages)
- Phase 16: Web Terminal / CloudShell (WebSocket + xterm.js, 31 tests, RBAC-gated)

## In Progress

- Phase 15: UI/UX Polish & Extended Functionality

## Planned Phases

- **Phase 17: BYOC (Bring Your Own Credentials)** — Multi-tenant AWS credential management. Users provide their own AWS Access Key and Secret Key for deployments. Credentials stored in-memory only (zero-persistence), validated via STS, with session isolation.

## Future Considerations

- Multi-region deployment support
- Container orchestration (ECS/EKS modules)
- Cost anomaly ML detection
- SSO authentication (SAML/OIDC)
- Multi-cloud provider support (Azure/GCP)

## Notes

- The roadmap order is intentional and matches the current `PROGRESS.md`.
- Future work should preserve the existing rule-based, AWS-only design unless the roadmap changes first.