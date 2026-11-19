export class NavigationGuard {
  private static BLOCKED_PROTOCOLS = ['file:', 'chrome:', 'javascript:', 'vbscript:', 'data:'];

  public static isNavigationPermitted(targetUrl: string, isInternal = false): { allowed: boolean; reason?: string } {
    if (isInternal) {
      return { allowed: true };
    }

    try {
      const parsed = new URL(targetUrl);
      if (this.BLOCKED_PROTOCOLS.includes(parsed.protocol)) {
        // Exception for safe error pages
        if (targetUrl.startsWith('data:text/html')) {
          return { allowed: true };
        }
        return {
          allowed: false,
          reason: `Navigation to protocol '${parsed.protocol}' is restricted for safety.`
        };
      }
      return { allowed: true };
    } catch {
      // If not a valid URL format, allow if search query
      return { allowed: true };
    }
  }
}
