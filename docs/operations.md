# Run and maintain your relay

This guide is for the person who pays for and maintains the relay. Most days you only need to check the hosting bill and confirm people can connect. Use the other sections when adding someone, updating software, or fixing a problem.

Run the Python commands from the template folder where you created `.relay/state.json`. This **state file** holds the server address and everyone's private connection keys. For Railway, use your computer; Windows owners use Ubuntu in WSL (the Linux environment inside Windows introduced in setup). For OVH, connect to your rented server with SSH (remote terminal access) first. See the [glossary](glossary.md) for unfamiliar dashboard terms.

## Check whether it works

```sh
python3 relay.py status
python3 relay.py validate
```

`status` lists your hosting company, server address, and user names without showing their keys. `validate` should report **“Local state is valid.”** These check your saved settings; neither contacts the server to see if it is online.

Optional advanced check: if you have the same fixed Xray version as this project installed, `python3 relay.py validate --xray xray` also asks Xray, the relay software, to check the generated settings.

For **Railway**, check that the intended service's latest deployment is successful in the dashboard. For **OVH**, run this on the VPS after a successful install:

```sh
sudo /opt/family-relay/current/scripts/ovh-install.sh --status
```

The status command checks the **container**, the running package of relay software. A healthy container means it started, but you still need a connection test. Import a current profile on a separate device and test a webpage, a download, and the apps you use. Test from the network where you need the relay. After removing someone's access or replacing their key, confirm their old profile cannot reconnect.

## Add, remove, or replace someone's access

Names use lowercase letters, numbers, and hyphens, beginning with a letter. Use separate names for devices if you want to remove access from just one device. This version allows up to 32 connection keys in one setup. It does not set a data allowance per person, so check your provider's bill and usage totals.

Add a person:

```sh
python3 relay.py user add alice
python3 relay.py export alice --format uri --output .relay/alice.txt
python3 relay.py export alice --format clash --output .relay/alice-clash.yaml
```

Replace a lost or shared connection key:

The command calls this **rotation**. The old key stops working after you apply the new settings to the server.

```sh
python3 relay.py user rotate alice
python3 relay.py export alice --format uri --output .relay/alice.txt
python3 relay.py export alice --format clash --output .relay/alice-clash.yaml
```

Remove a person's access:

The command calls this **revocation**.

```sh
python3 relay.py user revoke alice
```

**Each command changes the saved settings only.** Finish the provider's **Apply changes** procedure in [Railway setup](railway.md#apply-changes) or [OVH setup](ovh.md#apply-changes). Until the running server is updated, old access remains live and new keys will not work. Wait for the replacement server process to start and the old one to stop; a connection may continue while the old process remains running.

For Railway, the helper sends the saved settings to your chosen project; the following `railway up` command starts the updated relay. Use both commands in that guide. For OVH, **render** means create the server's settings file from your saved state, then install it:

```sh
python3 relay.py render --output .relay/server.json
sudo bash scripts/ovh-install.sh .relay/server.json
```

Run the installer on the rented server, with the Docker tools from the setup guide already installed. Keep using the same template folder and private state from setup.

After rotation, give the affected person a replacement import file and have them remove the old profile. Other people's keys remain unchanged. The tool refuses to revoke the last user; add a replacement first, or stop the hosting service if you intend to close the relay.

## Back up before changing anything

Keep an **encrypted backup** of `.relay/state.json`, the source version used, and the provider details needed to find your server. Encryption protects a backup's contents with a key or password; use your existing encrypted backup system or password-manager file storage. This template restricts who can read its files but does not encrypt backups for you. An ordinary ZIP file is not an encrypted backup.

The state file contains every person's connection key and, for OVH, the server's own secret key for REALITY (its secure connection method). Do not upload it to GitHub, attach it to a help request, or share the whole `.relay/` folder. Keep generated profiles and provider settings private too. You can export a person's connection file again from this state when needed.

To check a restored backup without overwriting your working state, copy it to `.relay/recovery/state.json` in a separate private folder, then run:

```sh
chmod 600 .relay/recovery/state.json
python3 relay.py --state .relay/recovery/state.json validate
python3 relay.py --state .relay/recovery/state.json status
```

The `.relay/recovery/` folder keeps this test copy inside the private directory excluded from uploads. It does not replace your encrypted backup. `chmod 600` gives only your user account permission to read/write the file. On Windows, keep this in WSL's Linux home folder, as during setup. Confirm the server address and user list before using restored settings on the running relay.

**An older backup can restore revoked keys.** Reapply every revocation and rotation made since that backup before returning it to service. Losing the state cannot be fixed by running `init` again: that creates new credentials and requires redeployment and new profiles for everyone.

## Update the software

1. Save the backup above and record the currently working source version and deployment.
2. Download a reviewed source version from this repository or your own maintained copy. Keep your private state separate while replacing source files. Read any release notes, which explain changes and extra update steps.
3. Validate the existing state with the new code. Do not rerun `init` or replace state with someone else's example.
4. Follow the provider's **Apply changes** steps. Allow a brief disconnection while the server is replaced.
5. Check provider/container health, then connect using a current client profile and test real traffic.

Updates that keep the server address and keys unchanged do not require everyone to import again. Railway manages its underlying computer. For OVH, you also maintain Ubuntu (the operating system) and Docker (which runs the relay), including security updates and planned reboots. Keep access to the OVH browser console, a backup way to control the server if SSH is unavailable.

## Recover from a bad deployment

Restoring an earlier working version is called a **rollback**. On OVH, the installer checks the new settings and waits for the software to start. If startup fails and a previous successful version exists, it attempts to restore it automatically. To restore that previous version yourself, run on the server:

```sh
sudo /opt/family-relay/current/scripts/ovh-install.sh --rollback
```

Rollback needs the previous successful release and its retained **Docker image**, the saved software package. **Do not remove these packages with Docker cleanup or “prune” commands.** Recovery refuses to use a missing or changed package; it does not download or rebuild one. It restores **both the software and the connection keys stored in that release**. This can restore access you removed or stop a newly added person from connecting. After recovery, compare the running server with your current saved settings and apply any needed access changes again. Keep `/opt/family-relay/` intact; it contains the current and recovery files.

On Railway, preserve the current local state and review the exact source and variables associated with the previous deployment before using a provider rollback. Alternatively, redeploy a known-good reviewed source version with configuration generated from your current state. Verify the actual running configuration through connection checks; do not assume that rolling back source also restores the desired credentials.

## Diagnose without collecting people's browsing history

Start with the smallest useful evidence:

- Time and duration of the failure, app/version, operating system, and network type.
- Whether the failure affects one person, one app, or everyone.
- Whether the same current profile works on another network or supported client.
- Running software version, restart count, whether the software started, and overall processing, memory, and data usage shown by the provider.
- Error text. DNS failures mean an address lookup failed; TLS failures mean a secure connection failed. A timeout means no answer arrived in time. An HTTP rejection means the website answered with an error.

Keep tests small and repeatable. Compare the same operation before and after one change; a speed test alone does not explain a broken sign-in or comment view. Record whether the website returned an error or the connection never completed.

By default, this template does not save the websites people visit or detailed traffic/error records. It reports generic startup failures. The provider's overall processing, memory, and network totals are still useful. App diagnostic reports can contain visited addresses or connection keys: review them and remove private details before sharing. The local `status` output contains no keys, but its server address and user names may still identify people.

See [client troubleshooting](clients.md#if-something-does-not-work) for Wi-Fi sign-in, app routing, and address-lookup checks. Keep secure-server verification and the template's network restrictions enabled. Do not open remote administration tools to the public internet as a shortcut.

## Keep the initial setup small

This version has no central subscriptions, billing, per-user usage limits, or automatic failover. Account names identify credentials, not individual humans: a recipient can copy their file. Add those features only when you need them, with server-side enforcement and tested recovery. A new host or transport also needs connection tests from the networks your group actually uses.
