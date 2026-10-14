# Connect your devices

The server owner sets up the relay once. Everyone else needs just a **profile** and a compatible app. A profile is a small file containing the server's address, connection settings, and your personal access key. You do not need a hosting account, access to this repository, or any of the owner's setup tools.

Ask the owner for **your profile only**. Treat it like a password: anyone with a copy can use your access. Do not paste it into an online configuration converter or QR-code website.

## Choose an app

The owner can export the same connection in two file formats. Choose the file that matches your app; you do not need to understand or edit its contents.

| Device | Suggested app | File to request |
| --- | --- | --- |
| iPhone or iPad | [Streisand](https://apps.apple.com/us/app/streisand/id6450534064) or [V2Box](https://apps.apple.com/us/app/v2box-v2ray-client/id6446814690) | Your `.txt` file |
| Mac | [Clash Verge Rev](https://github.com/clash-verge-rev/clash-verge-rev/releases) or [V2Box](https://apps.apple.com/us/app/v2box-v2ray-client/id6446814690) | Your `-clash.yaml` file for Clash Verge; `.txt` for V2Box |
| Windows | [Clash Verge Rev](https://github.com/clash-verge-rev/clash-verge-rev/releases) | Your `-clash.yaml` file |

Use the official App Store listing or project's release page. Check device requirements and regional availability there, choose a stable release, and keep the app current. These exports use connection types supported by the listed apps; see [verification status](verification.md) for what has actually been tested with this template.

## iPhone, iPad, or Mac with V2Box or Streisand

1. Install the app and receive your `.txt` file privately, such as through AirDrop or an encrypted message.
2. Open the file and copy the complete line starting with `vless://`. This is a **VLESS link**, a connection format the app understands. Copy the whole line without adding spaces.
3. In the app, open its configuration list, choose **Add / +**, then **Import from clipboard**. The wording varies between apps and versions.
4. Select **`family-relay-YOUR-NAME`** and connect. Accept the operating system's request to add a **VPN configuration**; this permission lets the app send traffic through your relay.
5. Open a webpage and test the apps you use. A green connection indicator alone does not prove that browsing works.

If the app offers **routing modes** (settings that decide which traffic uses the relay), begin with **Global / all traffic through the proxy** for the initial test. Here, “proxy” means your relay. Existing **bypass rules** can send selected traffic directly instead, which may explain why only some apps work. Keep any setting changes easy to undo.

The imported link contains the connection settings, so you do not need to fill in advanced fields. Keep **certificate verification** enabled: it checks the server's identity for HTTPS connections. Do not turn on **Allow insecure** to work around a failure.

## Mac or Windows with Clash Verge Rev

1. Install the stable package for your operating system and processor from the [official releases](https://github.com/clash-verge-rev/clash-verge-rev/releases).
2. Save your `YOUR-NAME-clash.yaml` file on your computer. YAML is a configuration-file format that Clash reads for you.
3. Open **Profiles / Subscriptions** and import a **local file**. Use the local-file import control, or drag the file into the profile list if your version supports it. Select the newly imported profile.
4. Open **Proxies**, find **family relay**, and select **`family-relay-YOUR-NAME`**.
5. Leave the mode on **Rule** for this supplied profile. Its single rule sends traffic handled by Clash through the relay.
6. Turn on **System Proxy**, then test a webpage. This tells apps that follow your computer's proxy settings to use Clash.

If a particular app still connects directly, try Clash Verge's **TUN mode** if supported. TUN creates a virtual network connection so Clash can handle traffic from more apps. Follow its operating-system permission prompts, and avoid running another VPN at the same time while testing. Neither a connection indicator nor the System Proxy switch guarantees that every program uses the relay.

Keep the supplied file as it is. Its contents use JSON, another configuration format that is also valid inside a YAML file; no conversion is needed. See the official [quick start](https://www.clashverge.dev/guide/quickstart.html) and [profile import guide](https://www.clashverge.dev/guide/profile.html) for the controls in your version.

## Changing or replacing a profile

**The imported file does not update automatically.** A subscription is a web address from which an app can download updated profiles. This version does not provide one, so pressing Refresh does not fetch changes from the owner.

- When another person joins, your existing profile keeps working.
- If the owner **rotates your key**, they replace it with a new one. Receive and import the replacement file, select it, and remove the old profile.
- If the server address or connection settings change, everyone needs a new file.
- If your access is **revoked**, the owner has removed it. Reimporting the old file will not restore access after the server update is applied.

The same person's profile can be used on several devices, but a lost device then requires replacing that profile everywhere. Ask for separate names such as `alice-phone` and `alice-laptop` if you want to remove each device's access independently.

## If something does not work

1. **Hotel or public Wi-Fi:** disconnect the relay, complete the network's sign-in page, then reconnect. This sign-in page is sometimes called a **captive portal**; the relay cannot complete it for you.
2. **No pages load:** confirm the correct profile is selected and that the owner has applied it to the server. Try another network, such as a phone hotspot, to see whether the failure is specific to your current connection.
3. **Only some apps or actions fail:** confirm their traffic is being handled by the relay app. With Clash, compare System Proxy and TUN. With V2Box or Streisand, check for bypass rules. Browser extensions can also interfere with a site.
4. **An error mentions DNS or “name resolution”:** DNS is the lookup that turns a website name into a network address. Update the client first, then inspect its DNS settings or diagnostic screen. Record the error and whether a different network changes it. Change one setting at a time so you can tell what helped and undo it if needed.
5. **Send the owner a small report:** include the app name/version, operating system, selected profile name, time, network type, and error text. Remove connection links, keys, and private account details from screenshots. A field called **UUID** is your personal access key and should also be hidden.

The owner can follow [the operations guide](operations.md) to check the server. A working basic transfer does not prove that every website, signed-in action, or local network will work. The [glossary](glossary.md) explains more of the terms you may see.

## Owner only: export the right file

Run these commands in the repository folder where your `.relay/state.json` file lives. That private state file contains the deployment settings and access keys. Replace `mom` with an existing user name.

```sh
python3 relay.py export mom --format uri --output .relay/mom.txt
python3 relay.py export mom --format clash --output .relay/mom-clash.yaml
```

Windows owners using Railway run these in **Ubuntu in WSL**, the Windows feature that provides a Linux terminal. OVH owners run them in the rented server's **SSH terminal**, a secure remote command window. The provider setup guide explains how to get there. People importing profiles use their normal device apps and do not need either tool.

### Find the exported file

The `.relay` folder starts with a dot, so some file browsers hide it. It contains both shareable personal profiles and the owner's private state; choose the exact exported filename rather than sharing the whole folder.

- **On a Mac:** open the repository folder in Finder, then press **Command–Shift–.** (the period key) to show hidden files. Open `.relay`, then choose `mom.txt` or `mom-clash.yaml`. For V2Box or Streisand, open the `.txt` file and copy only its complete `vless://` line into the app's **Import from clipboard** control. For Clash Verge, import the `.yaml` file directly. The same keyboard shortcut hides dot-folders again.
- **On Windows with WSL:** in the Ubuntu terminal, stay in the repository folder and run `explorer.exe .` to open that location in Windows File Explorer. You can also enter `\\wsl$` in Explorer's address bar and browse into your Ubuntu distribution, `home`, your Linux user folder, and the repository. Open `.relay` and select the intended exported profile. If you need a Windows copy to import or send, copy only that person's `.txt` or `.yaml` file into a private folder in your own Windows account. Keep the repository and `.relay/state.json` in the Linux home directory; do not move them to `/mnt/c` or copy the entire `.relay` folder.
- **On the OVH server:** follow the [OVH guide](ovh.md) to download only the intended profile to your computer. Finder or File Explorer on your computer does not show the remote server's files automatically.

Send only the file that matches the recipient's app. The separate `xray` export is for someone running the relay engine directly; it is not needed for the apps above. Apply newly added or rotated users to the server before asking them to connect.
