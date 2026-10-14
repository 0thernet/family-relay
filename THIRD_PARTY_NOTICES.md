# Third-party software

This template invokes and packages third-party software; it does not change their licenses.

- **Xray-core**, distributed inside the pinned container: [source and license](https://github.com/XTLS/Xray-core), Mozilla Public License 2.0. The pinned engine version is recorded in `Dockerfile`. Preserve its license and source availability obligations if redistributing images or modified binaries.
- **teddysun/xray container packaging**: [upstream Docker image source](https://github.com/teddysun/across/tree/master/docker/xray). Review upstream notices when rebuilding or redistributing.
- **Python, Alpine Linux packages, OpenSSL, Docker, and client apps** retain their respective licenses. Install clients from their official publishers. They are not bundled with this repository.

The command-line generator, runtime wrapper, installer, tests, and guides were written for this standalone template. Deployment credentials and provider account details belong in private state, never in the source files.

You may use this template for your own private deployment. No general redistribution license is granted for the original template code. Third-party license grants and obligations remain independent.
