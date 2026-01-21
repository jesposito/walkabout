# Development Workflow

## Branching Strategy

### Feature Development
- **Always develop on feature branches** - never commit directly to `main`
- Branch naming convention: `feature/description` or `feature/issue-number`
- Example: `feature/seats-api-integration`, `feature/deal-aggregation`

### CI/CD Pipeline
- **Continuous Integration triggers on all pushes** to GitHub (any branch)
- CI pipeline runs:
  - Linting and code quality checks
  - Unit tests
  - Integration tests
  - Docker build verification
  - Security scanning

## Testing Environment

### Unraid Testing Infrastructure
- **Test deployments on Unraid machine** (`ansiblenet` network)
- CI builds are automatically available for deployment testing
- Use built Docker images from CI for consistent testing environment

### Testing Workflow
1. **Push feature branch** → triggers CI build
2. **CI completes** → Docker images available in registry
3. **Deploy to Unraid test environment** for integration testing
4. **Manual testing** of full user workflows
5. **PR review** after testing confirms functionality
6. **Merge to main** after approval

## Local Development
- Use `docker-compose.yml` for local development
- Hot reload enabled for rapid iteration
- Local environment should mirror production as closely as possible

## Environment Promotion
- **Development** → Feature branches + local Docker
- **Testing** → Unraid ansiblenet deployment with CI builds
- **Production** → Main branch deployment to production Unraid

## Pre-commit Checklist
- [ ] Tests pass locally
- [ ] Linting passes
- [ ] Feature branch is up to date with main
- [ ] Docker build succeeds
- [ ] Environment variables documented in `.env.example`