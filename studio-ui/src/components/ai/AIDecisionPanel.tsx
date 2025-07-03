/**
 * AI Decision Panel - Phase 4 AI Integration Component
 * Transparency dashboard for AI decisions and reasoning
 */

'use client';

import React, { useState, useCallback, useMemo } from 'react';
import { AIDecision, CutSuggestion, QualityMetrics } from '@/types';

interface AIDecisionPanelProps {
  decisions: AIDecision[];
  isVisible: boolean;
  onToggleDecision?: (decisionId: string) => void;
  onAcceptDecision?: (decisionId: string) => void;
  onRejectDecision?: (decisionId: string) => void;
  className?: string;
}

export const AIDecisionPanel: React.FC<AIDecisionPanelProps> = ({
  decisions,
  isVisible,
  onToggleDecision,
  onAcceptDecision,
  onRejectDecision,
  className = '',
}) => {
  const [activeTab, setActiveTab] = useState<'all' | 'cuts' | 'quality' | 'reframing'>('all');
  const [sortBy, setSortBy] = useState<'confidence' | 'timestamp' | 'type'>('confidence');
  const [filterConfidence, setFilterConfidence] = useState(0);
  
  // Filter and sort decisions
  const filteredDecisions = useMemo(() => {
    let filtered = decisions.filter(decision => {
      if (decision.confidence < filterConfidence) return false;
      if (activeTab === 'all') return true;
      if (activeTab === 'cuts') return decision.type === 'cut_suggestion';
      if (activeTab === 'quality') return decision.type === 'quality_assessment';
      if (activeTab === 'reframing') return decision.type === 'reframing';
      return true;
    });
    
    filtered.sort((a, b) => {
      switch (sortBy) {
        case 'confidence':
          return b.confidence - a.confidence;
        case 'timestamp':
          return b.timestamp - a.timestamp;
        case 'type':
          return a.type.localeCompare(b.type);
        default:
          return 0;
      }
    });
    
    return filtered;
  }, [decisions, activeTab, sortBy, filterConfidence]);
  
  // Get decision icon
  const getDecisionIcon = useCallback((type: string) => {
    switch (type) {
      case 'cut_suggestion': return '✂️';
      case 'quality_assessment': return '📊';
      case 'reframing': return '🎯';
      case 'filler_removal': return '🗑️';
      default: return '🤖';
    }
  }, []);
  
  // Get confidence color
  const getConfidenceColor = useCallback((confidence: number) => {
    if (confidence >= 0.8) return 'text-editor-success';
    if (confidence >= 0.6) return 'text-editor-warning';
    return 'text-editor-error';
  }, []);
  
  // Get confidence background
  const getConfidenceBackground = useCallback((confidence: number) => {
    if (confidence >= 0.8) return 'bg-editor-success/20';
    if (confidence >= 0.6) return 'bg-editor-warning/20';
    return 'bg-editor-error/20';
  }, []);
  
  if (!isVisible) return null;
  
  return (
    <div className={`ai-decision-panel bg-editor-surface border border-editor-border rounded-lg ${className}`}>
      {/* Header */}
      <div className="p-4 border-b border-editor-border">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-medium text-editor-text-primary">AI Decisions</h3>
          <div className="flex items-center gap-2">
            <span className="text-sm text-editor-text-secondary">
              {filteredDecisions.length} decisions
            </span>
            
            {/* Sort selector */}
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as any)}
              className="form-input text-sm"
            >
              <option value="confidence">Sort by Confidence</option>
              <option value="timestamp">Sort by Time</option>
              <option value="type">Sort by Type</option>
            </select>
          </div>
        </div>
        
        {/* Tabs */}
        <div className="flex items-center gap-1">
          {['all', 'cuts', 'quality', 'reframing'].map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab as any)}
              className={`
                px-3 py-1.5 rounded text-sm font-medium transition-colors
                ${activeTab === tab
                  ? 'bg-editor-accent text-white'
                  : 'text-editor-text-secondary hover:text-editor-text-primary hover:bg-editor-border'
                }
              `}
            >
              {tab.charAt(0).toUpperCase() + tab.slice(1)}
            </button>
          ))}
        </div>
        
        {/* Confidence filter */}
        <div className="mt-3 flex items-center gap-2">
          <label className="text-sm text-editor-text-secondary">
            Min Confidence:
          </label>
          <input
            type="range"
            min="0"
            max="1"
            step="0.1"
            value={filterConfidence}
            onChange={(e) => setFilterConfidence(parseFloat(e.target.value))}
            className="w-20"
          />
          <span className="text-sm text-editor-text-primary">
            {(filterConfidence * 100).toFixed(0)}%
          </span>
        </div>
      </div>
      
      {/* Decision list */}
      <div className="max-h-96 overflow-y-auto">
        {filteredDecisions.length === 0 ? (
          <div className="p-8 text-center text-editor-text-secondary">
            No decisions match the current filters
          </div>
        ) : (
          <div className="space-y-2 p-2">
            {filteredDecisions.map((decision) => (
              <AIDecisionCard
                key={decision.id}
                decision={decision}
                onToggle={onToggleDecision}
                onAccept={onAcceptDecision}
                onReject={onRejectDecision}
                getIcon={getDecisionIcon}
                getConfidenceColor={getConfidenceColor}
                getConfidenceBackground={getConfidenceBackground}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

// Individual decision card component
const AIDecisionCard: React.FC<{
  decision: AIDecision;
  onToggle?: (id: string) => void;
  onAccept?: (id: string) => void;
  onReject?: (id: string) => void;
  getIcon: (type: string) => string;
  getConfidenceColor: (confidence: number) => string;
  getConfidenceBackground: (confidence: number) => string;
}> = ({
  decision,
  onToggle,
  onAccept,
  onReject,
  getIcon,
  getConfidenceColor,
  getConfidenceBackground,
}) => {
  const [isExpanded, setIsExpanded] = useState(false);
  
  const formatTime = (timestamp: number) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString();
  };
  
  const renderDecisionData = () => {
    if (decision.type === 'cut_suggestion') {
      const cutData = decision as CutSuggestion;
      return (
        <div className="mt-2 text-sm">
          <div className="flex justify-between text-editor-text-secondary">
            <span>Start: {cutData.startTime.toFixed(1)}s</span>
            <span>End: {cutData.endTime.toFixed(1)}s</span>
            <span>Score: {cutData.score.toFixed(2)}</span>
          </div>
          
          {cutData.alternatives && cutData.alternatives.length > 0 && (
            <div className="mt-2">
              <div className="text-editor-text-secondary text-xs mb-1">Alternatives:</div>
              {cutData.alternatives.slice(0, 2).map((alt, index) => (
                <div key={index} className="text-xs text-editor-text-muted">
                  {alt.startTime.toFixed(1)}s - {alt.endTime.toFixed(1)}s (Score: {alt.score.toFixed(2)})
                </div>
              ))}
            </div>
          )}
        </div>
      );
    }
    
    if (decision.type === 'quality_assessment') {
      const quality = decision.data as QualityMetrics;
      return (
        <div className="mt-2 grid grid-cols-2 gap-2 text-sm">
          <div>Audio: {(quality.audio * 100).toFixed(0)}%</div>
          <div>Visual: {(quality.visual * 100).toFixed(0)}%</div>
          <div>Semantic: {(quality.semantic * 100).toFixed(0)}%</div>
          <div>Engagement: {(quality.engagement * 100).toFixed(0)}%</div>
        </div>
      );
    }
    
    return null;
  };
  
  return (
    <div className={`
      ai-decision-card border border-editor-border rounded-lg p-3 
      ${getConfidenceBackground(decision.confidence)}
      ${decision.userOverride ? 'opacity-60' : ''}
    `}>
      <div className="flex items-start justify-between">
        {/* Decision info */}
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-lg">{getIcon(decision.type)}</span>
            <span className="font-medium text-editor-text-primary">
              {decision.type.replace('_', ' ').toUpperCase()}
            </span>
            <span className={`text-sm font-medium ${getConfidenceColor(decision.confidence)}`}>
              {(decision.confidence * 100).toFixed(0)}%
            </span>
            {decision.userOverride && (
              <span className="text-xs bg-editor-warning text-white px-2 py-0.5 rounded">
                OVERRIDDEN
              </span>
            )}
          </div>
          
          <p className="text-sm text-editor-text-secondary mb-2">
            {decision.reasoning}
          </p>
          
          {renderDecisionData()}
          
          <div className="text-xs text-editor-text-muted mt-2">
            {formatTime(decision.timestamp)}
          </div>
        </div>
        
        {/* Actions */}
        <div className="flex items-center gap-1 ml-3">
          {!decision.userOverride && (
            <>
              <button
                onClick={() => onAccept?.(decision.id)}
                className="w-6 h-6 bg-editor-success text-white rounded text-xs hover:bg-opacity-80 transition-colors"
                title="Accept decision"
              >
                ✓
              </button>
              
              <button
                onClick={() => onReject?.(decision.id)}
                className="w-6 h-6 bg-editor-error text-white rounded text-xs hover:bg-opacity-80 transition-colors"
                title="Reject decision"
              >
                ✕
              </button>
            </>
          )}
          
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="w-6 h-6 bg-editor-border text-editor-text-primary rounded text-xs hover:bg-editor-border/80 transition-colors"
            title="Toggle details"
          >
            {isExpanded ? '−' : '+'}
          </button>
        </div>
      </div>
      
      {/* Expanded details */}
      {isExpanded && (
        <div className="mt-3 pt-3 border-t border-editor-border">
          <div className="text-sm space-y-2">
            <div>
              <span className="text-editor-text-secondary">Decision ID:</span>
              <span className="ml-2 font-mono text-xs text-editor-text-muted">{decision.id}</span>
            </div>
            
            {decision.data && (
              <div>
                <span className="text-editor-text-secondary">Raw Data:</span>
                <pre className="mt-1 p-2 bg-editor-background rounded text-xs font-mono overflow-x-auto">
                  {JSON.stringify(decision.data, null, 2)}
                </pre>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

// AI Decision summary widget
export const AIDecisionSummary: React.FC<{
  decisions: AIDecision[];
  className?: string;
}> = ({ decisions, className = '' }) => {
  const stats = useMemo(() => {
    const total = decisions.length;
    const accepted = decisions.filter(d => d.userOverride === false).length;
    const rejected = decisions.filter(d => d.userOverride === true).length;
    const pending = total - accepted - rejected;
    const avgConfidence = decisions.reduce((sum, d) => sum + d.confidence, 0) / total || 0;
    
    return { total, accepted, rejected, pending, avgConfidence };
  }, [decisions]);
  
  return (
    <div className={`ai-decision-summary bg-editor-surface border border-editor-border rounded-lg p-3 ${className}`}>
      <h4 className="text-sm font-medium text-editor-text-primary mb-2">AI Decision Summary</h4>
      
      <div className="grid grid-cols-2 gap-2 text-sm">
        <div>
          <span className="text-editor-text-secondary">Total:</span>
          <span className="ml-2 text-editor-text-primary">{stats.total}</span>
        </div>
        
        <div>
          <span className="text-editor-text-secondary">Accepted:</span>
          <span className="ml-2 text-editor-success">{stats.accepted}</span>
        </div>
        
        <div>
          <span className="text-editor-text-secondary">Rejected:</span>
          <span className="ml-2 text-editor-error">{stats.rejected}</span>
        </div>
        
        <div>
          <span className="text-editor-text-secondary">Pending:</span>
          <span className="ml-2 text-editor-warning">{stats.pending}</span>
        </div>
      </div>
      
      <div className="mt-2 pt-2 border-t border-editor-border">
        <div className="text-sm">
          <span className="text-editor-text-secondary">Avg Confidence:</span>
          <span className="ml-2 text-editor-text-primary">
            {(stats.avgConfidence * 100).toFixed(0)}%
          </span>
        </div>
      </div>
    </div>
  );
};