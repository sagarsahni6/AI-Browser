export function generateErrorPageHtml(failedUrl: string, errorCode: number, errorDesc: string): string {
  const html = `
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Unable to Load Page</title>
  <style>
    body {
      background-color: #0d0f12;
      color: #f3f4f6;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      display: flex;
      align-items: center;
      justify-content: center;
      height: 100vh;
      margin: 0;
      user-select: none;
    }
    .card {
      background-color: #14171d;
      border: 1px solid rgba(255, 255, 255, 0.08);
      border-radius: 12px;
      padding: 32px;
      max-width: 520px;
      width: 90%;
      text-align: center;
      box-shadow: 0 10px 25px rgba(0, 0, 0, 0.5);
    }
    .icon {
      font-size: 40px;
      margin-bottom: 16px;
    }
    h1 {
      font-size: 18px;
      margin-bottom: 8px;
      font-weight: 600;
    }
    p {
      font-size: 13px;
      color: #9ca3af;
      line-height: 1.5;
      margin-bottom: 20px;
      word-break: break-all;
    }
    .err-code {
      display: inline-block;
      background-color: #1c212a;
      padding: 4px 10px;
      border-radius: 6px;
      font-family: monospace;
      font-size: 11px;
      color: #ef4444;
      margin-bottom: 24px;
    }
    button {
      background-color: #3b82f6;
      color: white;
      border: none;
      padding: 10px 24px;
      border-radius: 8px;
      font-size: 13px;
      font-weight: 500;
      cursor: pointer;
      transition: background-color 150ms ease;
    }
    button:hover {
      background-color: #2563eb;
    }
  </style>
</head>
<body>
  <div class="card">
    <div class="icon">🌐</div>
    <h1>This site can’t be reached</h1>
    <p>AI Browser was unable to establish a secure connection to <strong>${failedUrl}</strong>.</p>
    <div class="err-code">Error Code: ${errorCode} (${errorDesc})</div>
    <div>
      <button onclick="window.location.reload()">Try Again</button>
    </div>
  </div>
</body>
</html>
  `;
  return `data:text/html;charset=utf-8,${encodeURIComponent(html)}`;
}
