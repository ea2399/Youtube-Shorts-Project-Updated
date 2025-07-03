/**
 * Word-Level Editor - Phase 4 AI Integration Component
 * Precise word-level transcript editing with timeline synchronization
 */

'use client';

import React, { useState, useRef, useEffect, useCallback, useMemo } from 'react';
import { useTimelineStore } from '@/stores/timelineStore';

interface WordToken {
  id: string;
  text: string;
  startTime: number;
  endTime: number;
  confidence: number;
  speaker?: string;
  isFillerWord?: boolean;
  isEdited?: boolean;
  alternatives?: string[];
}

interface TranscriptSegment {
  id: string;
  startTime: number;
  endTime: number;
  words: WordToken[];
  speaker?: string;
}

interface WordLevelEditorProps {
  transcript: TranscriptSegment[];
  currentTime: number;
  isVisible: boolean;
  onWordEdit?: (wordId: string, newText: string) => void;
  onWordDelete?: (wordId: string) => void;
  onWordSplit?: (wordId: string, splitText: string[]) => void;
  onSeek?: (time: number) => void;
  className?: string;
}

export const WordLevelEditor: React.FC<WordLevelEditorProps> = ({
  transcript,
  currentTime,
  isVisible,
  onWordEdit,
  onWordDelete,
  onWordSplit,
  onSeek,
  className = '',
}) => {
  const [selectedWords, setSelectedWords] = useState<Set<string>>(new Set());
  const [editingWordId, setEditingWordId] = useState<string | null>(null);
  const [editText, setEditText] = useState('');
  const [showFillerWords, setShowFillerWords] = useState(true);
  const [highlightLowConfidence, setHighlightLowConfidence] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [autoScroll, setAutoScroll] = useState(true);
  
  const containerRef = useRef<HTMLDivElement>(null);
  const editInputRef = useRef<HTMLInputElement>(null);
  
  // Find current word being spoken
  const currentWordId = useMemo(() => {
    for (const segment of transcript) {
      for (const word of segment.words) {
        if (currentTime >= word.startTime && currentTime <= word.endTime) {
          return word.id;
        }
      }
    }
    return null;
  }, [transcript, currentTime]);
  
  // Filter transcript based on settings
  const filteredTranscript = useMemo(() => {
    return transcript.map(segment => ({
      ...segment,
      words: segment.words.filter(word => {
        if (!showFillerWords && word.isFillerWord) return false;
        if (searchTerm) {
          return word.text.toLowerCase().includes(searchTerm.toLowerCase());
        }
        return true;
      })
    })).filter(segment => segment.words.length > 0);
  }, [transcript, showFillerWords, searchTerm]);
  
  // Auto-scroll to current word
  useEffect(() => {
    if (!autoScroll || !currentWordId || !containerRef.current) return;
    
    const currentWordElement = containerRef.current.querySelector(`[data-word-id="${currentWordId}"]`);
    if (currentWordElement) {
      currentWordElement.scrollIntoView({
        behavior: 'smooth',
        block: 'center',
      });
    }
  }, [currentWordId, autoScroll]);
  
  // Handle word click
  const handleWordClick = useCallback((word: WordToken, event: React.MouseEvent) => {
    if (event.shiftKey) {
      // Multi-select
      setSelectedWords(prev => {
        const newSet = new Set(prev);
        if (newSet.has(word.id)) {
          newSet.delete(word.id);
        } else {
          newSet.add(word.id);
        }
        return newSet;
      });
    } else if (event.ctrlKey || event.metaKey) {
      // Toggle selection
      setSelectedWords(prev => {
        const newSet = new Set(prev);
        if (newSet.has(word.id)) {
          newSet.delete(word.id);
        } else {
          newSet.add(word.id);
        }
        return newSet;
      });
    } else {
      // Seek to word time
      onSeek?.(word.startTime);
      setSelectedWords(new Set([word.id]));
    }
  }, [onSeek]);
  
  // Handle word double-click for editing
  const handleWordDoubleClick = useCallback((word: WordToken) => {
    setEditingWordId(word.id);
    setEditText(word.text);
    setTimeout(() => editInputRef.current?.focus(), 0);
  }, []);
  
  // Handle edit save
  const handleEditSave = useCallback(() => {
    if (editingWordId && editText.trim()) {
      onWordEdit?.(editingWordId, editText.trim());
    }
    setEditingWordId(null);
    setEditText('');
  }, [editingWordId, editText, onWordEdit]);
  
  // Handle edit cancel
  const handleEditCancel = useCallback(() => {
    setEditingWordId(null);
    setEditText('');
  }, []);
  
  // Handle delete selected words
  const handleDeleteSelected = useCallback(() => {
    selectedWords.forEach(wordId => {
      onWordDelete?.(wordId);
    });
    setSelectedWords(new Set());
  }, [selectedWords, onWordDelete]);
  
  // Get word styling
  const getWordStyling = useCallback((word: WordToken) => {
    const classes = ['word-token'];
    
    // Current word highlight
    if (word.id === currentWordId) {
      classes.push('bg-editor-accent', 'text-white');
    } else if (selectedWords.has(word.id)) {
      classes.push('bg-editor-accent/30', 'text-editor-text-primary');
    } else {
      classes.push('text-editor-text-primary', 'hover:bg-editor-border');
    }
    
    // Confidence styling
    if (highlightLowConfidence && word.confidence < 0.7) {
      classes.push('border-b-2', 'border-editor-warning');
    }
    
    // Filler word styling
    if (word.isFillerWord) {
      classes.push('text-editor-text-muted', 'italic');
    }
    
    // Edited word styling
    if (word.isEdited) {
      classes.push('border-b', 'border-editor-success');
    }
    
    return classes.join(' ');
  }, [currentWordId, selectedWords, highlightLowConfidence]);
  
  // Format time for display
  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = (seconds % 60).toFixed(1);
    return `${mins}:${secs.padStart(4, '0')}`;
  };
  
  if (!isVisible) return null;
  
  return (
    <div className={`word-level-editor bg-editor-surface border border-editor-border rounded-lg ${className}`}>
      {/* Header */}
      <div className="p-4 border-b border-editor-border">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-medium text-editor-text-primary">Word-Level Editor</h3>
          
          <div className="flex items-center gap-2">
            {/* Search */}
            <input
              type="text"
              placeholder="Search words..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="form-input text-sm w-32"
            />
            
            {/* Settings */}
            <div className="flex items-center gap-1">
              <button
                onClick={() => setShowFillerWords(!showFillerWords)}
                className={`
                  px-2 py-1 text-xs rounded transition-colors
                  ${showFillerWords 
                    ? 'bg-editor-accent text-white' 
                    : 'bg-editor-border text-editor-text-secondary'
                  }
                `}
                title="Show filler words"
              >
                Fillers
              </button>
              
              <button
                onClick={() => setHighlightLowConfidence(!highlightLowConfidence)}
                className={`
                  px-2 py-1 text-xs rounded transition-colors
                  ${highlightLowConfidence 
                    ? 'bg-editor-warning text-white' 
                    : 'bg-editor-border text-editor-text-secondary'
                  }
                `}
                title="Highlight low confidence words"
              >
                Low Conf
              </button>
              
              <button
                onClick={() => setAutoScroll(!autoScroll)}
                className={`
                  px-2 py-1 text-xs rounded transition-colors
                  ${autoScroll 
                    ? 'bg-editor-success text-white' 
                    : 'bg-editor-border text-editor-text-secondary'
                  }
                `}
                title="Auto-scroll to current word"
              >
                Auto-scroll
              </button>
            </div>
          </div>
        </div>
        
        {/* Actions */}
        {selectedWords.size > 0 && (
          <div className="flex items-center gap-2">
            <span className="text-sm text-editor-text-secondary">
              {selectedWords.size} words selected
            </span>
            
            <button
              onClick={handleDeleteSelected}
              className="px-3 py-1 bg-editor-error text-white text-sm rounded hover:bg-opacity-80 transition-colors"
            >
              Delete Selected
            </button>
            
            <button
              onClick={() => setSelectedWords(new Set())}
              className="px-3 py-1 bg-editor-border text-editor-text-primary text-sm rounded hover:bg-opacity-80 transition-colors"
            >
              Clear Selection
            </button>
          </div>
        )}
      </div>
      
      {/* Transcript content */}
      <div 
        ref={containerRef}
        className="p-4 max-h-96 overflow-y-auto space-y-4"
      >
        {filteredTranscript.map((segment) => (
          <div key={segment.id} className="transcript-segment">
            {/* Segment header */}
            <div className="flex items-center gap-2 mb-2 text-sm text-editor-text-secondary">
              <span>{formatTime(segment.startTime)} - {formatTime(segment.endTime)}</span>
              {segment.speaker && (
                <span className="bg-editor-border px-2 py-0.5 rounded text-xs">
                  {segment.speaker}
                </span>
              )}
            </div>
            
            {/* Words */}
            <div className="flex flex-wrap gap-1 leading-relaxed">
              {segment.words.map((word) => (
                <span key={word.id}>
                  {editingWordId === word.id ? (
                    <input
                      ref={editInputRef}
                      type="text"
                      value={editText}
                      onChange={(e) => setEditText(e.target.value)}
                      onBlur={handleEditSave}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') handleEditSave();
                        if (e.key === 'Escape') handleEditCancel();
                      }}
                      className="word-edit-input bg-editor-background border border-editor-accent rounded px-1"
                      style={{ width: `${Math.max(editText.length, 4)}ch` }}
                    />
                  ) : (
                    <span
                      data-word-id={word.id}
                      className={`
                        ${getWordStyling(word)}
                        cursor-pointer px-1 py-0.5 rounded transition-colors
                        select-none
                      `}
                      onClick={(e) => handleWordClick(word, e)}
                      onDoubleClick={() => handleWordDoubleClick(word)}
                      title={`${word.text} (${(word.confidence * 100).toFixed(0)}% confidence)`}
                    >
                      {word.text}
                    </span>
                  )}
                  {/* Add space after word unless it's punctuation */}
                  {!/[.,!?;:]$/.test(word.text) && ' '}
                </span>
              ))}
            </div>
          </div>
        ))}
        
        {filteredTranscript.length === 0 && (
          <div className="text-center py-8 text-editor-text-secondary">
            {searchTerm ? 'No words match your search' : 'No transcript available'}
          </div>
        )}
      </div>
      
      {/* Footer */}
      <div className="p-4 border-t border-editor-border">
        <div className="flex items-center justify-between text-sm text-editor-text-secondary">
          <div>
            Click to seek, double-click to edit, Shift+click to select multiple
          </div>
          
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-1">
              <div className="w-3 h-3 bg-editor-accent rounded" />
              <span>Current</span>
            </div>
            
            <div className="flex items-center gap-1">
              <div className="w-3 h-1 bg-editor-warning" />
              <span>Low confidence</span>
            </div>
            
            <div className="flex items-center gap-1">
              <div className="w-3 h-1 bg-editor-success" />
              <span>Edited</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

// Word confidence indicator component
export const WordConfidenceIndicator: React.FC<{
  confidence: number;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}> = ({ confidence, size = 'sm', className = '' }) => {
  const getColor = () => {
    if (confidence >= 0.8) return 'bg-editor-success';
    if (confidence >= 0.6) return 'bg-editor-warning';
    return 'bg-editor-error';
  };
  
  const getSize = () => {
    switch (size) {
      case 'sm': return 'w-2 h-2';
      case 'md': return 'w-3 h-3';
      case 'lg': return 'w-4 h-4';
      default: return 'w-2 h-2';
    }
  };
  
  return (
    <div
      className={`${getColor()} ${getSize()} rounded-full ${className}`}
      title={`Confidence: ${(confidence * 100).toFixed(0)}%`}
    />
  );
};

// Transcript statistics component
export const TranscriptStats: React.FC<{
  transcript: TranscriptSegment[];
  className?: string;
}> = ({ transcript, className = '' }) => {
  const stats = useMemo(() => {
    const allWords = transcript.flatMap(s => s.words);
    const totalWords = allWords.length;
    const fillerWords = allWords.filter(w => w.isFillerWord).length;
    const editedWords = allWords.filter(w => w.isEdited).length;
    const lowConfidenceWords = allWords.filter(w => w.confidence < 0.7).length;
    const avgConfidence = allWords.reduce((sum, w) => sum + w.confidence, 0) / totalWords || 0;
    const totalDuration = Math.max(...transcript.map(s => s.endTime)) - Math.min(...transcript.map(s => s.startTime));
    
    return {
      totalWords,
      fillerWords,
      editedWords,
      lowConfidenceWords,
      avgConfidence,
      totalDuration,
    };
  }, [transcript]);
  
  return (
    <div className={`transcript-stats bg-editor-surface border border-editor-border rounded-lg p-3 ${className}`}>
      <h4 className="text-sm font-medium text-editor-text-primary mb-2">Transcript Statistics</h4>
      
      <div className="grid grid-cols-2 gap-2 text-sm">
        <div>
          <span className="text-editor-text-secondary">Total Words:</span>
          <span className="ml-2 text-editor-text-primary">{stats.totalWords}</span>
        </div>
        
        <div>
          <span className="text-editor-text-secondary">Duration:</span>
          <span className="ml-2 text-editor-text-primary">{Math.round(stats.totalDuration)}s</span>
        </div>
        
        <div>
          <span className="text-editor-text-secondary">Filler Words:</span>
          <span className="ml-2 text-editor-warning">{stats.fillerWords}</span>
        </div>
        
        <div>
          <span className="text-editor-text-secondary">Edited:</span>
          <span className="ml-2 text-editor-success">{stats.editedWords}</span>
        </div>
        
        <div>
          <span className="text-editor-text-secondary">Low Confidence:</span>
          <span className="ml-2 text-editor-error">{stats.lowConfidenceWords}</span>
        </div>
        
        <div>
          <span className="text-editor-text-secondary">Avg Confidence:</span>
          <span className="ml-2 text-editor-text-primary">{(stats.avgConfidence * 100).toFixed(0)}%</span>
        </div>
      </div>
    </div>
  );
};