/**
 * Template Dropdown Component - Organization templates selector
 */

import { useState, useRef, useEffect } from 'react';
import { FileDown, ChevronDown, Search, File, FileText, FolderOpen, X } from 'lucide-react';
import { useMonisterStore } from '../stores/monisterStore';
import type { Template } from '../types';

export function TemplateDropdown() {
    const [isOpen, setIsOpen] = useState(false);
    const [searchQuery, setSearchQuery] = useState('');
    const [expandedCategories, setExpandedCategories] = useState<string[]>([]);
    const [recommendedIds, setRecommendedIds] = useState<string[] | null>(null);
    const [isSearching, setIsSearching] = useState(false);
    const dropdownRef = useRef<HTMLDivElement>(null);

    const { templates: rawTemplates, selectedTemplate, selectTemplate } = useMonisterStore();
    const templates = rawTemplates ?? [];

    // Close dropdown when clicking outside
    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
                setIsOpen(false);
            }
        };

        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    // AI Recommendation
    useEffect(() => {
        const fetchRecommendations = async () => {
            if (searchQuery.length < 3) {
                setRecommendedIds(null);
                return;
            }

            setIsSearching(true);
            try {
                const res = await fetch('http://localhost:8000/api/templates/recommend', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ query: searchQuery })
                });
                const data = await res.json();
                if (data.recommendations) {
                    setRecommendedIds(data.recommendations.map((t: any) => t.id));
                }
            } catch (e) {
                console.error("Rec error", e);
            } finally {
                setIsSearching(false);
            }
        };

        const timeoutId = setTimeout(fetchRecommendations, 500);
        return () => clearTimeout(timeoutId);
    }, [searchQuery]);

    // Filter logic
    const filteredTemplates = templates.filter(t => {
        if (recommendedIds && recommendedIds.length > 0) {
            // If we have recommendations, show ONLY them or boost them?
            // Let's show everything that matches query OR is recommended
            return recommendedIds.includes(t.id) ||
                t.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                t.category.toLowerCase().includes(searchQuery.toLowerCase());
        }
        if (!searchQuery) return true;
        return t.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
            t.category.toLowerCase().includes(searchQuery.toLowerCase());
    });

    // Sort logic: Recommended first
    const sortedTemplates = [...filteredTemplates].sort((a, b) => {
        if (recommendedIds && recommendedIds.length > 0) {
            const indexA = recommendedIds.indexOf(a.id);
            const indexB = recommendedIds.indexOf(b.id);

            // Both recommended
            if (indexA !== -1 && indexB !== -1) return indexA - indexB;
            // A recommended
            if (indexA !== -1) return -1;
            // B recommended
            if (indexB !== -1) return 1;
        }
        return 0; // Keep original order otherwise
    });

    // Grouping
    const groupedTemplates = sortedTemplates.reduce((acc, template) => {
        if (!acc[template.category]) {
            acc[template.category] = [];
        }
        acc[template.category].push(template);
        return acc;
    }, {} as Record<string, Template[]>);

    const toggleCategory = (category: string) => {
        setExpandedCategories((prev) =>
            prev.includes(category)
                ? prev.filter((c) => c !== category)
                : [...prev, category]
        );
    };

    const handleSelectTemplate = (template: Template) => {
        selectTemplate(template);
        setIsOpen(false);

        // Also open preview for the template
        handlePreviewTemplate(template);
    };

    const handlePreviewTemplate = (template: Template) => {
        // Determine file type from path
        const path = template.path.toLowerCase();
        type PreviewType = 'none' | 'excel' | 'pdf' | 'image' | 'text' | 'json' | 'video' | 'spreadsheet' | 'code' | 'docx' | 'word' | 'html' | 'audio' | 'archive' | 'presentation' | 'file';
        let fileType: PreviewType = 'text';
        if (path.endsWith('.html') || path.endsWith('.htm')) fileType = 'html';
        else if (path.endsWith('.docx') || path.endsWith('.doc')) fileType = 'docx';
        else if (path.endsWith('.pdf')) fileType = 'pdf';
        else if (path.endsWith('.xlsx') || path.endsWith('.xls')) fileType = 'excel';

        // Use the relative path from templates directory (includes subdirectory)
        // template.path is already relative to templates dir, e.g. "Hisobot/oylik_hisobot.html"
        const previewUrl = `http://localhost:8000/templates/${template.path}`;

        // Set preview data
        useMonisterStore.getState().setPreviewData({
            tool: 'template_preview',
            content: '',
            url: previewUrl,
            type: fileType,
            timestamp: new Date().toISOString(),
        });

        useMonisterStore.getState().setPreviewType(fileType);
        useMonisterStore.getState().setPreviewOpen(true);
    };

    const handleClearSelection = (e: React.MouseEvent) => {
        e.stopPropagation();
        selectTemplate(null);
    };

    const getFileIcon = (path: string) => {
        if (path.endsWith('.docx') || path.endsWith('.doc')) return <FileText size={16} />;
        if (path.endsWith('.pdf')) return <File size={16} className="pdf-icon" />;
        return <File size={16} />;
    };

    return (
        <div className="template-dropdown" ref={dropdownRef}>
            {/* Trigger Button */}
            <button
                className={`template-trigger ${isOpen ? 'active' : ''} ${selectedTemplate ? 'has-selection' : ''}`}
                onClick={() => setIsOpen(!isOpen)}
                title="Shablonlar"
            >
                <FileDown size={18} />
                {selectedTemplate && (
                    <span className="selected-name">{selectedTemplate.name}</span>
                )}
                <ChevronDown size={16} className={`chevron ${isOpen ? 'rotated' : ''}`} />
            </button>

            {/* Selected Template Clear */}
            {selectedTemplate && (
                <button className="clear-template" onClick={handleClearSelection} title="Tanlashni bekor qilish">
                    <X size={14} />
                </button>
            )}

            {/* Dropdown Menu */}
            {isOpen && (
                <div className="template-menu">
                    {/* Search */}
                    <div className="template-search">
                        <Search size={16} />
                        <input
                            type="text"
                            placeholder="Shablon qidirish..."
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                            autoFocus
                        />
                        {isSearching && <div className="spinner-sm" />}
                    </div>

                    {/* Template List */}
                    <div className="template-list">
                        {Object.keys(groupedTemplates).length === 0 ? (
                            <div className="no-templates">
                                <FolderOpen size={24} />
                                <p>Shablonlar topilmadi</p>
                            </div>
                        ) : (
                            Object.entries(groupedTemplates).map(([category, items]) => (
                                <div key={category} className="template-category">
                                    <button
                                        className="category-header"
                                        onClick={() => toggleCategory(category)}
                                    >
                                        <FolderOpen size={16} />
                                        <span className="category-name">{category}</span>
                                        <span className="category-count">{items.length}</span>
                                        <ChevronDown
                                            size={14}
                                            className={`chevron ${expandedCategories.includes(category) ? 'rotated' : ''}`}
                                        />
                                    </button>

                                    {expandedCategories.includes(category) && (
                                        <div className="category-items">
                                            {items.map((template) => (
                                                <button
                                                    key={template.id}
                                                    className={`template-item ${selectedTemplate?.id === template.id ? 'selected' : ''}`}
                                                    onClick={() => handleSelectTemplate(template)}
                                                >
                                                    {getFileIcon(template.path)}
                                                    <span className="template-name">{template.name}</span>
                                                    {recommendedIds?.includes(template.id) && <span className="badge-rec">AI</span>}
                                                </button>
                                            ))}
                                        </div>
                                    )}
                                </div>
                            ))
                        )}
                    </div>
                </div>
            )}
        </div>
    );
}
