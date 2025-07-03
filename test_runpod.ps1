#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Test YouTube Shorts Generator RunPod endpoint
.DESCRIPTION
    PowerShell script to test the deployed YouTube Shorts Generator on RunPod.
    Follows the same pattern as your WhisperX testing script.
.EXAMPLE
    .\test_runpod.ps1 -EndpointId "your_endpoint_id" -ConfigFile "payloads\torah_lecture_basic.json"
.EXAMPLE
    .\test_runpod.ps1 -EndpointId "your_endpoint_id" -VideoUrl "https://example.com/video.mp4" -Clips 3
#>

param(
    [Parameter(Mandatory=$true)]
    [string]$EndpointId,
    
    [Parameter(ParameterSetName="ConfigFile")]
    [string]$ConfigFile = "payloads\torah_lecture_basic.json",
    
    [Parameter(ParameterSetName="Direct")]
    [string]$VideoUrl,
    
    [Parameter(ParameterSetName="Direct")]
    [int]$Clips = 3,
    
    [Parameter(ParameterSetName="Direct")]
    [string]$Language = "he",
    
    [Parameter(ParameterSetName="Direct")]
    [string]$ModelSize = "small",
    
    [Parameter(ParameterSetName="Direct")]
    [int]$MinDuration = 20,
    
    [Parameter(ParameterSetName="Direct")]
    [int]$MaxDuration = 60,
    
    [Parameter(ParameterSetName="Direct")]
    [bool]$Vertical = $true,
    
    [Parameter(ParameterSetName="Direct")]
    [bool]$Subtitles = $true,
    
    [string]$ApiKey = $env:RUNPOD_API_KEY,
    
    [switch]$Async = $false,
    
    [int]$TimeoutMinutes = 15
)

# Colors for output
function Write-Success { param($Message) Write-Host "✅ $Message" -ForegroundColor Green }
function Write-Info { param($Message) Write-Host "ℹ️  $Message" -ForegroundColor Cyan }
function Write-Warning { param($Message) Write-Host "⚠️  $Message" -ForegroundColor Yellow }
function Write-Error { param($Message) Write-Host "❌ $Message" -ForegroundColor Red }

# Validate inputs
if (-not $ApiKey) {
    Write-Error "RunPod API key not found. Set RUNPOD_API_KEY environment variable or pass -ApiKey parameter."
    Write-Info "Set with: `$env:RUNPOD_API_KEY = 'your_api_key_here'"
    exit 1
}

# Prepare payload
$payload = $null

if ($PSCmdlet.ParameterSetName -eq "ConfigFile") {
    if (-not (Test-Path $ConfigFile)) {
        Write-Error "Config file not found: $ConfigFile"
        exit 1
    }
    Write-Info "Loading configuration from: $ConfigFile"
    $payload = Get-Content -Raw $ConfigFile | ConvertFrom-Json
} else {
    if (-not $VideoUrl) {
        Write-Error "VideoUrl is required when not using a config file"
        exit 1
    }
    Write-Info "Creating configuration from parameters"
    $payload = @{
        input = @{
            video_url = $VideoUrl
            language = $Language
            num_clips = $Clips
            min_duration = $MinDuration
            max_duration = $MaxDuration
            vertical = $Vertical
            subtitles = $Subtitles
            model_size = $ModelSize
        }
    }
}

Write-Info "🚀 YouTube Shorts Generator - RunPod Test"
Write-Host "=" * 50
Write-Info "Endpoint ID: $EndpointId"
Write-Info "Video URL: $($payload.input.video_url)"
Write-Info "Language: $($payload.input.language)"
Write-Info "Clips requested: $($payload.input.num_clips)"
Write-Info "Model size: $($payload.input.model_size)"
Write-Info "Async mode: $Async"
Write-Host ""

# 1️⃣ Run the job --> capture the ID
Write-Info "🎬 Submitting job to RunPod..."

try {
    $endpoint = if ($Async) { "runAsync" } else { "run" }
    $uri = "https://api.runpod.ai/v2/$EndpointId/$endpoint"
    
    $headers = @{
        Authorization = "Bearer $ApiKey"
        "Content-Type" = "application/json"
    }
    
    $body = $payload | ConvertTo-Json -Depth 10
    
    $response = Invoke-RestMethod -Method Post -Uri $uri -Headers $headers -Body $body
    
    if ($Async) {
        $jobId = $response.id
        Write-Success "Queued job ID: $jobId"
    } else {
        # Synchronous response
        Write-Success "Job completed synchronously!"
        $response.output | ConvertTo-Json -Depth 10 | Out-File -FilePath "shorts_result.json" -Encoding utf8
        Write-Success "Results written to shorts_result.json"
        
        # Display summary
        if ($response.output.clips_generated) {
            Write-Success "🎬 Generated $($response.output.clips_generated) clips!"
            foreach ($clip in $response.output.clips) {
                Write-Info "   $($clip.index). $($clip.title) ($($clip.duration)s) - Score: $($clip.score)/10"
            }
        }
        exit 0
    }
} catch {
    Write-Error "Failed to submit job: $($_.Exception.Message)"
    if ($_.Exception.Response) {
        $errorBody = $_.Exception.Response.GetResponseStream()
        $reader = [System.IO.StreamReader]::new($errorBody)
        $errorText = $reader.ReadToEnd()
        Write-Error "Response: $errorText"
    }
    exit 1
}

# 2️⃣ Poll until finished (for async jobs only)
if ($Async) {
    Write-Info "⏳ Polling for completion..."
    $timeoutTime = (Get-Date).AddMinutes($TimeoutMinutes)
    
    do {
        try {
            $job = Invoke-RestMethod `
                -Uri "https://api.runpod.ai/v2/$EndpointId/status/$jobId" `
                -Headers @{ Authorization = "Bearer $ApiKey" }

            $timestamp = Get-Date -Format "HH:mm:ss"
            Write-Host "$timestamp Status: $($job.status)" -ForegroundColor Cyan
            
            if ($job.status -eq "FAILED") {
                Write-Error "Job failed!"
                if ($job.error) {
                    Write-Error "Error: $($job.error)"
                }
                exit 1
            }
            
            if ($job.status -notin @("COMPLETED", "FAILED")) {
                if ((Get-Date) -gt $timeoutTime) {
                    Write-Error "Job timed out after $TimeoutMinutes minutes"
                    exit 1
                }
                Start-Sleep 10
            }
        } catch {
            Write-Error "Failed to check job status: $($_.Exception.Message)"
            exit 1
        }
    } until ($job.status -eq "COMPLETED")

    # 3️⃣ Save the results
    Write-Success "Job completed! Processing results..."
    
    try {
        $job.output | ConvertTo-Json -Depth 10 | Out-File -FilePath "shorts_result.json" -Encoding utf8
        Write-Success "Results written to shorts_result.json"
        
        # Display summary
        if ($job.output.clips_generated) {
            Write-Host ""
            Write-Success "🎬 Generated $($job.output.clips_generated) clips!"
            Write-Host "📊 Analysis Method: $($job.output.analysis.method)"
            Write-Host "🌐 Language: $($job.output.transcription.language)"
            Write-Host "📝 Segments: $($job.output.transcription.segments)"
            
            if ($job.output.analysis.themes) {
                Write-Host "🏷️  Themes: $($job.output.analysis.themes -join ', ')"
            }
            
            Write-Host ""
            Write-Info "Generated Clips:"
            foreach ($clip in $job.output.clips) {
                $deps = if ($clip.context_dependency) { "($($clip.context_dependency) dependency)" } else { "" }
                Write-Host "   $($clip.index). $($clip.title) $deps" -ForegroundColor White
                Write-Host "      Duration: $($clip.duration)s | Score: $($clip.score)/10" -ForegroundColor Gray
                if ($clip.files.horizontal) { Write-Host "      📹 Horizontal: $($clip.files.horizontal)" -ForegroundColor Gray }
                if ($clip.files.vertical) { Write-Host "      📱 Vertical: $($clip.files.vertical)" -ForegroundColor Gray }
                if ($clip.files.subtitle) { Write-Host "      📝 Subtitles: $($clip.files.subtitle)" -ForegroundColor Gray }
            }
        }
        
        if ($job.output.processing_info) {
            Write-Host ""
            Write-Info "Processing Info:"
            Write-Host "   Model: $($job.output.processing_info.model_size)"
            Write-Host "   Vertical created: $($job.output.processing_info.vertical_created)"
            Write-Host "   Subtitles created: $($job.output.processing_info.subtitles_created)"
        }
        
    } catch {
        Write-Error "Failed to save results: $($_.Exception.Message)"
        # Still show raw output
        Write-Info "Raw output:"
        $job.output | ConvertTo-Json -Depth 5
    }
}

Write-Success "🎉 Test completed successfully!"