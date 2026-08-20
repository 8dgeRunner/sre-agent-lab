# Contabo Platform Deployment

The current Contabo host uses a single-node `kind` cluster (`coagent-demo`), not
k3s. The platform runs as the `sre` user's systemd service on `127.0.0.1:18080`
and is published through the existing Cloudflare tunnel as:

```text
https://sre-lab.8dgerunner.xyz
```

For people, use the web page. It provides a normal username/password login and
keeps the session in an `HttpOnly` cookie; participants do not type Bearer Tokens
for every request. The current trial account is stored in the Contabo-only env
file and should be shared through a private channel.

The live deployment directory is `/home/sre/sre-agent-lab`.

The platform API is a standard-library Python service and should be placed behind
an HTTPS reverse proxy. Initial private trial can run behind VPN with no token:

```bash
ssh contabo
systemctl --user status sre-lab.service
curl -H "Authorization: Bearer $LAB_ACCESS_TOKEN" \
  https://sre-lab.8dgerunner.xyz/v1/cases
```

The access token is stored on Contabo at
`/home/sre/.config/sre-lab/env` with mode `0600`; HMAC remains disabled for the
initial trial. `LAB_WEB_USERNAME` and `LAB_WEB_PASSWORD` are the human login;
`LAB_ACCESS_TOKEN` remains for Agent integrations. The process handles independent offline runs concurrently. Chaos
Mesh is installed in `chaos-mesh`, while workloads and experiments are restricted
by procedure to `chaos-lab`.
