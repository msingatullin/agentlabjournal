# Admitad API integration for ALJ

Automated management of affiliate links: fetch active programs, generate deeplinks, update ALJ tools/recommendations page.

## What it does

1. Authenticates with Admitad API via OAuth2.
2. Fetches affiliate programs connected to your ad space (`website_id`).
3. Generates deeplinks for specific landing pages.
4. Updates `/root/agentlabjournal/tools.html` with active offers.

## What it does NOT do

- Place links into content automatically without rules.
- Guarantee income without traffic.

## Required credentials

Create a file `/root/agentlabjournal/scripts/admitad/.env` with:

```bash
ADMITAD_CLIENT_ID=your_client_id
ADMITAD_CLIENT_SECRET=your_client_secret
ADMITAD_WEBSITE_ID=your_ad_space_id
```

### How to get credentials

1. Log in to https://www.admitad.com/.
2. Go to Account → API → Create application (or API keys).
3. Copy `client_id` and `client_secret`.
4. Find your ad space ID (website ID) in the list of platforms.

**Never commit `.env` to git.** It is already ignored in `.gitignore` along with `venv/`.

Your ad space ID for this project is `2989069`.

## Install

```bash
cd /root/agentlabjournal/scripts/admitad
python3 -m venv venv
source venv/bin/activate
pip install requests
```

## Run

```bash
cd /root/agentlabjournal/scripts/admitad
source venv/bin/activate
python3 sync_tools.py
```

## Automation

Add to crontab or systemd timer to run weekly:

```bash
0 10 * * 1 cd /root/agentlabjournal/scripts/admitad && venv/bin/python sync_tools.py
```
