/**
 * IndustryPanel - Browse and select industry modules
 * Shows available industries with their document counts
 */

import { useState, useEffect } from 'react';
import { useMonisterStore } from '../stores/monisterStore';
import type { IndustryDocument } from '../types';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export function IndustryPanel() {
    const { industries, setIndustries, activeIndustry, setActiveIndustry } = useMonisterStore();
    const [documents, setDocuments] = useState<IndustryDocument[]>([]);
    const [loading, setLoading] = useState(false);
    const [expanded, setExpanded] = useState(true);

    // Fetch industries on mount
    useEffect(() => {
        const fetchIndustries = async () => {
            try {
                const res = await fetch(`${API_BASE}/api/industries`);
                if (res.ok) {
                    const data = await res.json();
                    setIndustries(data.industries);
                }
            } catch (err) {
                console.error('Failed to fetch industries:', err);
            }
        };
        if (industries.length === 0) {
            fetchIndustries();
        }
    }, []);

    // Fetch documents when industry selected
    useEffect(() => {
        if (!activeIndustry) {
            setDocuments([]);
            return;
        }
        setLoading(true);
        fetch(`${API_BASE}/api/industries/${activeIndustry}`)
            .then(r => r.json())
            .then(data => {
                setDocuments(data.documents || []);
                setLoading(false);
            })
            .catch(() => setLoading(false));
    }, [activeIndustry]);

    return (
        <div className="industry-panel">
            <div
                className="industry-panel-header"
                onClick={() => setExpanded(!expanded)}
            >
                <span className="industry-panel-title">🏢 Soha modullari</span>
                <span className={`expand-arrow ${expanded ? 'expanded' : ''}`}>▼</span>
            </div>

            {expanded && (
                <div className="industry-panel-content">
                    {/* Industry grid */}
                    <div className="industry-grid">
                        {industries.map((ind) => (
                            <button
                                key={ind.id}
                                className={`industry-card ${activeIndustry === ind.id ? 'active' : ''}`}
                                onClick={() => setActiveIndustry(activeIndustry === ind.id ? null : ind.id)}
                                title={ind.description_uz}
                            >
                                <span className="industry-icon">{ind.icon}</span>
                                <span className="industry-name">{ind.name_uz}</span>
                                <span className="industry-count">{ind.document_count}</span>
                            </button>
                        ))}
                    </div>

                    {/* Documents list */}
                    {activeIndustry && (
                        <div className="industry-documents">
                            {loading ? (
                                <div className="loading-mini">Yuklanmoqda...</div>
                            ) : documents.length > 0 ? (
                                documents.map((doc) => (
                                    <div key={doc.id} className="industry-doc-item">
                                        <div className="doc-item-header">
                                            <span className={`doc-template-badge ${doc.has_template ? 'has-template' : ''}`}>
                                                {doc.has_template ? '✅' : '📝'}
                                            </span>
                                            <span className="doc-item-name">{doc.name_uz}</span>
                                        </div>
                                        <div className="doc-item-desc">{doc.description}</div>
                                        {doc.required_fields.length > 0 && (
                                            <div className="doc-item-fields">
                                                {doc.required_fields.slice(0, 4).map(f => (
                                                    <span key={f} className="field-tag">{f}</span>
                                                ))}
                                                {doc.required_fields.length > 4 && (
                                                    <span className="field-tag more">+{doc.required_fields.length - 4}</span>
                                                )}
                                            </div>
                                        )}
                                        {doc.compliance_rules.length > 0 && (
                                            <div className="doc-item-rules">
                                                {doc.compliance_rules.map((rule, i) => (
                                                    <span key={i} className="rule-tag">⚠️ {rule}</span>
                                                ))}
                                            </div>
                                        )}
                                    </div>
                                ))
                            ) : (
                                <div className="no-docs">Hujjatlar topilmadi</div>
                            )}
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}
