/**
 * HITL Modal Component
 * Human-in-the-Loop approval dialog
 */

import { CheckCircle, XCircle, AlertTriangle } from 'lucide-react';
import { useMonisterStore } from '../stores/monisterStore';
import { useWebSocket } from '../hooks/useWebSocket';

export function HITLModal() {
    const { hitlRequest, setHITLRequest } = useMonisterStore();
    const { sendHITLResponse } = useWebSocket();

    if (!hitlRequest) return null;

    const handleApprove = () => {
        sendHITLResponse(hitlRequest.id, 'approve');
    };

    const handleReject = () => {
        sendHITLResponse(hitlRequest.id, 'reject');
    };

    return (
        <div className="hitl-overlay">
            <div className="hitl-modal">
                <div className="hitl-header">
                    <AlertTriangle className="hitl-icon" />
                    <h3>Agent Approval Required</h3>
                </div>

                <div className="hitl-content">
                    <p>{hitlRequest.message}</p>
                </div>

                <div className="hitl-actions">
                    <button className="hitl-btn reject" onClick={handleReject}>
                        <XCircle size={18} />
                        Reject
                    </button>
                    <button className="hitl-btn approve" onClick={handleApprove}>
                        <CheckCircle size={18} />
                        Approve
                    </button>
                </div>

                <div className="hitl-hint">
                    <span>Agent is waiting for your decision...</span>
                </div>
            </div>
        </div>
    );
}
