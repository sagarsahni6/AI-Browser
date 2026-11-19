# Release & Windows Packaging Guide

## Packaging Pipeline

AI Browser is packaged for 64-bit Windows systems using `electron-builder` with NSIS installer generation.

### Prerequisites for Distribution Build
- Windows 10/11 x64
- Node.js 20+
- Python 3.11+
- NSIS (bundled automatically by electron-builder)

### Step-by-Step Production Build
1. **Compile Desktop Assets**:
   ```powershell
   npm run build:renderer --workspace=@ai-browser/desktop
   npm run build:electron --workspace=@ai-browser/desktop
   ```

2. **Package Python Backend Executable**:
   ```powershell
   powershell -ExecutionPolicy Bypass -File scripts/build-backend.ps1
   ```

3. **Generate Windows NSIS Installer**:
   ```powershell
   powershell -ExecutionPolicy Bypass -File scripts/package-windows.ps1
   ```
   The installer executable will be generated at:
   `dist-installer/AI Browser Setup 0.1.0.exe`

---

## Windows Code Signing Policy

For commercial releases:
1. Obtain an Authenticode standard or EV (Extended Validation) code signing certificate.
2. Configure environment variables before running the build:
   ```powershell
   $env:CSC_LINK = "path/to/certificate.pfx"
   $env:CSC_KEY_PASSWORD = "certificate-password"
   ```
3. In local development or testing environments, unsigned installers can be produced by leaving these variables unset.

---

## First-Run Setup & API Credentials

1. Upon first launch, the browser runs in local mode.
2. Open **Settings** (or AI Assistant) to provide an optional **NVIDIA NIM API Key** (`NVIDIA_API_KEY`).
3. Keys are encrypted at rest using Windows DPAPI via Electron's `safeStorage`.
4. The Python backend communicates exclusively over loopback `127.0.0.1` and stdio JSON-RPC.
