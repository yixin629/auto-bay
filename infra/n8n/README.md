# n8n Social Publish Bridge

This folder contains a ready-to-import n8n workflow for AutoBay social automation.

## File

- social_publish_bridge.workflow.json

## What It Does

- Exposes a POST webhook endpoint at:
  - /webhook/autobay/social-publish
- Accepts payload from AutoBay social automation
- Optionally validates Bearer token against `AUTOBAY_BRIDGE_TOKEN`
- Returns standardized JSON response envelope

## Import Steps

1. Open n8n.
2. Import workflow from social_publish_bridge.workflow.json.
3. Activate the workflow.
4. Copy the webhook production URL.

## Optional Auth Guard

If you want token enforcement in the workflow, set n8n env var:

`AUTOBAY_BRIDGE_TOKEN=<your-token>`

Then set the same token in AutoBay automation `publisher_config.token`.

## AutoBay Mapping

Set social automation publisher fields as:

- publisher_type: webhook_bridge
- publisher_config.endpoint: your n8n webhook production URL
- publisher_config.token: optional bearer token
- publisher_config.timeout_seconds: optional timeout

## Input Payload (from AutoBay)

The workflow accepts JSON payload with fields like:

- platform
- caption
- hashtags
- media_urls
- call_to_action
- credentials
- region

## Suggested Extension

Replace the Code node with real publishing logic, for example:

- Call your Douyin/Xiaohongshu automation API
- Upload media
- Create post
- Return publish_id and platform-specific response body

## Standard Response Shape

The workflow responds with:

```json
{
  "ok": true,
  "platform": "douyin",
  "publish_id": "pub_123",
  "message": "Accepted by n8n bridge",
  "error": null,
  "meta": {
    "caption_length": 12,
    "hashtag_count": 3,
    "media_count": 1
  }
}
```
