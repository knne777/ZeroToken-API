# Binaries directory for ZeroToken container builds

If you want to bake the proprietary standalone **Google Antigravity (`agy`)** CLI binary directly into the Docker image (for example, for Coolify Git-based builds or environments without host volume mounting), place the Linux x86-64 `agy` executable in this directory:

```bash
cp ~/.local/bin/agy bin/agy
chmod +x bin/agy
```

When building the Docker image, if `bin/agy` exists, it will be automatically copied into `/usr/local/bin/agy` inside the container.
