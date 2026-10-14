# Terms you may see

You do not need to memorize these. Follow a setup guide, then come back here when an unfamiliar word appears. The names in code blocks must still be typed exactly as shown, with the specified placeholders replaced.

## The basic pieces

| Term | What it means here |
| --- | --- |
| Relay / proxy | A computer that forwards your internet connections. Websites receive those connections from the relay. |
| Server / host | The rented computer running the relay. “Host” can also mean its internet address in a command. |
| Provider | The company you rent hosting from: Railway or OVH. |
| VPS | Virtual private server: a rented Linux computer you control remotely. The OVH guide uses one. |
| Repository / repo | The project's source files and change history on GitHub. A template lets someone make a separate copy. |
| Deployment | A running copy of the relay on your provider. To deploy is to upload or install the software and start it. |
| Client / profile | The client is an app such as V2Box. A profile is the saved connection settings it uses. |
| Credential / UUID | A credential is a secret that grants access. This relay uses a randomly generated identifier called a UUID as each person's connection key; treat it like a password. |
| Rotate / revoke | Rotate means replace a connection key. Revoke means remove access. Both require applying the change to the server. |
| State | The saved private settings, including everyone's keys, in `.relay/state.json`. This is what you back up. |

## Commands and setup

| Term | What it means here |
| --- | --- |
| Terminal / shell / CLI | A terminal is the app where you type commands; a shell interprets them. A command-line interface (CLI) is a tool you operate this way. |
| Python | The programming tool that runs this template's `relay.py` commands. You do not need to learn Python to use them. |
| WSL | Windows Subsystem for Linux: a way to run Ubuntu inside Windows. Required for the Railway owner's setup commands on Windows, not for friends using client apps. |
| Ubuntu / LTS / x86-64 | Ubuntu is the server's operating system. LTS means long-term support. x86-64 is a processor type offered by hosting providers; choose the exact version in the OVH guide. |
| SSH | Secure Shell: an encrypted way to control your server from a terminal. Commands typed after connecting run on that server. |
| SSH fingerprint | A short identifier for the server's SSH key. Comparing it with the provider console helps confirm you reached your own server. |
| `scp` | A command that copies files between your computer and server using SSH. |
| `sudo` | Run the next command with administrator permission. Only use it where the guide calls for it. |
| Docker / image / container | Docker runs packaged software. An image is the package; a container is a running instance of it. Docker Compose starts it using the settings in `compose.yaml`. |
| Environment variable / stdin | A variable is a setting supplied to a program. Stdin means the program's input stream. The Railway helper uses it to send private settings without printing their contents. |
| Rollback | Restore an earlier working release. It can also restore older keys, so check access afterward. |

## Addresses and connections

| Term | What it means here |
| --- | --- |
| IP address / IPv4 / IPv6 | A numeric internet address. IPv4 and IPv6 are different address formats; the OVH guide requires a public IPv4 address. |
| Domain / hostname / DNS | A hostname is a readable address such as `example.up.railway.app`. DNS looks up its numeric address. Railway supplies a hostname, so you do not buy a domain. |
| Port / TCP | A port is a numbered entry point on a computer. TCP is a common way to carry connections. This relay accepts public connections on port 443, also commonly used by secure websites. |
| HTTPS / TLS / certificate | HTTPS is the secure website connection method, using TLS encryption. A certificate helps an app verify that it reached the intended server. Keep verification enabled. |
| VLESS / WebSocket / REALITY | Names for parts of the relay's connection method. VLESS carries requests; Railway wraps them in WebSocket over HTTPS. OVH uses REALITY, which uses cryptographic keys to authenticate and protect the connection. The template fills in these settings for you. |
| Xray | The relay software running on the server. The apps use compatible connection methods; you do not need to run Xray by hand. |
| Transport / endpoint / listener | A transport is a connection method. An endpoint is the address you connect to. A listener is the server component waiting for connections on a port. |
| Firewall / UFW | A firewall controls allowed network connections. UFW is an Ubuntu firewall tool. Keep remote-login access open when changing rules. |
| System Proxy / TUN | System Proxy asks compatible apps to use your relay app. TUN uses a virtual network interface to handle traffic from more apps; it may need additional system permission. |
| Captive portal | A hotel or public Wi-Fi sign-in page. Complete it with the relay disconnected, then reconnect. |
| Latency / bandwidth / egress | Latency is waiting time. Bandwidth is the rate data can travel. Egress is data sent out from a provider, which Railway bills. GB and TB measure amounts of data; Mbps measures speed. |
| CPU / memory / replica | CPU is processing capacity; memory is temporary working space. A replica is another running copy of a service. Adding capacity does not fix every network problem. |

## Optional advanced work

| Term | What it means here |
| --- | --- |
| JSON / YAML | Text formats for settings. Generated files use them; you do not need to edit them to follow the guides. |
| API | A way for software to send requests to another service. A management API could change your server, so it must not be publicly exposed. |
| Health check / probe | A small test. Local health checks confirm the relay started; an end-to-end probe sends real traffic through it. Neither proves every app or network will work. |
| Telemetry / logs | Measurements and recorded events. This template does not collect browsing history or traffic measurements by default. |
| CI / commit / pinned version | CI runs automated checks on code changes. A commit identifies a saved source version. A pinned version fixes which dependency is used instead of silently taking a newer one. |
| Failover / quota | Failover switches to a backup server. A quota limits usage, such as data per person. This version provides neither automatically. |

Return to [the main guide](../README.md), [Railway setup](railway.md), [OVH setup](ovh.md), or [device setup](clients.md).
