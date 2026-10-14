# Choosing Railway or OVH

Both recommended providers can run a relay for friends and family. One person owns the hosting account and manages access; everyone else imports a personal profile into an app.

| What matters to you | Railway | OVH |
| --- | --- | --- |
| Setup and upkeep | Railway manages the underlying server. | You rent a Linux server and maintain its software. |
| Main cost | Running the program plus the amount of data it sends. | A server rental fee; traffic charges or limits depend on the exact plan and region. |
| Need to buy a domain name? | No. Railway supplies a server name and HTTPS certificate. | No. The relay uses the server's numeric IP address. |
| Connection method | WebSocket over HTTPS: a continuing connection through Railway's secure web service. | REALITY: a secure connection method that works directly with the server's address. |
| Best starting point | You want less server administration and can monitor usage costs. | You want included traffic and are willing to maintain a server. |

An **IP address** is a computer's numeric address on the internet. A **domain name** is a readable name for an address. An **HTTPS certificate** lets compatible apps verify the server's identity when making an encrypted connection. The setup guides fill in the remaining connection details.

Choose a provider before generating access keys. Switching providers changes the connection method, so everyone will need a new profile. Neither choice guarantees access from every country, hotel, or mobile network; test the connection where people will actually use it.

## Railway: less server maintenance

Railway runs the relay in a **container**, a packaged copy of the program and the software it needs. It supplies the public server name and manages the HTTPS certificate.

Users connect on **port 443**, the numbered connection point normally used for secure websites. Railway forwards that connection to port 8080 inside the container. The profile handles this automatically. This setup avoids Railway's separate TCP proxy, which would give users a different, high-numbered public port. TCP is the underlying connection method used by both options here.

### What you pay for

Railway charges for **compute** (the processing power and memory used to run the program) and **egress** (data sent out of its service).

On **13 October 2026**, its published container egress rate was **$0.05 per GB**:

| Data sent in one month | Traffic charge alone |
| --- | --- |
| 100 GB | About $5 |
| 1 TB (1,000 GB) | About $50 |

These examples exclude compute and plan billing. A relay sends data out when forwarding uploads toward websites and downloads toward users. Use Railway's measured egress to estimate the bill; the number of people alone does not tell you their usage. Set a usage alert before sharing profiles, and check current [pricing](https://docs.railway.com/pricing/plans) and [cost controls](https://docs.railway.com/pricing/cost-control).

### Where to start

Choose a **region**, the location where Railway runs the relay, near the people using it. Distance is only a starting point: even nearby servers can have slow or unreliable connections on a particular network, especially during busy evening hours. Test from the networks your group actually uses.

Leave service sleeping/serverless behavior disabled so the relay stays available. Start with one **replica**, meaning one running copy of the service. Adding copies does not automatically make a long-running relay connection more reliable.

Continue with [the Railway setup guide](railway.md).

## OVH: included traffic and more owner responsibility

An OVH **VPS**, or virtual private server, is a Linux computer you rent. This template uses its public IP address and port 443 directly. Its REALITY connection method uses generated server keys, so you do not need to buy a domain or manage an HTTPS certificate.

### What “unlimited traffic” means

On **13 October 2026**, the [US VPS page](https://us.ovhcloud.com/vps/) advertised an entry plan from **$4.54/month**, with a **500 Mbps** connection and unlimited traffic. Mbps measures connection speed; GB and TB measure how much data you transfer over time. A higher speed limit does not promise that downloads will reach that speed.

For eligible plans, “unlimited traffic” means no charge per GB. The connection still has a speed limit, shares network capacity, and is subject to network-use policies. Some [Asia-Pacific plans](https://www.ovhcloud.com/en/vps/) instead have monthly allowances and reduce speed after the allowance is used. Do not apply the US headline to a Singapore quote.

Before paying, check the exact region and plan, total upfront payment, renewal price, tax, included public IPv4 address, traffic and speed limits, how long backups are kept, and cancellation conditions. The advertised starting price may depend on a longer commitment. A cheap European or North American server may also have a poor connection to your users.

### Check the applicable terms

OVH markets VPN use, but some service terms restrict anonymization or public proxy services, including VPNs. Restricting access to friends and family does not itself establish permission. Check the [terms for your contracting entity and product](https://us.ovhcloud.com/legal/service-specific-terms/) before buying; ask the provider if your intended family setup is unclear. This template does not resolve local legal or commercial licensing requirements.

### Which server to try

For a small trial, choose a fresh **Ubuntu 24.04 LTS, x86-64 VPS with a public IPv4**, initially on a short commitment:

- **Ubuntu 24.04 LTS** is the Linux operating-system version this setup targets. LTS means long-term support.
- **x86-64** is the processor type; choose that option rather than ARM for this guide.
- **Public IPv4** is an internet-reachable numeric address supplied by the provider.

The smallest offered machine is a starting point for a few people, not a tested capacity promise. Use a new server: a website already using port 443 would conflict with the relay. Keep **SSH**, the secure remote terminal used to manage the server, available while setting up.

Continue with [the OVH setup guide](ovh.md).

## Before inviting everyone

Try at least two real networks, including the intended location and busy hours. Test page loading, a small download, the apps people use, and several people connecting at once. Compare the provider's processing (**CPU**), memory, and traffic graphs during the test. More CPU helps when the server is running out of processing capacity; it cannot fix a blocked address, a Wi-Fi sign-in page, or a poor network connection between countries.

Then check recovery and access management. Make an encrypted backup, add a temporary person, remove their access, apply the change, and confirm their old profile cannot reconnect. On OVH, test a planned reboot after the first successful connection. Confirm that the owner can apply an update and recover from a failed one. Keep the previous code and a backup of the current private state before updating.

See [verification and pilot checks](verification.md) for the full checklist, or the [glossary](glossary.md) for unfamiliar terms.
