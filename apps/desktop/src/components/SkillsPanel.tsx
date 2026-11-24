import React, { useEffect, useState } from 'react';
import {
  Zap,
  Table,
  FileCheck,
  ShieldCheck,
  Download,
  BookOpen,
  TrendingUp,
  Cpu,
  Search,
  ChevronDown,
  ChevronRight,
  Play,
  RotateCcw,
  CheckCircle2,
  AlertCircle
} from 'lucide-react';
import { useBrowserStore } from '../store/browser-store';
import type { SkillManifest } from '@ai-browser/shared';
import styles from './SkillsPanel.module.css';

const CATEGORIES = [
  'all',
  'scraping',
  'automation',
  'diagnostics',
  'research',
  'finance',
  'developer'
] as const;

export const SkillsPanel: React.FC = () => {
  const { skills, loadSkills, toggleSkill, executeSkill } = useBrowserStore();
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [expandedSkillIds, setExpandedSkillIds] = useState<Set<string>>(new Set(['web_scraper', 'form_automation']));
  const [runningTool, setRunningTool] = useState<string | null>(null);
  const [toolOutputs, setToolOutputs] = useState<Record<string, string>>({});

  useEffect(() => {
    loadSkills();
  }, [loadSkills]);

  const toggleExpand = (id: string) => {
    setExpandedSkillIds(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const getSkillIcon = (iconName: string) => {
    switch (iconName) {
      case 'Table': return <Table size={15} />;
      case 'FileCheck': return <FileCheck size={15} />;
      case 'ShieldCheck': return <ShieldCheck size={15} />;
      case 'Download': return <Download size={15} />;
      case 'BookOpen': return <BookOpen size={15} />;
      case 'TrendingUp': return <TrendingUp size={15} />;
      case 'Cpu': return <Cpu size={15} />;
      default: return <Zap size={15} />;
    }
  };

  const handleRunTool = async (skillId: string, toolName: string) => {
    setRunningTool(toolName);
    try {
      const res = await executeSkill(toolName, {});
      setToolOutputs(prev => ({
        ...prev,
        [toolName]: JSON.stringify(res, null, 2)
      }));
    } catch (err: any) {
      setToolOutputs(prev => ({
        ...prev,
        [toolName]: `Error: ${err.message || String(err)}`
      }));
    } finally {
      setRunningTool(null);
    }
  };

  const filteredSkills = (skills || []).filter(skill => {
    if (selectedCategory !== 'all' && skill.category !== selectedCategory) {
      return false;
    }
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const matchName = skill.name.toLowerCase().includes(q);
      const matchDesc = skill.description.toLowerCase().includes(q);
      const matchTools = skill.tools.some(t => t.name.toLowerCase().includes(q) || t.description.toLowerCase().includes(q));
      const matchTriggers = skill.triggers?.some(tr => tr.toLowerCase().includes(q));
      return matchName || matchDesc || matchTools || matchTriggers;
    }
    return true;
  });

  const activeCount = (skills || []).filter(s => s.enabled).length;
  const totalTools = (skills || []).reduce((acc, s) => acc + (s.tools?.length || 0), 0);

  return (
    <div className={styles.container}>
      {/* Header */}
      <div className={styles.header}>
        <div className={styles.titleRow}>
          <div className={styles.title}>
            <Zap size={15} style={{ color: 'var(--accent-primary)' }} />
            <span>Agent Skills Suite</span>
          </div>
          <button
            onClick={() => loadSkills()}
            className={styles.refreshBtn}
            title="Reload skills registry"
          >
            <RotateCcw size={12} />
          </button>
        </div>
        <div className={styles.subtitle}>
          Extensible cognitive tools automatically orchestrated by the autonomous browser agent.
        </div>
      </div>

      {/* Search Input */}
      <div className={styles.searchBox}>
        <Search size={13} style={{ color: 'var(--text-muted)' }} />
        <input
          type="text"
          placeholder="Filter skills or tools (/skill:...)"
          value={searchQuery}
          onChange={e => setSearchQuery(e.target.value)}
          className={styles.searchInput}
        />
      </div>

      {/* Category Filter Chips */}
      <div className={styles.categoryStrip}>
        {CATEGORIES.map(cat => (
          <button
            key={cat}
            onClick={() => setSelectedCategory(cat)}
            className={`${styles.categoryChip} ${selectedCategory === cat ? styles.categoryChipActive : ''}`}
          >
            {cat.charAt(0).toUpperCase() + cat.slice(1)}
          </button>
        ))}
      </div>

      {/* Stats Bar */}
      <div className={styles.statsBar}>
        <span>{activeCount} of {(skills || []).length} active skills</span>
        <span>{totalTools} tools registered</span>
      </div>

      {/* Skills List */}
      <div className={styles.skillsList}>
        {filteredSkills.map(skill => {
          const isExpanded = expandedSkillIds.has(skill.id);
          return (
            <div
              key={skill.id}
              className={`${styles.skillCard} ${!skill.enabled ? styles.skillCardDisabled : ''}`}
            >
              {/* Card Header */}
              <div className={styles.skillCardHeader}>
                <div
                  className={styles.skillTitleArea}
                  onClick={() => toggleExpand(skill.id)}
                >
                  <div className={styles.skillIconWrap}>
                    {getSkillIcon(skill.icon)}
                  </div>
                  <div className={styles.skillNameRow}>
                    <div className={styles.skillName}>{skill.name}</div>
                    <div className={styles.skillCategoryBadge}>{skill.category}</div>
                  </div>
                  <div style={{ marginLeft: 'auto', color: 'var(--text-muted)' }}>
                    {isExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                  </div>
                </div>

                {/* Toggle Enable Switch */}
                <div
                  className={`${styles.toggleSwitch} ${skill.enabled ? styles.toggleSwitchActive : ''}`}
                  onClick={() => toggleSkill(skill.id, !skill.enabled)}
                  title={skill.enabled ? 'Click to disable' : 'Click to enable'}
                >
                  <div className={`${styles.toggleThumb} ${skill.enabled ? styles.toggleThumbActive : ''}`} />
                </div>
              </div>

              {/* Description */}
              <div className={styles.skillDesc}>{skill.description}</div>

              {/* Trigger Chips */}
              {skill.triggers && skill.triggers.length > 0 && (
                <div className={styles.triggerRow}>
                  {skill.triggers.slice(0, 5).map(tr => (
                    <span key={tr} className={styles.triggerPill}>
                      {tr}
                    </span>
                  ))}
                </div>
              )}

              {/* Expanded Tools Accordion */}
              {isExpanded && (
                <div className={styles.toolsAccordion}>
                  <div style={{ fontSize: '10px', fontWeight: 600, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '4px' }}>
                    <span>Tools & Operations ({skill.tools?.length || 0}):</span>
                  </div>

                  {skill.tools?.map(t => {
                    const isRunning = runningTool === t.name;
                    const output = toolOutputs[t.name];

                    return (
                      <div key={t.name} className={styles.toolItem}>
                        <div className={styles.toolHeader}>
                          <span className={styles.toolNameBadge}>{t.name}</span>
                          <span
                            className={
                              t.riskTier === 'red'
                                ? styles.riskBadgeRed
                                : t.riskTier === 'yellow'
                                ? styles.riskBadgeYellow
                                : styles.riskBadgeGreen
                            }
                          >
                            {t.riskTier === 'red' ? 'RED: Approval' : t.riskTier === 'yellow' ? 'YELLOW: Notify' : 'GREEN: Auto'}
                          </span>
                        </div>

                        <div className={styles.toolDesc}>{t.description}</div>

                        <div className={styles.toolActionRow}>
                          <button
                            onClick={() => handleRunTool(skill.id, t.name)}
                            disabled={isRunning || !skill.enabled}
                            className={styles.runToolBtn}
                          >
                            <Play size={10} />
                            <span>{isRunning ? 'Running...' : 'Test Run'}</span>
                          </button>
                        </div>

                        {output && (
                          <div className={styles.toolOutputBox}>
                            {output}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};
