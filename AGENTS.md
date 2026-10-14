# Contents

- `relay.py` manages private deployment state, people, server configuration, and client exports.
- `Dockerfile`, `compose.yaml`, `railway.json`, `docker/`, and `scripts/` package and run the relay.
- `docs/` contains provider setup, client instructions, and the operations guide.
- `tests/` contains offline credential, configuration, and lifecycle regression tests.

# Guidelines

- Write setup and usage guides for someone new to terminals and servers. Explain the purpose of each step, where commands run, and what success looks like. Define technical terms on first use and link the glossary; reserve implementation detail for clearly marked advanced sections.
- This is a public, multi-user template for independent deployments. Recommend Railway and OVH. Keep the project self-contained and documentation country-neutral, with no references to originating projects or deployments.
- Never commit `.relay/`, real credentials, generated client profiles, or provider variables. Public source must never contain deployment secrets, and a private source copy is not secret storage either.
- Give every person or device a distinct UUID. Revocation must remove that identity from the server. Do not introduce a shared fallback credential that defeats revocation.
- Preserve verified TLS on Railway. OVH REALITY uses its public key and server name; never add `allowInsecure` or `skip-cert-verify` to make connectivity pass.
- Preserve private-network and mail-port blocks. Do not expose a management or statistics API publicly.
- Keep shell examples literal, bound subprocesses, avoid shell interpolation, write private state atomically, and fail without printing secrets.
- Run focused tests while editing. Final gate: `python3 -m unittest discover -s tests -v`, shell syntax validation, and the container check in CI. Use the installed host scheduler for broad local checks and container builds. A local container validation does not establish live provider operation or compatibility with a particular network or client app.
- Use one independently reviewed branch for changes after the initial repository bootstrap. Do not bypass required checks. Never deploy into somebody else's existing server or relay while testing this template.
