# Contributing to PDF Layout Analysis Engine

Thank you for your interest in contributing to PDF Layout Analysis Engine! This document provides guidelines and information for contributors.

## 🤝 How to Contribute

### Reporting Issues
- Use the GitHub issue tracker
- Provide detailed reproduction steps
- Include sample PDFs when possible (remove sensitive content)
- Specify your environment (OS, Python version, etc.)

### Suggesting Enhancements
- Open an issue with the "enhancement" label
- Describe the use case and expected behavior
- Consider the impact on existing functionality

### Code Contributions
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Commit your changes (`git commit -m 'Add amazing feature'`)
7. Push to the branch (`git push origin feature/amazing-feature`)
8. Open a Pull Request

## 🛠 Development Setup

### Prerequisites
- Python 3.8+
- Git
- Virtual environment (recommended)

### Setup
```bash
# Clone your fork
git clone https://github.com/your-username/pdf-layout-engine.git
cd pdf-layout-engine

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode
pip install -e ".[dev]"

# Run tests
pytest
```

## 📝 Code Style

### Python Style
- Follow PEP 8 guidelines
- Use type hints for function parameters and return values
- Write comprehensive docstrings
- Keep functions focused and small
- Use meaningful variable names

### Documentation
- Update README.md for user-facing changes
- Add docstrings for new functions/classes
- Include examples in docstrings
- Update API documentation

### Testing
- Write unit tests for new functionality
- Maintain or improve test coverage
- Test edge cases and error conditions
- Include integration tests for complex features

## 🧪 Testing Guidelines

### Running Tests
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src

# Run specific test file
pytest tests/test_figures.py

# Run with verbose output
pytest -v
```

### Test Structure
- Unit tests in `tests/unit/`
- Integration tests in `tests/integration/`
- Test data in `tests/data/`
- Use descriptive test names

## 📋 Pull Request Process

### Before Submitting
- [ ] Code follows style guidelines
- [ ] Tests pass locally
- [ ] Documentation updated
- [ ] No merge conflicts
- [ ] Commit messages are clear

### PR Description
- Describe what changes were made
- Explain why the changes were necessary
- Reference any related issues
- Include screenshots for UI changes
- List any breaking changes

### Review Process
- All PRs require review
- Address feedback promptly
- Keep PRs focused and small
- Update PR description if needed

## 🐛 Bug Reports

### Required Information
- Clear description of the bug
- Steps to reproduce
- Expected vs actual behavior
- Environment details
- Sample files (if applicable)

### Bug Report Template
```markdown
**Bug Description**
A clear description of what the bug is.

**To Reproduce**
Steps to reproduce the behavior:
1. Go to '...'
2. Click on '....'
3. Scroll down to '....'
4. See error

**Expected Behavior**
What you expected to happen.

**Environment**
- OS: [e.g. macOS, Windows, Linux]
- Python version: [e.g. 3.8.5]
- Package version: [e.g. 1.0.0]

**Additional Context**
Add any other context about the problem here.
```

## ✨ Feature Requests

### Guidelines
- Check existing issues first
- Provide clear use case
- Consider implementation complexity
- Think about backward compatibility

### Feature Request Template
```markdown
**Feature Description**
A clear description of the feature you'd like to see.

**Use Case**
Describe the problem this feature would solve.

**Proposed Solution**
Describe how you think this should work.

**Alternatives**
Describe any alternative solutions you've considered.

**Additional Context**
Add any other context or screenshots about the feature request.
```

## 📚 Documentation

### Types of Documentation
- **README.md**: Project overview and quick start
- **API Documentation**: Function and class references
- **Tutorials**: Step-by-step guides
- **Examples**: Code samples and use cases

### Writing Guidelines
- Use clear, concise language
- Include code examples
- Add diagrams for complex concepts
- Keep documentation up-to-date

## 🔒 Security

### Reporting Security Issues
- **DO NOT** open public issues for security vulnerabilities
- Email security issues to: security@pdf-layout-engine.org
- Include detailed reproduction steps
- Allow time for response before public disclosure

### Security Guidelines
- Never commit secrets or credentials
- Use secure coding practices
- Validate all inputs
- Keep dependencies updated

## 🏷 Release Process

### Version Numbering
- Follow Semantic Versioning (SemVer)
- MAJOR.MINOR.PATCH
- Breaking changes = MAJOR
- New features = MINOR
- Bug fixes = PATCH

### Release Checklist
- [ ] All tests pass
- [ ] Documentation updated
- [ ] Version number updated
- [ ] Changelog updated
- [ ] Release notes prepared

## 💬 Community Guidelines

### Code of Conduct
- Be respectful and inclusive
- Welcome newcomers
- Focus on constructive feedback
- Help others learn and grow

### Communication
- Use clear, professional language
- Be patient with questions
- Provide helpful responses
- Stay on topic

## 📞 Getting Help

### Resources
- GitHub Issues: Bug reports and feature requests
- GitHub Discussions: General questions and ideas
- Documentation: Comprehensive guides and references
- Examples: Code samples and tutorials

### Response Times
- Bug reports: 1-3 business days
- Feature requests: 1-2 weeks
- General questions: 2-5 business days

## 🙏 Recognition

Contributors will be recognized in:
- CONTRIBUTORS.md file
- Release notes
- Project documentation
- GitHub contributor list

Thank you for contributing to PDF Layout Analysis Engine! 🚀
