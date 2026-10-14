# Verification and pilot checklist

This page records what has been checked and what still needs a real-world trial. **If you just want to connect, use the [device guide](clients.md).** The detailed checklist below is for the owner testing a new setup or someone changing the code. Technical terms are explained in the [glossary](glossary.md).

This standalone template needs a real-world trial on each supported provider and client combination. Automated tests cover specific behavior; they do not establish that every hosting account, operating system, or network works with the template.

## Evidence recorded during development

As of October 13, 2026:

- Core generator tests: **22 passed**, covering state permissions, native Windows refusal, separate identities, rotation and revocation, both transports, client exports, configuration validation, and private-network routing rules.
- Runtime tests: **10 passed**, covering configuration limits, schema restrictions, private files, nonblocking input handling, startup validation, and health semantics.
- VPS installer passed Bash syntax validation and independent source review. Railway helper flags were checked against the installed Railway CLI help.
- Container validation passed with the pinned Xray engine for both transports, each server configuration and two separate users' client configurations. Both nonroot listeners started, and the engine's process environment no longer contained the configuration secret. Four failure-path cleanup tests passed.
- Source and documentation received independent review, including checks of local documentation links and headings. No live Railway or OVH account was modified while building this template.

The GitHub **Actions → Check → Required** job runs the automated checks for each source change; inspect its result for the version you download. Fresh provider installations, upgrades/rollback on a real VPS, and device imports still need live testing. Automated checks passing is not a claim that this template works on every provider or device.

## Reproduce artifact checks

From a Mac/Linux shell with Python 3.11+, OpenSSL, Docker Engine/Desktop and Docker Compose v2 available:

```sh
bash scripts/check.sh
```

On a machine with an agent scheduler, invoke this through that machine's required scheduler. The workflow performs the same offline tests and builds the pinned image on Ubuntu. The container smoke check uses fresh disposable identities, no published ports, and `--network none`; it validates server and client configurations with the real engine, starts both transports as the image's nonroot user, and checks removal of the runtime secret environment. It does **not** claim successful internet relay traffic.

The Docker build downloads its pinned base image and distribution packages. The temporary test image tag and test containers are cleaned up after the local script. Docker's ordinary build cache may remain.

## First deployment on each provider

Use a new, explicitly selected service/server and a small invited test group:

1. Follow the provider guide from an untouched checkout. Record the exact source commit, image, region, OS, and deployed identity. Keep secrets out of the record.
2. Import two separate users into actual client apps. Check a page, a bounded download, and the apps the group uses. Test the real destination network, including evening usage if relevant.
3. Revoke one identity and apply it. Confirm its old profile cannot reconnect while the other identity still works. Rotate a key and confirm only the replacement works.
4. Add a new identity without changing the other users' credentials, then test both.
5. For OVH, reboot at a planned time and verify recovery. Test an update and a rollback while preserving state; reconcile revocations after any rollback.
6. Restore an encrypted state backup into a separate private directory and verify the endpoint and user list. Never overwrite working state just to test recovery.
7. Record actual client versions and results for Streisand, V2Box, and Clash Verge Rev. A parser test is not a substitute for importing on each app/platform.

## Scope of the result

Health checks only prove that the local listener is running. They do not establish reachability from a particular network, restrictive-Wi-Fi compatibility, app-specific behavior, or sustainable bandwidth. Provider selection and billing remain the owner's responsibility; this repository makes no measured cost or reliability promise for a new deployment.
