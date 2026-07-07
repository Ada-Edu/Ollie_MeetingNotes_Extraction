# How to Find Bedrock API Information

## Step-by-Step Guide

### Step 1: Identify Where You Got the API Key

**Question**: Where did this API key come from?

**Check these places**:

#### A. Email or Slack/Teams Message
- Search your email for "Bedrock" or "API Key"
- Look for messages from your DevOps/Platform team
- Check for subject lines like "AWS Access", "Bedrock Setup", "API Credentials"

#### B. Internal Portal/Dashboard
- Does your company have an internal developer portal?
- Common names: "Developer Portal", "Cloud Console", "API Gateway", "Service Catalog"
- Look for sections like:
  - "API Keys"
  - "AWS Services"
  - "Bedrock Access"
  - "AI/ML Services"

#### C. Confluence/Wiki/Documentation
- Search your company wiki for:
  - "Bedrock setup"
  - "AI model access"
  - "AWS Bedrock guide"
  - "GenAI platform"

#### D. Ask Your Team
Who to ask:
- **DevOps/Platform team**: They manage cloud resources
- **AI/ML team**: They might have set this up
- **Tech lead**: They should know the setup process
- **Colleague who used it before**: Ask "How did you set up Bedrock?"

**Questions to ask them**:
1. "Where do I find the Bedrock API documentation?"
2. "What endpoint should I use for Bedrock in af-south-1?"
3. "What model IDs are available?"
4. "Is this a custom proxy or direct AWS Bedrock?"

---

### Step 2: Look for Documentation

**Search for files on your machine**:

#### Windows Search (Win + S):
```
Search terms to try:
- "bedrock"
- "AWS guide"
- "API documentation"
- "model setup"
- ".pdf" in your Downloads folder
```

#### Check Common Locations:
```
C:\Users\Ollie.Olwage\Documents\
C:\Users\Ollie.Olwage\Downloads\
C:\Users\Ollie.Olwage\OneDrive\
Network drives (if any)
```

#### Look for files like:
- `Bedrock_Setup_Guide.pdf`
- `AWS_Access_Instructions.docx`
- `API_Keys.txt`
- `README.md` in related projects

---

### Step 3: Check If It's Standard AWS Bedrock

**Try AWS Console Access**:

1. **Open Browser**: Go to https://console.aws.amazon.com/
2. **Sign In**: 
   - If you have AWS credentials, sign in
   - If using SSO, use your company login

3. **Check Bedrock Access**:
   - Search for "Bedrock" in the AWS Console search bar
   - If you can access it:
     - Note the region (should be `af-south-1`)
     - Click "Model access" in left sidebar
     - See which models are enabled
     - Click "API request examples" for endpoint info

4. **Check IAM Credentials**:
   - Go to IAM → Users → Your User
   - Security credentials tab
   - Look for "Access keys"
   - If you have these, we can use standard AWS auth

**Take screenshots of**:
- Model access page
- Available model list
- Any API documentation you find

---

### Step 4: Check AWS CLI Configuration

**Open Command Prompt or PowerShell**:

```cmd
# Check if AWS CLI is installed
aws --version

# If installed, check configuration
aws configure list

# Try to list Bedrock models
aws bedrock list-foundation-models --region af-south-1

# Check if you have a profile configured
cat %USERPROFILE%\.aws\credentials
cat %USERPROFILE%\.aws\config
```

**Copy the output** and share it with me (remove any sensitive keys first!)

---

### Step 5: Look for Environment Variables

**Check existing environment variables**:

```cmd
# In Command Prompt, search for AWS or Bedrock variables
set | findstr /i "AWS"
set | findstr /i "BEDROCK"
```

**Look in**:
- System environment variables (Windows Settings → System → About → Advanced system settings → Environment Variables)
- Project-specific .env files
- Docker compose files
- CI/CD configuration (GitHub Actions, Jenkins, etc.)

---

### Step 6: Check Related Projects

**Do you have other projects using Bedrock?**

Look for:
```
# Search your code directories
cd C:\Users\Ollie.Olwage\
dir /s /b *.env | findstr -i "bedrock"
dir /s /b *bedrock* 
```

**In those projects, check**:
- `.env` files
- `config.py` or `config.js` files
- `docker-compose.yml`
- README files
- Example/template files

---

### Step 7: Test with Different Model IDs

**While we investigate, let's try common model IDs**:

Try these in order:
1. `anthropic.claude-v2`
2. `anthropic.claude-v2:1`
3. `anthropic.claude-3-sonnet-20240229-v1:0`
4. `anthropic.claude-3-haiku-20240307-v1:0`
5. `claude-3-sonnet` (simplified format)
6. `claude-v2` (simplified format)

**I can write a script** to test all of these automatically.

---

## Information to Provide Me

Once you find the information, tell me:

### Essential Info:
1. **Endpoint URL**: 
   - Is it `https://bedrock-runtime.af-south-1.amazonaws.com`?
   - Or something else like `https://bedrock.adaptit.com` or `https://api.company.com/bedrock`?

2. **Model ID format**: 
   - Example from documentation or working code
   - List of available models

3. **Authentication method**:
   - Bearer token in header?
   - AWS Signature Version 4?
   - Custom authentication?

### Nice to Have:
4. **Example request** (from docs or working code)
5. **Response format** (what the API returns)
6. **Rate limits or quotas**

---

## How to Share Info Safely

**For sensitive information**:

### API Keys/Secrets:
✅ **Safe to share with me**:
- The full API key (I already have it in .env)
- Model IDs
- Endpoint URLs (if not exposing internal infrastructure)
- Documentation/examples

❌ **Don't share publicly**:
- Don't post API keys in public Slack channels
- Don't commit them to public GitHub repos
- Don't share screenshots with keys visible on public forums

**You can share directly with me in this conversation** - it's private.

### Screenshots:
When sharing screenshots:
1. Use Windows Snipping Tool (Win + Shift + S)
2. Black out any sensitive info not needed (personal emails, other services)
3. Save to desktop
4. Tell me the path and I'll read it

---

## Quick Wins to Try First

**Before deep investigation, try these quick checks**:

### Quick Check 1: Ask a colleague
**Copy this message to them**:
> "Hey! I'm trying to use AWS Bedrock for a project. I have an API key that starts with 'ABSKQmVkcm9ja0FQSUtleS1idDh6...' for af-south-1. Do you know:
> 1. What endpoint I should call?
> 2. What model IDs are available?
> 3. Is there a setup guide or docs I should look at?"

### Quick Check 2: Check browser history
- Open browser history (Ctrl + H)
- Search for "bedrock" or "aws"
- You might find the portal where you got the key

### Quick Check 3: Check your notes/OneNote
- Search OneNote for "bedrock" or "aws"
- Check any onboarding notes
- Look for "setup" or "credentials" notes

---

## Still Stuck?

If you can't find the info, we have backup options:

### Option A: Try Azure OpenAI Instead
If you have Azure OpenAI access, we can use that:
```env
MODEL_PROVIDER=azure
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_DEPLOYMENT=gpt-4
```

### Option B: Request New Credentials
Ask your platform team:
> "I need AWS Bedrock access for the af-south-1 region. Can you provide:
> - IAM credentials (Access Key ID + Secret) OR
> - Bedrock API documentation for our internal setup
> I'm working on an AI action items extraction feature."

### Option C: Mock the Model Call
For development, we can mock the model response and build everything else first.

---

## Let Me Know

Tell me which step you're on:
- "I found docs at [location]"
- "I asked [person] and waiting for response"
- "I checked [place] but nothing there"
- "I have the endpoint, it's [URL]"
- "I'm stuck at step [number]"

I'll help you through it!
