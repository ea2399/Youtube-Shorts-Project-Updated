/**
 * Export Dialog - Phase 4C
 * Platform-specific export interface with presets and customization
 */

'use client';

import React, { useState, useEffect } from 'react';
import { 
  ExportPreset, 
  ExportSettings, 
  ExportManager, 
  ExportProgress,
  EXPORT_PRESETS,
  validateExportSettings,
  estimateExportTime,
  formatExportDuration
} from '@/lib/export';

interface ExportDialogProps {
  isOpen: boolean;
  onClose: () => void;
  edlId: string;
  duration: number; // Duration in seconds
  onExportStart?: (jobId: string) => void;
}

export const ExportDialog: React.FC<ExportDialogProps> = ({
  isOpen,
  onClose,
  edlId,
  duration,
  onExportStart,
}) => {
  const [selectedPreset, setSelectedPreset] = useState<ExportPreset>(EXPORT_PRESETS[0]);
  const [customSettings, setCustomSettings] = useState<ExportSettings>(selectedPreset.settings);
  const [isCustomMode, setIsCustomMode] = useState(false);
  const [validationErrors, setValidationErrors] = useState<string[]>([]);
  const [isExporting, setIsExporting] = useState(false);
  const [exportProgress, setExportProgress] = useState<ExportProgress | null>(null);
  const [exportManager] = useState(() => new ExportManager());

  // Update custom settings when preset changes
  useEffect(() => {
    if (!isCustomMode) {
      setCustomSettings({ ...selectedPreset.settings });
    }
  }, [selectedPreset, isCustomMode]);

  // Validate settings on change
  useEffect(() => {
    const errors = validateExportSettings(customSettings);
    setValidationErrors(errors);
  }, [customSettings]);

  const handlePresetSelect = (preset: ExportPreset) => {
    setSelectedPreset(preset);
    setIsCustomMode(false);
  };

  const handleCustomToggle = () => {
    setIsCustomMode(!isCustomMode);
    if (!isCustomMode) {
      setCustomSettings({ ...selectedPreset.settings });
    }
  };

  const handleSettingChange = <K extends keyof ExportSettings>(
    key: K,
    value: ExportSettings[K]
  ) => {
    setCustomSettings(prev => ({ ...prev, [key]: value }));
  };

  const handleExport = async () => {
    if (validationErrors.length > 0) return;

    try {
      setIsExporting(true);
      
      const exportPreset: ExportPreset = {
        ...selectedPreset,
        settings: customSettings,
      };

      const jobId = await exportManager.startExport(
        edlId,
        exportPreset,
        (progress) => {
          setExportProgress(progress);
        }
      );

      onExportStart?.(jobId);

      // Keep dialog open to show progress
      // User can close manually or we can auto-close on completion

    } catch (error) {
      console.error('Export failed:', error);
      setIsExporting(false);
    }
  };

  const handleClose = () => {
    if (!isExporting) {
      onClose();
      setExportProgress(null);
    }
  };

  const estimatedTime = estimateExportTime(duration, customSettings);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-editor-surface border border-editor-border rounded-lg w-full max-w-4xl max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-editor-border">
          <h2 className="text-xl font-semibold text-editor-text-primary">
            Export Video
          </h2>
          <button
            onClick={handleClose}
            disabled={isExporting}
            className="text-editor-text-secondary hover:text-editor-text-primary transition-colors disabled:opacity-50"
          >
            <svg className="w-6 h-6" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
            </svg>
          </button>
        </div>

        <div className="flex h-[70vh]">
          {/* Preset Selection */}
          <div className="w-1/3 border-r border-editor-border p-6 overflow-y-auto">
            <h3 className="text-lg font-medium text-editor-text-primary mb-4">
              Export Presets
            </h3>
            
            <div className="space-y-3">
              {EXPORT_PRESETS.map((preset) => (
                <button
                  key={preset.id}
                  onClick={() => handlePresetSelect(preset)}
                  disabled={isExporting}
                  className={`w-full text-left p-4 rounded-lg border transition-colors disabled:opacity-50 ${
                    selectedPreset.id === preset.id
                      ? 'border-blue-500 bg-blue-500/10'
                      : 'border-editor-border hover:border-editor-border-hover'
                  }`}
                >
                  <div className="flex items-center gap-3 mb-2">
                    <span className="text-2xl">{preset.icon}</span>
                    <span className="font-medium text-editor-text-primary">
                      {preset.name}
                    </span>
                  </div>
                  <p className="text-sm text-editor-text-secondary">
                    {preset.description}
                  </p>
                  <div className="flex items-center gap-4 mt-2 text-xs text-editor-text-muted">
                    <span>{preset.settings.resolution}</span>
                    <span>{preset.settings.aspectRatio}</span>
                    <span>{preset.settings.format.toUpperCase()}</span>
                  </div>
                </button>
              ))}
            </div>

            {/* Custom Settings Toggle */}
            <div className="mt-6 pt-6 border-t border-editor-border">
              <label className="flex items-center gap-3">
                <input
                  type="checkbox"
                  checked={isCustomMode}
                  onChange={handleCustomToggle}
                  disabled={isExporting}
                  className="rounded border-editor-border"
                />
                <span className="text-sm text-editor-text-primary">
                  Custom Settings
                </span>
              </label>
            </div>
          </div>

          {/* Settings Panel */}
          <div className="flex-1 p-6 overflow-y-auto">
            <h3 className="text-lg font-medium text-editor-text-primary mb-4">
              Export Settings
            </h3>

            {/* Export Progress */}
            {isExporting && exportProgress && (
              <div className="mb-6 p-4 bg-blue-500/10 border border-blue-500/20 rounded-lg">
                <div className="flex items-center justify-between mb-2">
                  <span className="font-medium text-editor-text-primary">
                    {exportProgress.message}
                  </span>
                  <span className="text-sm text-editor-text-secondary">
                    {Math.round(exportProgress.percentage)}%
                  </span>
                </div>
                <div className="w-full bg-editor-border rounded-full h-2">
                  <div
                    className="bg-blue-500 h-2 rounded-full transition-all duration-300"
                    style={{ width: `${exportProgress.percentage}%` }}
                  />
                </div>
                {exportProgress.timeRemaining && (
                  <div className="text-xs text-editor-text-muted mt-2">
                    Estimated time remaining: {formatExportDuration(exportProgress.timeRemaining)}
                  </div>
                )}
              </div>
            )}

            <div className="grid grid-cols-2 gap-6">
              {/* Basic Settings */}
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-editor-text-primary mb-2">
                    Format
                  </label>
                  <select
                    value={customSettings.format}
                    onChange={(e) => handleSettingChange('format', e.target.value as any)}
                    disabled={!isCustomMode || isExporting}
                    className="w-full px-3 py-2 bg-editor-background border border-editor-border rounded-md text-editor-text-primary disabled:opacity-50"
                  >
                    <option value="mp4">MP4</option>
                    <option value="webm">WebM</option>
                    <option value="mov">MOV</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-editor-text-primary mb-2">
                    Resolution
                  </label>
                  <select
                    value={customSettings.resolution}
                    onChange={(e) => handleSettingChange('resolution', e.target.value as any)}
                    disabled={!isCustomMode || isExporting}
                    className="w-full px-3 py-2 bg-editor-background border border-editor-border rounded-md text-editor-text-primary disabled:opacity-50"
                  >
                    <option value="720p">720p (HD)</option>
                    <option value="1080p">1080p (Full HD)</option>
                    <option value="4K">4K (Ultra HD)</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-editor-text-primary mb-2">
                    Aspect Ratio
                  </label>
                  <select
                    value={customSettings.aspectRatio}
                    onChange={(e) => handleSettingChange('aspectRatio', e.target.value as any)}
                    disabled={!isCustomMode || isExporting}
                    className="w-full px-3 py-2 bg-editor-background border border-editor-border rounded-md text-editor-text-primary disabled:opacity-50"
                  >
                    <option value="16:9">16:9 (Widescreen)</option>
                    <option value="9:16">9:16 (Vertical)</option>
                    <option value="1:1">1:1 (Square)</option>
                    <option value="4:5">4:5 (Portrait)</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-editor-text-primary mb-2">
                    Quality
                  </label>
                  <select
                    value={customSettings.quality}
                    onChange={(e) => handleSettingChange('quality', e.target.value as any)}
                    disabled={!isCustomMode || isExporting}
                    className="w-full px-3 py-2 bg-editor-background border border-editor-border rounded-md text-editor-text-primary disabled:opacity-50"
                  >
                    <option value="low">Low (Fastest)</option>
                    <option value="medium">Medium (Balanced)</option>
                    <option value="high">High (Best Quality)</option>
                  </select>
                </div>
              </div>

              {/* Advanced Settings */}
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-editor-text-primary mb-2">
                    Video Bitrate (kbps)
                  </label>
                  <input
                    type="number"
                    value={customSettings.videoBitrate}
                    onChange={(e) => handleSettingChange('videoBitrate', parseInt(e.target.value))}
                    disabled={!isCustomMode || isExporting}
                    min="1000"
                    max="50000"
                    className="w-full px-3 py-2 bg-editor-background border border-editor-border rounded-md text-editor-text-primary disabled:opacity-50"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-editor-text-primary mb-2">
                    Audio Bitrate (kbps)
                  </label>
                  <input
                    type="number"
                    value={customSettings.audioBitrate}
                    onChange={(e) => handleSettingChange('audioBitrate', parseInt(e.target.value))}
                    disabled={!isCustomMode || isExporting}
                    min="64"
                    max="320"
                    className="w-full px-3 py-2 bg-editor-background border border-editor-border rounded-md text-editor-text-primary disabled:opacity-50"
                  />
                </div>

                <div>
                  <label className="flex items-center gap-3">
                    <input
                      type="checkbox"
                      checked={customSettings.includeSubtitles}
                      onChange={(e) => handleSettingChange('includeSubtitles', e.target.checked)}
                      disabled={!isCustomMode || isExporting}
                      className="rounded border-editor-border"
                    />
                    <span className="text-sm text-editor-text-primary">
                      Include Subtitles
                    </span>
                  </label>
                </div>

                {/* Export Info */}
                <div className="mt-6 p-4 bg-editor-background rounded-lg">
                  <h4 className="font-medium text-editor-text-primary mb-2">
                    Export Information
                  </h4>
                  <div className="space-y-1 text-sm text-editor-text-secondary">
                    <div>Duration: {formatExportDuration(duration)}</div>
                    <div>Estimated time: {formatExportDuration(estimatedTime)}</div>
                    <div>Output format: {customSettings.format.toUpperCase()}</div>
                  </div>
                </div>
              </div>
            </div>

            {/* Validation Errors */}
            {validationErrors.length > 0 && (
              <div className="mt-6 p-4 bg-red-500/10 border border-red-500/20 rounded-lg">
                <h4 className="font-medium text-red-400 mb-2">
                  Validation Errors
                </h4>
                <ul className="space-y-1 text-sm text-red-300">
                  {validationErrors.map((error, index) => (
                    <li key={index}>• {error}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between p-6 border-t border-editor-border">
          <div className="text-sm text-editor-text-secondary">
            {isCustomMode ? 'Custom Settings' : `Using ${selectedPreset.name} preset`}
          </div>
          
          <div className="flex items-center gap-3">
            <button
              onClick={handleClose}
              disabled={isExporting}
              className="px-4 py-2 text-editor-text-secondary hover:text-editor-text-primary transition-colors disabled:opacity-50"
            >
              {isExporting ? 'Exporting...' : 'Cancel'}
            </button>
            <button
              onClick={handleExport}
              disabled={isExporting || validationErrors.length > 0}
              className="px-6 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-md transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isExporting ? 'Exporting...' : 'Start Export'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};