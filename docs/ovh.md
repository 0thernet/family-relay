# OVH server setup

A **VPS**, or virtual private server, is a Linux computer you rent from OVH. It runs the relay continuously, even when your laptop is off. You will use your laptop to connect to that server and run the setup there. Unlike Railway, you are responsible for maintaining the server's operating system. First review [the provider options and applicable terms](providers.md).

When buying it, select a **new Ubuntu 24.04 LTS, x86-64 VPS with a public IPv4**. Ubuntu is the operating system, 24.04 LTS is the supported version, x86-64 is the processor type, and the public IPv4 is the internet address your devices will connect to. Use a fresh server so this setup cannot interrupt an existing website. You do not need to buy a domain name.

Have the server's IP address, login username (often `ubuntu`), and password or SSH key ready from the OVH control panel. An **SSH key** is a login file you may have chosen instead of a password. Keep it on your computer; do not share it with people using the relay.

Commands below are labelled **your computer** or **server**. Run one line at a time, wait for it to finish, and stop if it reports an error. Replace capitalized placeholders such as `SERVER_IP` with your own values. The [plain-language glossary](glossary.md) explains other unfamiliar terms.

## 1. Connect to the server

**On your computer:** open Terminal on a Mac, or PowerShell on Windows. These apps let you type commands. The `ssh` command opens a secure remote login, so subsequent commands in that window will run on your rented server.

```sh
ssh ubuntu@SERVER_IP
```

Replace `SERVER_IP` and, if needed, `ubuntu` with the values OVH gave you. If you selected an SSH key that your computer does not find automatically, follow OVH's login instructions to select that key file.

On first connection, SSH asks whether to trust the server's **fingerprint**, an identifying code. Compare it with the server's SSH host-key fingerprint through OVH's browser console before accepting it. That console is a way to reach the server through OVH's website; keep it available in case the SSH connection fails. When entering a password, nothing appears as you type, which is normal.

**Ready to continue:** the server shows its welcome message and a new command prompt, usually containing your server username and name. Keep this window open. From this point, call it the **server terminal**.

## 2. Install the tools on the server

Python runs the template's setup script. OpenSSL creates the server's cryptographic keys. Docker runs the relay in a **container**, a packaged environment containing the program and what it needs. Docker Compose starts that container using the supplied settings file.

**In the server terminal**, run:

```sh
sudo apt-get update
sudo apt-get install -y python3 openssl docker.io docker-compose-v2
sudo systemctl enable --now docker
sudo docker compose version
```

`sudo` runs a command with administrator permission and may ask for the server account's password. `apt-get update` refreshes Ubuntu's software list; the next line installs the tools. `systemctl` starts Docker and tells it to start after a reboot.

**Ready to continue:** the last command prints a Docker Compose version starting with `v2`. If a package cannot be found, check that the server is Ubuntu 24.04 with its standard software sources enabled. Do not substitute an unrelated one-line installer. The [Docker Ubuntu guide](https://docs.docker.com/engine/install/ubuntu/) describes an alternative installation source; do not mix it with the Ubuntu packages used above.

A **firewall** decides which connections can reach the server. Keep SSH login allowed, and permit incoming **TCP port 443** for the relay. A port is a numbered network entrance; 443 is the entrance devices use here. TCP is the type of connection. Check any firewall enabled in OVH's control panel too.

If Ubuntu's **UFW** firewall is already active, `sudo ufw allow 443/tcp` adds the relay rule. Do not reset firewall rules or turn a firewall on without first preserving SSH access. Docker also manages rules for the ports it exposes, so a UFW setting alone does not describe all access. This template needs no public management interface or extra relay port.

## 3. Copy the setup files to the server

**On your computer:** download this repository using **Code → Download ZIP** and extract it. Rename the extracted folder `family-relay`. Use a fresh copy, not another deployment's folder containing `.relay/` and its private settings.

Open a **second terminal on your computer**, leaving the server terminal connected. Go to the folder containing `family-relay`, then run:

```sh
scp -r family-relay ubuntu@SERVER_IP:~/
```

`scp` copies files over the same secure connection as SSH. `-r` includes the folder's contents, and `~/` means the server account's home folder. Use the same username and server address as for SSH.

**Ready to continue:** the copy finishes without an error and your computer's command prompt returns. You do not need to put a GitHub login token or SSH private key on the server.

## 4. Create people's access and start the relay

**Back in the server terminal**, run the commands below. `cd` opens the copied folder. Replace `SERVER_IP` with the public IPv4 address. Replace `owner,mom,dad` with your chosen short names, separated by commas without spaces. Use lowercase letters, numbers, and hyphens, starting each name with a letter.

```sh
cd ~/family-relay
python3 relay.py init --provider ovh --host SERVER_IP --users owner,mom,dad
python3 relay.py render --output .relay/server.json
sudo bash scripts/ovh-install.sh .relay/server.json
```

`init` creates separate connection keys and saves them in `.relay/state.json`. Run it only for a new setup. `render` writes the server settings, and the installer checks those settings before starting the relay. The `.relay` folder is hidden on many systems; keep it for future changes and backups, and do not send it to someone joining the relay.

**Ready to continue:** the installer reports that the relay is listening on TCP port 443. This confirms startup; the next step checks a real connection from your device.

The installer stores each installed version under `/opt/family-relay`. During later updates, it retains the previous successful version and attempts to restore it if the new one fails its startup check. It does not erase the server, install Docker, or change SSH or firewall settings.

If it reports that port 443 is already occupied, another program may be using that entrance. Stop and inspect the listening programs with `sudo ss -lntp`, or ask for help interpreting that output. Do not stop an unrelated website to make this guide work; use a fresh VPS instead.

## 5. Make connection files and try them

A **profile** is a small file containing the address and key an app needs to connect. **In the server terminal**, create one for each person. These examples make text links for V2Box or Streisand, and a `.yaml` settings file for Clash Verge. Choose the format each person needs; the names must match people created above.

```sh
python3 relay.py export owner --format uri --output .relay/owner.txt
python3 relay.py export mom --format uri --output .relay/mom.txt
python3 relay.py export dad --format clash --output .relay/dad-clash.yaml
```

**Ready to copy:** each command reports that it wrote a private file. Now return to the **second terminal on your computer** and copy only the intended person's file back:

```sh
scp ubuntu@SERVER_IP:~/family-relay/.relay/owner.txt .
```

The final `.` means “save it in the folder this terminal is currently in.” Use the corresponding filename for another person. Import it following [the client guide](clients.md), then share other people's files privately. On Windows, keep downloaded files in your own user account's protected folder. Delete unneeded copies after importing. Never share `state.json` or `server.json`, which hold server-wide secrets.

**Setup is working when:** a device using its imported profile loads a webpage and the apps you use. Test the actual networks where you need it, then disconnect and reconnect the app and test again.

This connection method is called **REALITY**. It uses the server's keys and a configured public website during its initial connection check, without requiring you to buy a domain or certificate. The default website is `www.bing.com` on port 443; the server must be able to reach it. REALITY does not create a normal website at `https://SERVER_IP`, so opening that address in a browser is not a useful connection test.

After the first successful connection, arrange a brief interruption and reboot the server using OVH's console or SSH. Reconnect and confirm that the relay returns. Docker's `unless-stopped` setting is intended to bring it back automatically, unless you explicitly stopped it. Keep the provider console available during this check.

## Apply changes

Adding a person, replacing their key (**rotation**), or removing access (**revocation**) first changes only the saved settings. Use the relevant commands in [the operations guide](operations.md), then run these **in the server terminal**, inside `~/family-relay`:

```sh
python3 relay.py render --output .relay/server.json
sudo bash scripts/ovh-install.sh .relay/server.json
sudo /opt/family-relay/current/scripts/ovh-install.sh --status
```

**The change is applied when:** the installer succeeds, the status command shows the container running and healthy, and a current profile can reconnect. If you removed access, also confirm that the removed profile cannot make a new connection. An app left connected may retain its old connection until the previous container stops.

For updates, encrypted backups, restoring a previous version, and troubleshooting, follow [the operations guide](operations.md). Do not delete `/opt/family-relay` to repair a failure; it contains the current and recovery settings.
