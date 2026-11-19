import type { CdpClient } from './cdp-client';

export interface AccessibilityNode {
  nodeId: string;
  role: string;
  name?: string;
  description?: string;
  value?: string;
  disabled?: boolean;
  focused?: boolean;
}

export class AccessibilityReader {
  private cdp: CdpClient;

  constructor(cdp: CdpClient) {
    this.cdp = cdp;
  }

  public async getTree(): Promise<AccessibilityNode[]> {
    await this.cdp.attach();
    await this.cdp.sendCommand('Accessibility.enable');

    try {
      const result: any = await this.cdp.sendCommand('Accessibility.getFullAXTree', { depth: 4 });
      const nodes = result?.nodes || [];

      // Filter to relevant semantic nodes
      const filtered: AccessibilityNode[] = [];
      for (const node of nodes) {
        const role = node.role?.value;
        const name = node.name?.value;
        const desc = node.description?.value;
        const val = node.value?.value;

        // Skip purely generic/empty layout containers
        if (!role || role === 'generic' || role === 'none' || role === 'InlineTextBox') {
          if (!name) continue;
        }

        filtered.push({
          nodeId: String(node.nodeId),
          role: role || 'element',
          name: name ? String(name).slice(0, 150) : undefined,
          description: desc ? String(desc).slice(0, 150) : undefined,
          value: val ? String(val).slice(0, 150) : undefined,
          disabled: node.disabled?.value || false,
          focused: node.focused?.value || false,
        });

        if (filtered.length >= 80) break;
      }

      return filtered;
    } catch (err: any) {
      console.warn('Failed to retrieve full AX tree via CDP:', err?.message);
      return [];
    }
  }
}
