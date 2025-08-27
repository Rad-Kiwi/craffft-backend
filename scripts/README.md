# Scripts Directory

This directory contains utility scripts for managing the Craffft Backend application.

## Available Scripts

### 🔐 Authentication Scripts

#### `generate_admin_password.py`
Generates SHA256 password hashes for admin authentication.

**Usage:**
```bash
python scripts/generate_admin_password.py
```

**Features:**
- Interactive password hash generation
- Password verification against existing hashes
- Secure password input (hidden typing)
- Ready-to-use .env format output

**Example:**
```bash
cd /path/to/craffft-backend
python scripts/generate_admin_password.py

# Follow prompts to generate hash
# Copy the generated hash to your .env file:
# ADMIN_PASSWORD_HASH=your_generated_hash_here
```

## Usage Notes

- Run scripts from the project root directory
- Make sure your virtual environment is activated
- Never commit generated passwords or hashes to version control
- Use strong, unique passwords for production environments

## Adding New Scripts

When adding new utility scripts:

1. Place them in this `scripts/` directory
2. Add a description to this README
3. Include usage examples
4. Follow the naming convention: `action_description.py`
5. Include proper error handling and user feedback

## Security Considerations

- Scripts that generate secrets should never log or store them
- Use `getpass` for password input to avoid terminal history
- Validate all user inputs
- Provide clear warnings about security best practices
