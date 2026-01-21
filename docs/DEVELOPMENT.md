# Development Workflow

## Branching Strategy

### Feature Development
- **Always develop on feature branches** - never commit directly to `main`
- Branch naming convention: `feature/description` or `feature/issue-number`
- Example: `feature/seats-api-integration`, `feature/deal-aggregation`

## Testing Environment

### Testing Workflow
1. **Push feature branch** for review
2. **Manual testing** of full user workflows  
3. **PR review** after testing confirms functionality
4. **Merge to main** after approval

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