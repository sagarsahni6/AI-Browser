import React, { useState, useEffect } from 'react';
import { FolderGit2, Plus, Trash2, Folder, BookOpen, ExternalLink } from 'lucide-react';
import styles from './CollectionsPanel.module.css';

interface Collection {
  id: string;
  name: string;
  description?: string;
  created_at: number;
}

export const CollectionsPanel: React.FC = () => {
  const [collections, setCollections] = useState<Collection[]>([]);
  const [showCreate, setShowCreate] = useState(false);
  const [name, setName] = useState('');
  const [desc, setDesc] = useState('');
  const [loading, setLoading] = useState(false);

  const loadCollections = async () => {
    if (window.electronAPI?.listCollections) {
      try {
        const list = await window.electronAPI.listCollections();
        setCollections(list || []);
      } catch (err) {
        console.error(err);
      }
    }
  };

  useEffect(() => {
    loadCollections();
  }, []);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim() || loading) return;

    setLoading(true);
    try {
      if (window.electronAPI?.createCollection) {
        await window.electronAPI.createCollection(name.trim(), desc.trim());
        setName('');
        setDesc('');
        setShowCreate(false);
        loadCollections();
      }
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (window.electronAPI?.deleteCollection) {
      await window.electronAPI.deleteCollection(id);
      loadCollections();
    }
  };

  return (
    <div className={styles.container}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <FolderGit2 size={14} style={{ color: 'var(--accent-primary)' }} />
          <span style={{ fontSize: '11px', fontWeight: 600, textTransform: 'uppercase' }}>
            Collections ({collections.length})
          </span>
        </div>
        <button
          onClick={() => setShowCreate(!showCreate)}
          style={{ fontSize: '11px', color: 'var(--accent-primary)', fontWeight: 600, cursor: 'pointer' }}
        >
          {showCreate ? 'Cancel' : '+ New'}
        </button>
      </div>

      {showCreate && (
        <form onSubmit={handleCreate} className={styles.createForm}>
          <input
            type="text"
            placeholder="Collection Name (e.g. AI Research)"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className={styles.input}
            required
            autoFocus
          />
          <input
            type="text"
            placeholder="Description (optional)"
            value={desc}
            onChange={(e) => setDesc(e.target.value)}
            className={styles.input}
          />
          <button type="submit" disabled={loading || !name.trim()} className={styles.submitBtn}>
            <Plus size={12} />
            <span>{loading ? 'Saving...' : 'Create Collection'}</span>
          </button>
        </form>
      )}

      {collections.length === 0 && !showCreate ? (
        <div style={{ fontSize: '11px', color: 'var(--text-muted)', textAlign: 'center', padding: '24px 8px' }}>
          No research collections yet. Save pages and cited summaries here.
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
          {collections.map(col => (
            <div key={col.id} className={styles.collectionCard}>
              <div className={styles.cardLeft}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <Folder size={13} style={{ color: 'var(--accent-primary)' }} />
                  <span className={styles.cardName}>{col.name}</span>
                </div>
                {col.description && <span className={styles.cardDesc}>{col.description}</span>}
              </div>
              <button
                onClick={(e) => handleDelete(col.id, e)}
                className={styles.deleteBtn}
                title="Delete Collection"
              >
                <Trash2 size={12} />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
