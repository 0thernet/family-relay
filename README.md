# Family relay

A relay is a computer that forwards internet connections for you. With this template, one person rents that computer from **Railway or OVH**, sets it up, and shares access with friends and family. Each person gets their own connection key, which works like a password.

**Setting it up for the group?** Follow one of the setup guides below. You need a computer, a paid hosting account, and a willingness to copy commands into a terminal (the app where you type instructions). You do not need to write code, buy a domain name, or install a new app we made.

**Just joining someone else's relay?** Ask them for your connection file and go straight to [Connect your devices](docs/clients.md). You do not need this repository, a hosting account, or terminal commands.

Choose **Railway** for less server maintenance, or **OVH** for a rented Linux computer (a **VPS**, or virtual private server) with included traffic on eligible plans. Both cost money to run. One setup serves the whole group; you do not need a separate server for each friend.

| | Railway | OVH VPS |
|---|---|---|
| Setup | Run commands on your computer; Railway runs the relay | Rent a server, then control it remotely from your terminal |
| Server address | Railway supplies an address and handles its HTTPS security certificate | Use the server's numeric internet address; no domain purchase needed |
| Cost model | Pay for computing resources and data sent out | Pay a fixed server price; included traffic depends on the plan and location |
| Maintenance | Railway maintains the computer underneath the relay | You keep the server's operating system and software updated |
| Best fit | A small group that values convenience | An owner willing to maintain a server, especially with more traffic |

Both options use **port 443**, the numbered connection entry point commonly used by secure websites. That can help on networks that restrict other ports, but it does not guarantee access. Test with a small group on the networks you actually use before committing to a long hosting term. See [provider details and costs](docs/providers.md).

## Start here

1. Download this repository (the shared folder of source files on GitHub) using **Code → Download ZIP**. Unzip it and rename the extracted folder `family-relay`. No invitation is needed. Owners who already use Git can clone it instead.
2. Follow **[Railway setup](docs/railway.md)** or **[OVH setup](docs/ovh.md)**. Both generate new secrets and create an independent relay in your own hosting account.
3. Create one person's **profile**, a small connection file containing their settings and personal connection key, and send it privately. Follow **[Connect an iPhone, Mac, or Windows computer](docs/clients.md)**.
4. Test a normal webpage, a larger download, and the apps that matter to your group. Test again on the network where you plan to use it.

The examples use `owner,mom,dad`. Replace those with short names of your choice, such as `alice,bob,charlie`. You can add people later, up to 32 per deployment in this initial version. This is an administrative limit, not a promise that 32 simultaneous streams will perform well.

### If terminal commands are new to you

- Follow **one provider guide**, in order. Each tells you whether a command runs on your computer or the rented server.
- On Mac, open **Terminal**. To work inside the downloaded folder, type `cd ` (including the space), drag the folder from Finder into the terminal, and press Enter. `cd` means “change directory,” or choose the folder to work in. On Windows, the Railway guide uses Ubuntu inside Windows; the OVH guide uses PowerShell.
- Copy one command line at a time and wait for it to finish. Lines starting with `#` are explanations; you can skip them.
- Uppercase examples such as `SERVER_IP` and `PROJECT_ID` are placeholders. Replace them with your own values before pressing Enter. The guide tells you where to find each value.
- If a command reports an error, stop at that step and read the troubleshooting guidance. Do not keep running later commands and hope it worked.

The [plain-language glossary](docs/glossary.md) explains terms you may see in the guides or your hosting dashboard.

## Everyday commands

Use this section **after completing setup**. Run only the command for the action you need. Run it from the template folder where you created the private settings: on your computer for Railway, or on the server for OVH. Windows Railway owners use WSL, the Ubuntu environment explained in that guide.

```sh
# Show the provider and people without revealing connection keys.
python3 relay.py status

# Give a person or device their own connection key.
python3 relay.py user add alice

# Write private import files. Nothing secret is printed to the terminal.
python3 relay.py export alice --format uri --output .relay/alice.txt
python3 relay.py export alice --format clash --output .relay/alice-clash.yaml

# Remove access, or replace someone's key if it was shared or lost.
python3 relay.py user revoke alice
python3 relay.py user rotate mom
```

**Changes take effect only after sending the updated settings to the server.** Follow the provider's **Apply changes** section after adding someone, rotating a key (replacing it), or revoking access (removing it). After rotation, send that person a new import file. An existing connection may continue until the old server process stops; the apply steps replace that process.

The hidden `.relay/` folder holds your private settings and connection files. Keep an encrypted backup, such as a file stored in your password manager. It is excluded from source uploads and software builds. Do not send the entire folder to a friend; share only that person's exported file. Anyone with a copy of their file can use their access.

## What is included

- Commands that create fresh connection keys and separate access for each person.
- Setup instructions for Railway and OVH, with no purchased domain required.
- Connection files for Streisand, V2Box, and Clash Verge Rev, plus an advanced Xray export.
- Checks for invalid settings before startup and private file permissions to protect keys.
- [Monitoring, backup, updates, rollback, debugging, and extensions](docs/operations.md).

Each person imports a private file into their app. There is no subscription URL that automatically refreshes their settings. Adding a person does not require existing people to import again; changing the server address or someone's key does. This version has no customer billing, enforced data allowance per person, or automatic switch to a backup server. The owner pays the hosting bill and controls a server that can observe connections, so only use a relay whose owner you trust.

## Development and verification

**For people changing the template's code.** You can skip this section when following a setup guide. A container is a package that runs the relay software with its required tools. Docker runs that package; Xray is the software inside it that forwards connections.

Python 3.11 or later is required. The generator uses the Python standard library; OVH key generation also uses OpenSSL. Docker is required on the VPS and for the full developer check below, not on family members' devices.

```sh
bash scripts/check.sh
```

GitHub also runs these checks automatically when code changes; this is called **continuous integration**, or CI. It builds a fixed version of the Xray container and checks the generated settings with the actual software. Check [verification status](docs/verification.md) for what has been tested and what still needs a real-world trial. Installing your own copy does not update or restart anyone else's relay.

## Public source, private access

Anyone can read or download this project's source files. GitHub's **Use this template → Create a new repository** option also creates your own source copy; select **Private** if you want to keep your changes and notes to yourself. Downloading the ZIP is enough to follow the setup guides. See [usage permissions and third-party notices](THIRD_PARTY_NOTICES.md) before redistributing code.

The public files contain no working relay keys. Setup generates fresh keys for your group and stores them in the hidden `.relay/` folder, which is excluded from source uploads. Keep those files and your hosting credentials private even if you keep a private source copy. Public source does not make your deployed relay open to everyone: people still need a valid personal profile to connect.

Share this repository link with someone who wants to set up their own server. Someone joining your existing relay only needs their personal connection file and the [device guide](docs/clients.md).

See [architecture and extension notes](docs/extending.md) for how the standalone project works.
