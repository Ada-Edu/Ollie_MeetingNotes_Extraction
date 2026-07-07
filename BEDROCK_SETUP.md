# AWS Bedrock Setup Guide

## Current Status

**API Key Format Detected**: `BedrockAPIKey-{id}-at-{account}:{token}`

**Configuration**:
- Region: `af-south-1`
- API Key: `[REDACTED]` (base64 encoded bearer token)
- Set via environment variable: `AWS_BEARER_TOKEN_BEDROCK`

## Issue

Testing the standard AWS Bedrock endpoint returns:
```
400 Bad Request
{"message":"The provided model identifier is invalid."}
```

## Possible Causes

1. **Custom Bedrock Proxy**: The API key format suggests this might be for a managed Bedrock service or proxy (not direct AWS Bedrock)
2. **Different Endpoint**: May need a different base URL (not `https://bedrock-runtime.{region}.amazonaws.com`)
3. **Model ID Format**: The model IDs available in your environment might be different
4. **Authentication Method**: Might need different headers or authentication approach

## Next Steps

Please provide:

1. **Source of API Key**: Where did you get this key? (AWS Console, AdaptIT portal, internal tool?)
2. **Documentation**: Any docs or examples for using this API key?
3. **Endpoint URL**: What's the correct endpoint to call?
4. **Available Models**: What model IDs are available in your environment?

## Alternative: Use AWS IAM Credentials

If you have standard AWS credentials (Access Key ID + Secret Access Key), we can use those instead:

```env
MODEL_PROVIDER=bedrock
AWS_REGION=af-south-1
AWS_ACCESS_KEY_ID=YOUR_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY=YOUR_SECRET_ACCESS_KEY
BEDROCK_MODEL_ID=anthropic.claude-3-5-sonnet-20240620-v1:0
```

## Supported Model IDs (Standard AWS Bedrock)

For reference, standard AWS Bedrock model IDs are:
- `anthropic.claude-3-5-sonnet-20240620-v1:0` (Claude 3.5 Sonnet)
- `anthropic.claude-3-opus-20240229-v1:0` (Claude 3 Opus)
- `anthropic.claude-3-sonnet-20240229-v1:0` (Claude 3 Sonnet)
- `anthropic.claude-3-haiku-20240307-v1:0` (Claude 3 Haiku)
- `anthropic.claude-v2:1` (Claude 2.1)
- `anthropic.claude-v2` (Claude 2)

Note: Model availability varies by region.
