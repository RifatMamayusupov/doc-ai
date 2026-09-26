'use client';

import { useState } from 'react';
import { motion } from 'framer-motion';
import { Check, Building2, FileText } from 'lucide-react';
import { Template, useUIStore } from '@/lib/store';
import { wsClient } from '@/lib/websocket';

interface TemplateDropdownProps {
    templates: Template[];
}

export default function TemplateDropdown({ templates }: TemplateDropdownProps) {
    const [selectedId, setSelectedId] = useState<string | null>(null);
    const { setSuggestedTemplates, setPreviewPanelOpen } = useUIStore();

    const handleSelect = (template: Template) => {
        setSelectedId(template.id);
        wsClient.selectTemplate(template.id);

        // Auto-close after selection
        setTimeout(() => {
            setSuggestedTemplates([]);
            setPreviewPanelOpen(false);
        }, 500);
    };

    // Group templates by organization
    const groupedTemplates = templates.reduce((acc, template) => {
        if (!acc[template.organization]) {
            acc[template.organization] = [];
        }
        acc[template.organization].push(template);
        return acc;
    }, {} as Record<string, Template[]>);

    return (
        <div className="space-y-4">
            <p className="text-sm text-dark-400">
                Quyidagi shablonlardan birini tanlang:
            </p>

            {Object.entries(groupedTemplates).map(([org, orgTemplates]) => (
                <div key={org} className="space-y-2">
                    {/* Organization header */}
                    <div className="flex items-center gap-2 text-dark-300">
                        <Building2 className="w-4 h-4" />
                        <span className="text-sm font-medium">{org}</span>
                    </div>

                    {/* Templates grid */}
                    <div className="grid gap-2">
                        {orgTemplates.map((template) => (
                            <motion.button
                                key={template.id}
                                onClick={() => handleSelect(template)}
                                whileHover={{ scale: 1.02 }}
                                whileTap={{ scale: 0.98 }}
                                className={`w-full text-left p-3 rounded-xl border transition-all ${selectedId === template.id
                                        ? 'bg-primary/20 border-primary'
                                        : 'bg-dark-800 border-dark-600 hover:border-dark-500'
                                    }`}
                            >
                                <div className="flex items-start gap-3">
                                    {/* Preview thumbnail */}
                                    <div className="w-12 h-12 bg-dark-700 rounded-lg flex items-center justify-center flex-shrink-0">
                                        {template.preview_image ? (
                                            <img
                                                src={template.preview_image}
                                                alt={template.name}
                                                className="w-full h-full object-cover rounded-lg"
                                            />
                                        ) : (
                                            <FileText className="w-6 h-6 text-dark-400" />
                                        )}
                                    </div>

                                    {/* Info */}
                                    <div className="flex-1 min-w-0">
                                        <div className="flex items-center justify-between">
                                            <h4 className="font-medium text-white truncate">
                                                {template.name}
                                            </h4>
                                            {selectedId === template.id && (
                                                <Check className="w-5 h-5 text-primary flex-shrink-0" />
                                            )}
                                        </div>
                                        <p className="text-xs text-dark-400 mt-0.5">
                                            {template.category}
                                        </p>
                                    </div>
                                </div>
                            </motion.button>
                        ))}
                    </div>
                </div>
            ))}
        </div>
    );
}
