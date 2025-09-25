## Description
Brief description of the changes in this PR.

## Type of Change
- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update
- [ ] Refactoring (no functional changes)

## How Has This Been Tested?
- [ ] Existing tests pass
- [ ] Added new tests for new functionality
- [ ] Manually tested the changes
- [ ] API documentation updated (if applicable)

## Checklist
- [ ] My code follows the project's coding standards
- [ ] I have performed a self-review of my code
- [ ] I have commented my code, particularly in hard-to-understand areas
- [ ] I have made corresponding changes to the documentation
- [ ] My changes generate no new warnings
- [ ] Any dependent changes have been merged and published

## Automated Tests
🤖 **Automated tests will run when this PR is created/updated:**
- **Unit Tests**: All test functions in `tests.py` will be executed
- **Flask App Validation**: Checks that the app can start without errors
- **Multi-Python Testing**: Tests run on Python 3.9, 3.10, and 3.11
- **Coverage Report**: Test coverage analysis (when available)

If tests fail, check the "Actions" tab for detailed error information.

## API Documentation
If you've added or modified API endpoints:
- [ ] Updated documentation in `docs/swagger_docs.py`
- [ ] Tested endpoints using the interactive docs at `/docs/`
- [ ] Added proper request/response models
- [ ] Included example values and descriptions

## Environment Variables
If you've added new environment variables:
- [ ] Updated `.env.local` template in README
- [ ] Added to GitHub Secrets (for maintainers)
- [ ] Documented in the README