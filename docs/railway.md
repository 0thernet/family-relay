# Railway setup

Railway rents you the computer that runs the relay and looks after its operating system. You will use your own computer to create the settings and send them to Railway. Once setup is complete, your computer can be turned off; Railway keeps the relay running.

**Every command on this page runs on your own computer.** A terminal is an app where you type commands: use Terminal on a Mac, or the Ubuntu app described below on Windows. Open it in the downloaded `family-relay` folder. Run one line at a time, wait for it to finish, and stop if it reports an error. Never paste a whole later section to try to fix an earlier failure.

Words in capitals, such as `PROJECT_ID`, are placeholders for your own values. Do not type those words literally. See the [plain-language glossary](glossary.md) whenever a term is unfamiliar.

## 1. Install the two tools

Python runs this template's setup script. The Railway command-line tool, often called its **CLI**, lets your terminal create and update your Railway service. You need Python version **3.11 or newer** and the current Railway tool.

On a Mac with [Homebrew](https://brew.sh/) installed, run the following. Homebrew is a tool for installing software; use the alternatives below if you do not have it.

```sh
brew install python railway
python3 --version
railway --version
```

Otherwise use [Python's download page](https://www.python.org/downloads/) and the [official Railway CLI installation guide](https://docs.railway.com/cli), then run the two `--version` commands above.

On Windows, use **Ubuntu in WSL**. WSL is Microsoft's way to run Linux tools on a Windows computer; Ubuntu is the Linux system used here. [Install WSL](https://learn.microsoft.com/en-us/windows/wsl/install), open Ubuntu, and put the template folder in Ubuntu's home folder, for example `~/family-relay`. Here `~` means your home folder. Keep it there rather than under `/mnt/c`, which refers to the Windows drive, so the private files can have the permissions this tool needs.

In Ubuntu, install Python with `sudo apt-get update` followed by `sudo apt-get install -y python3`. `sudo` asks to run that command with administrator permission; it may request your Ubuntu password. Follow Railway's Linux CLI installation instructions, then check both versions. Running the setup with ordinary Windows Python is not supported. People connecting to the relay still use normal Windows apps.

**Ready to continue:** both version commands print a version number, with Python at least 3.11. If you see “command not found,” finish that tool's installation first.

## 2. Create an empty project and service

A Railway **project** groups your setup together; a **service** is the program it runs. These commands sign you in and create a new project containing one empty service. Use the Railway account that should own and pay for this relay:

```sh
railway login
railway init --name family-relay
railway add --service relay
railway status
```

The login command opens a browser or shows instructions for signing in. If asked to choose a workspace, choose the personal or team account that should pay the bill.

**Ready to continue:** `railway status` identifies your new **family-relay** project. Open that project in the Railway dashboard, the website where you manage it, and check that it contains the **relay** service. Copy its project ID, the unique identifier shown in project settings or its web address. In every later command, replace `PROJECT_ID` with that exact ID. Do not use the ID of an existing project that runs something else.

In the service settings, choose the region, meaning the location where Railway will run it. Leave **replicas** at one: that means one running copy. Turn off **sleeping/serverless** if enabled so it stays available between connections. Set a budget or usage alert in Railway to help track the bill. You do not need to add a database or storage service.

## 3. Get your relay's free address

A **hostname** is a readable internet address. Railway supplies one and handles the security certificate that lets apps verify they are connecting to the right address. You do not need to buy a domain name.

```sh
railway domain --project PROJECT_ID --service relay --environment production --port 8080
```

**Ready to continue:** the command returns an address such as `family-relay-production.up.railway.app`. Save **your** address. If you already generated one, reuse the domain shown under service Settings → Networking; do not generate a different address each time you update.

A **port** is a numbered entrance for a network connection. Your devices use public port **443**, the usual secure-web entrance. Railway passes those connections to the relay's internal entrance, **8080**, set by the command above. Leave that target at 8080 and do not enable the separate **TCP Proxy** feature. You do not need to configure the underlying HTTPS/WebSocket connection yourself.

## 4. Create people's access and start the relay

These commands create a different connection key for each person, send the private server settings to Railway, and **deploy** the relay, meaning upload and start it.

Replace the entire `YOUR_HOSTNAME.up.railway.app` value with the address from step 3, using lowercase letters. Do not include `https://`, a port number, or a slash. Replace `owner,mom,dad` with your preferred short names, separated by commas without spaces. Use lowercase letters, numbers, and hyphens, starting each name with a letter.

```sh
python3 relay.py init --provider railway --host YOUR_HOSTNAME.up.railway.app --users owner,mom,dad
python3 relay.py status
python3 scripts/railway-apply.py --project PROJECT_ID
railway up --project PROJECT_ID --service relay --environment production --detach
```

Run `init` only for a new setup. It saves the keys in `.relay/state.json`, a private file in the template folder. The leading dot makes `.relay` a hidden folder on many systems. Keep it for future changes and backups; never send it to someone joining the relay.

The `railway-apply.py` helper stores the server settings in Railway's private service setting named `RELAY_CONFIG_JSON`. It passes them directly to the Railway tool without printing the keys. It does not start the relay by itself; the `railway up` line does that. Keep `.railwayignore` and `.dockerignore` intact: these files tell the upload and build tools to leave private files out.

**Ready to continue:** the helper reports that the configuration is staged, and Railway's dashboard shows a successful deployment with the service running. `--detach` returns your terminal prompt while Railway continues working, so keep watching the dashboard.

Leave the dashboard's **HTTP healthcheck path** empty. That option checks a webpage for signs of life, but this relay does not serve a health webpage. Opening its address in a browser may show an error even when it is running. The next step tests a real connection.

## 5. Make connection files and try them

A **profile** is a small file containing the address and key an app needs to connect. These examples create a text link for V2Box or Streisand, and a `.yaml` settings file for Clash Verge. Choose the format each person needs; the names must match people created above.

```sh
python3 relay.py export owner --format uri --output .relay/owner.txt
python3 relay.py export mom --format uri --output .relay/mom.txt
python3 relay.py export dad --format clash --output .relay/dad-clash.yaml
```

**Ready to connect:** each export command reports that it wrote a private file. Follow [the client guide](clients.md) to import it into the app. Share each file privately with only its intended person. Neither your Railway login nor `.relay/state.json` should be shared. Friends do not need Railway accounts.

**Setup is working when:** a device using its imported profile loads a normal webpage and the apps you use. Switch the relay app off and back on, then test again. A successful deployment alone does not prove that your device can connect from its network.

## Apply changes

Adding a person, replacing their key (**rotation**), or removing access (**revocation**) first changes only your computer's saved settings. After using the relevant `user add`, `user rotate`, or `user revoke` command in [the operations guide](operations.md), run these on **your own computer**, in the same template folder:

```sh
python3 scripts/railway-apply.py --project PROJECT_ID
railway up --project PROJECT_ID --service relay --environment production --detach
```

Wait for the new deployment to succeed and the old one to stop. Only then is removed access fully turned off. Test that a current profile works and a removed profile cannot make a new connection. Existing users keep their profile unless you changed their key or the server address. Export a new file for anyone added or given a replacement key.

If a command times out, check the project's settings and deployments before retrying: Railway may have accepted the operation even though your terminal stopped waiting. Do not copy the contents of Railway's **Variables** page into a help request; those settings can contain keys. See [operations](operations.md) for checks, recovery, and troubleshooting.

## Why no “Deploy” button yet?

This public GitHub repository shares the setup files; your generated access keys stay private. The commands above create fresh keys for your group and deploy to your own account. A Railway marketplace button would be a separate feature; it is not included in this version.
