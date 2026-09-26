/**
 * Template Gallery Component
 * 
 * Displays available templates for user selection.
 * Supports multi-select, filtering, and automatic matching.
 */

import React, { useState, useMemo } from 'react';
import './TemplateGallery.css';

interface Template {
    id: string;
    name: string;
    description?: string;
    category: string;
    organization?: string;
    preview_image?: string;
    match_score?: number;
    required_fields?: string[];
    tags?: string[];
}

interface TemplateGalleryProps {
    templates: Template[];
    allowMultiple?: boolean;
    maxSelections?: number;
    preselected?: string[];
    showMatchScores?: boolean;
    onSelect: (templateIds: string[]) => void;
    onCancel?: () => void;
    title?: string;
    subtitle?: string;
}

export function TemplateGallery({
    templates,
    allowMultiple = true,
    maxSelections = 5,
    preselected = [],
    showMatchScores = true,
    onSelect,
    onCancel,
    title = "Shablon tanlang",
    subtitle,
}: TemplateGalleryProps) {
    const [selected, setSelected] = useState<Set<string>>(new Set(preselected));
    const [searchQuery, setSearchQuery] = useState('');
    const [categoryFilter, setCategoryFilter] = useState<string>('all');
    const [sortBy, setSortBy] = useState<'match' | 'name' | 'category'>('match');

    // Get unique categories
    const categories = useMemo(() => {
        const cats = new Set<string>();
        templates.forEach(t => cats.add(t.category));
        return ['all', ...Array.from(cats)];
    }, [templates]);

    // Filter and sort templates
    const filteredTemplates = useMemo(() => {
        let result = templates;

        // Filter by search query
        if (searchQuery) {
            const query = searchQuery.toLowerCase();
            result = result.filter(t =>
                t.name.toLowerCase().includes(query) ||
                t.description?.toLowerCase().includes(query) ||
                t.tags?.some(tag => tag.toLowerCase().includes(query))
            );
        }

        // Filter by category
        if (categoryFilter !== 'all') {
            result = result.filter(t => t.category === categoryFilter);
        }

        // Sort
        result = [...result].sort((a, b) => {
            switch (sortBy) {
                case 'match':
                    return (b.match_score || 0) - (a.match_score || 0);
                case 'name':
                    return a.name.localeCompare(b.name);
                case 'category':
                    return a.category.localeCompare(b.category);
                default:
                    return 0;
            }
        });

        return result;
    }, [templates, searchQuery, categoryFilter, sortBy]);

    // Toggle selection
    const toggleSelection = (templateId: string) => {
        setSelected(prev => {
            const newSet = new Set(prev);

            if (newSet.has(templateId)) {
                newSet.delete(templateId);
            } else {
                if (!allowMultiple) {
                    newSet.clear();
                }
                if (newSet.size < maxSelections) {
                    newSet.add(templateId);
                }
            }

            return newSet;
        });
    };

    // Select all visible
    const selectAll = () => {
        const ids = filteredTemplates.slice(0, maxSelections).map(t => t.id);
        setSelected(new Set(ids));
    };

    // Clear selection
    const clearSelection = () => {
        setSelected(new Set());
    };

    // Handle continue
    const handleContinue = () => {
        onSelect(Array.from(selected));
    };

    return (
        <div className="template-gallery">
            {/* Header */}
            <div className="gallery-header">
                <div className="header-text">
                    <h3>{title}</h3>
                    {subtitle && <p className="subtitle">{subtitle}</p>}
                </div>
                <div className="selection-count">
                    <span className="count">{selected.size}</span>
                    <span className="label">tanlandi</span>
                </div>
            </div>

            {/* Filters */}
            <div className="gallery-filters">
                <div className="search-box">
                    <span className="search-icon">🔍</span>
                    <input
                        type="text"
                        placeholder="Shablon qidirish..."
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                    />
                </div>

                <div className="filter-controls">
                    <select
                        value={categoryFilter}
                        onChange={(e) => setCategoryFilter(e.target.value)}
                        className="category-filter"
                    >
                        {categories.map(cat => (
                            <option key={cat} value={cat}>
                                {cat === 'all' ? 'Barcha kategoriyalar' : cat}
                            </option>
                        ))}
                    </select>

                    <select
                        value={sortBy}
                        onChange={(e) => setSortBy(e.target.value as any)}
                        className="sort-filter"
                    >
                        <option value="match">Moslik bo'yicha</option>
                        <option value="name">Nom bo'yicha</option>
                        <option value="category">Kategoriya bo'yicha</option>
                    </select>
                </div>

                <div className="quick-actions">
                    <button onClick={selectAll} className="quick-btn">
                        Barchasini tanlash
                    </button>
                    <button onClick={clearSelection} className="quick-btn">
                        Tozalash
                    </button>
                </div>
            </div>

            {/* Template Grid */}
            <div className="template-grid">
                {filteredTemplates.map(template => (
                    <TemplateCard
                        key={template.id}
                        template={template}
                        selected={selected.has(template.id)}
                        showMatchScore={showMatchScores}
                        onToggle={() => toggleSelection(template.id)}
                    />
                ))}

                {filteredTemplates.length === 0 && (
                    <div className="no-templates">
                        <p>Hech qanday shablon topilmadi</p>
                    </div>
                )}
            </div>

            {/* Actions */}
            <div className="gallery-actions">
                {onCancel && (
                    <button onClick={onCancel} className="cancel-btn">
                        Bekor qilish
                    </button>
                )}
                <button
                    onClick={handleContinue}
                    disabled={selected.size === 0}
                    className="continue-btn"
                >
                    Davom etish ({selected.size})
                </button>
            </div>
        </div>
    );
}

// Template Card Component
interface TemplateCardProps {
    template: Template;
    selected: boolean;
    showMatchScore: boolean;
    onToggle: () => void;
}

function TemplateCard({ template, selected, showMatchScore, onToggle }: TemplateCardProps) {
    const matchPercent = template.match_score ? Math.round(template.match_score * 100) : null;

    return (
        <div
            className={`template-card ${selected ? 'selected' : ''}`}
            onClick={onToggle}
        >
            {/* Selection indicator */}
            <div className="selection-indicator">
                {selected ? '✓' : ''}
            </div>

            {/* Match score badge */}
            {showMatchScore && matchPercent !== null && (
                <div className={`match-badge ${matchPercent >= 80 ? 'high' : matchPercent >= 50 ? 'medium' : 'low'}`}>
                    {matchPercent}% mos
                </div>
            )}

            {/* Preview image */}
            <div className="template-preview">
                {template.preview_image ? (
                    <img src={template.preview_image} alt={template.name} />
                ) : (
                    <div className="preview-placeholder">
                        <span>📄</span>
                    </div>
                )}
            </div>

            {/* Info */}
            <div className="template-info">
                <h4 className="template-name">{template.name}</h4>
                {template.description && (
                    <p className="template-description">{template.description}</p>
                )}
                <div className="template-meta">
                    <span className="category-tag">{template.category}</span>
                    {template.organization && (
                        <span className="org-tag">{template.organization}</span>
                    )}
                </div>
            </div>

            {/* Required fields */}
            {template.required_fields && template.required_fields.length > 0 && (
                <div className="required-fields">
                    <span className="fields-label">Kerakli maydonlar:</span>
                    <div className="fields-list">
                        {template.required_fields.slice(0, 3).map(field => (
                            <span key={field} className="field-chip">{field}</span>
                        ))}
                        {template.required_fields.length > 3 && (
                            <span className="field-chip more">+{template.required_fields.length - 3}</span>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
}

export default TemplateGallery;
