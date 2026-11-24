export interface SkillToolDefinition {
  name: string;
  description: string;
  parameters: Record<string, any>;
  riskTier: 'green' | 'yellow' | 'red';
}

export interface SkillManifest {
  id: string;
  name: string;
  description: string;
  category: 'scraping' | 'automation' | 'diagnostics' | 'research' | 'finance' | 'developer' | 'general';
  icon: string;
  enabled: boolean;
  triggers: string[];
  systemPrompt?: string;
  tools: SkillToolDefinition[];
}

export interface SkillExecutionResult {
  skillId: string;
  toolName: string;
  status: 'success' | 'error' | 'approval_required';
  result?: any;
  error?: string;
  reason?: string;
  params?: Record<string, any>;
}
