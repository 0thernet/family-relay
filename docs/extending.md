# Optional: understand or extend the relay

**You can skip this page for setup and everyday use.** Follow the [provider guides](providers.md), [client guide](clients.md), and [operations guide](operations.md) first. This page is for someone who wants to change the software or add monitoring later.

The features below are ideas for future development. They are not included unless the text explicitly describes current behavior. The [glossary](glossary.md) explains terms used elsewhere in the repository.

## How the current relay fits together

The owner runs `relay.py`, the included command-line tool. It maintains a **private state file**, which stores the deployment settings and everyone's access keys. From that file, it generates a configuration for the server and a separate profile for each person. Applying changes replaces the configuration used by the server. During normal use, people's apps connect to that server; the owner's computer and this repository do not need to stay online.

The **client** is the app on a person's phone or computer. The **transport** is the method that carries its connection to the server. A **port** is a numbered connection point at a server address. Both supported transports use public port 443, but their connection methods differ:

- **Railway:** client → Railway's HTTPS port 443 → relay inside a container → requested website or other destination. HTTPS encrypts the public connection and uses a trusted certificate to verify the server's identity. WebSocket keeps a connection open through that web service. Railway supplies the hostname and certificate, then forwards traffic to port 8080 inside the container. A container is the packaged program Railway runs; it has no custom certificate to renew.
- **OVH:** client → rented server's IP address, port 443, using REALITY → requested destination. REALITY is a secure connection method that verifies the server using generated keys. It uses a configured website during its disguised connection setup; ordinary relay traffic goes to the destinations the client requests. It does not turn the server's IP address into a browser-trusted HTTPS website or provide a web address for downloading profiles.

Both use **Xray**, the software that forwards the traffic. An **image** is the package from which a container starts. The Xray base image is **pinned**, meaning this repository names an exact engine image instead of automatically selecting the newest one. Each person has a separate **UUID**, a randomly generated identifier used here as an access key.

Both configurations block access to private/local network addresses and mail-sending ports. Keep these restrictions in place when extending the relay. The runtime has no public **administrative API**, a software interface for controlling the service. The transport differences are in `relay.py`; changing provider requires new client exports.

## Add monitoring gradually

**Monitoring** means regularly checking whether the service is working and what it costs. Start with provider billing alerts, restart counts, and processing, memory, and network graphs. On OVH, `--status` reports the container's health. Its health check only tests a **local listener**, meaning whether the relay is accepting connections inside the server. It does not establish that users can browse through it.

A future **end-to-end check** should behave like a real client: connect from another network, fetch a small file through the relay, and confirm the response. Give this monitor its own named user and keep its profile in a **secret store**, a protected location intended for passwords and access keys. Use a fixed test file on a server you control and record only the result, elapsed time, number of bytes, test location, and deployed version. Do not record connection keys or other users' browsing history.

Start with **alert-only** monitoring: it tells the owner about a problem without changing the service. Require repeated failures before sending an alert, and test again to recognize recovery. A single website rejecting a request does not establish that the relay needs a restart.

If you implement the monitor in **GitHub Actions**, GitHub's service for running automated tasks, use its **secrets** feature for credentials, not ordinary variables or source files. Keep test downloads small and notifications useful. Prove the alerts work before adding automatic repair. Any repair should preserve access keys, identify the exact deployment it may change, make one limited attempt, check whether service recovered, and stop if recovery failed.

## Possible later features

These additions require code and testing before users can rely on them.

| Feature | What it would provide | What the implementation must handle |
| --- | --- | --- |
| HTTPS subscriptions | A private web address from which an app can refresh its profile. | A separate, revocable access token for each person. A token is a password in the subscription address; each response must include only that person's profile. Never publish the private state or server keys. |
| Usage allowances | A limit on how much data each person can transfer. | Measure bytes and enforce the limit on the server. Naming a profile “100 GB” does not enforce anything. Accounting does not need browsing history. |
| Multiple hosts | More than one relay server, with a choice or backup when one fails. | Separate state for each server and explicit address selection. Test automatic switching from the users' networks before relying on it. |
| Additional transports | Another way for clients to connect. | Check that client and server settings agree, then import and test profiles in real apps. On OVH, two independent services cannot both listen at the same IP address and port 443. |
| Automatic updates | Install reviewed releases without a manual update each time. | Use identifiable release files that cannot change under the same version, preserve private state, verify health, and retain the exact previous container image for recovery. Avoid automatically pulling a changing `latest` image tag. |
| A provider deploy button | Start a fresh installation from a provider's website. | Generate fresh access keys, initialize multiple users, and let the owner retain and recover private state. A provider marketplace button needs its own setup and safety checks; publishing this repository does not create one. |

## Check a change before sharing it

Keep changes small. With the development tools listed in [verification](verification.md#reproduce-artifact-checks) installed, run the repository's check script from its root folder:

```sh
bash scripts/check.sh
```

This runs automated checks and builds a test container. It does not prove that a changed relay works from a particular hotel, country, or phone app. Repeat the relevant [pilot checks](verification.md#first-deployment-on-each-provider) after changing connection methods, startup, profile generation, access keys, or recovery. New optional features should require an explicit choice before they become active on an existing installation.
