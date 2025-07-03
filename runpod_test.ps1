# YouTube Shorts Generator - RunPod Testing Script
# Usage: .\runpod_test.ps1 -EndpointId "your-endpoint-id" -ConfigFile "payloads\torah_lecture_basic.json"

param(
    [Parameter(Mandatory=$true)]
    [string]$EndpointId,
    
    [Parameter(Mandatory=$false)]
    [string]$ConfigFile = "payloads\torah_lecture_basic.json",
    
    [Parameter(Mandatory=$false)]
    [string]$ApiKey = $env:RUNPOD_API_KEY,
    
    [Parameter(Mandatory=$false)]
    [switch]$Async = $false,
    
    [Parameter(Mandatory=$false)]
    [int]$TimeoutSeconds = 600
)

# Check if API key is provided
if (-not $ApiKey) {
    Write-Error "RunPod API key not found. Set RUNPOD_API_KEY environment variable or provide -ApiKey parameter."
    exit 1
}

# Check if config file exists
if (-not (Test-Path $ConfigFile)) {
    Write-Error "Configuration file not found: $ConfigFile"
    exit 1
}

# Load configuration
try {
    $config = Get-Content $ConfigFile | ConvertFrom-Json
    Write-Host "✓ Loaded configuration from: $ConfigFile" -ForegroundColor Green
    Write-Host "  Video URL: $($config.input.video_url)" -ForegroundColor Cyan
    Write-Host "  Language: $($config.input.language)" -ForegroundColor Cyan
    Write-Host "  Clips: $($config.input.num_clips)" -ForegroundColor Cyan
    Write-Host "  Model: $($config.input.model_size)" -ForegroundColor Cyan
}
catch {
    Write-Error "Failed to parse configuration file: $_"
    exit 1
}

# Prepare request
$url = "https://api.runpod.ai/v2/$EndpointId/run"
if ($Async) {
    $url += "Async"
}

$headers = @{
    "Authorization" = "Bearer $ApiKey"
    "Content-Type" = "application/json"
}

$body = $config | ConvertTo-Json -Depth 10

Write-Host "`n🚀 Sending request to RunPod..." -ForegroundColor Yellow
Write-Host "Endpoint: $EndpointId" -ForegroundColor Cyan
Write-Host "URL: $url" -ForegroundColor Cyan
Write-Host "Async: $Async" -ForegroundColor Cyan

try {
    $stopwatch = [System.Diagnostics.Stopwatch]::StartNew()
    
    if ($Async) {
        # Async request
        $response = Invoke-RestMethod -Uri $url -Method POST -Headers $headers -Body $body
        $jobId = $response.id
        
        Write-Host "✓ Job submitted successfully!" -ForegroundColor Green
        Write-Host "Job ID: $jobId" -ForegroundColor Cyan
        
        # Poll for results
        $statusUrl = "https://api.runpod.ai/v2/$EndpointId/status/$jobId"
        
        Write-Host "`n⏳ Polling for results..." -ForegroundColor Yellow
        
        do {
            Start-Sleep -Seconds 5
            $statusResponse = Invoke-RestMethod -Uri $statusUrl -Method GET -Headers $headers
            $status = $statusResponse.status
            
            Write-Host "Status: $status" -ForegroundColor Cyan
            
            if ($stopwatch.Elapsed.TotalSeconds -gt $TimeoutSeconds) {
                Write-Warning "Timeout reached after $TimeoutSeconds seconds"
                break
            }
        } while ($status -eq "IN_PROGRESS" -or $status -eq "IN_QUEUE")
        
        $response = $statusResponse
    }
    else {
        # Synchronous request
        $response = Invoke-RestMethod -Uri $url -Method POST -Headers $headers -Body $body -TimeoutSec $TimeoutSeconds
    }
    
    $stopwatch.Stop()
    $elapsed = $stopwatch.Elapsed
    
    Write-Host "`n✅ Request completed!" -ForegroundColor Green
    Write-Host "Processing time: $($elapsed.ToString('mm\:ss'))" -ForegroundColor Cyan
    
    # Display results
    if ($response.output) {
        $output = $response.output
        Write-Host "`n📊 Results Summary:" -ForegroundColor Yellow
        Write-Host "Clips generated: $($output.clips_generated)" -ForegroundColor Green
        Write-Host "Transcription segments: $($output.transcription.segments)" -ForegroundColor Green
        Write-Host "Language detected: $($output.transcription.language)" -ForegroundColor Green
        Write-Host "Analysis method: $($output.analysis.method)" -ForegroundColor Green
        Write-Host "Main themes: $($output.analysis.themes -join ', ')" -ForegroundColor Green
        
        Write-Host "`n🎬 Generated Clips:" -ForegroundColor Yellow
        foreach ($clip in $output.clips) {
            Write-Host "  $($clip.index). $($clip.title)" -ForegroundColor Cyan
            Write-Host "     Duration: $($clip.duration)s | Score: $($clip.score)" -ForegroundColor Gray
            Write-Host "     Context: $($clip.context_dependency)" -ForegroundColor Gray
            if ($clip.files.horizontal) {
                Write-Host "     Horizontal: $($clip.files.horizontal)" -ForegroundColor Gray
            }
            if ($clip.files.vertical) {
                Write-Host "     Vertical: $($clip.files.vertical)" -ForegroundColor Gray
            }
            if ($clip.files.subtitle) {
                Write-Host "     Subtitle: $($clip.files.subtitle)" -ForegroundColor Gray
            }
        }
    }
    elseif ($response.error) {
        Write-Error "RunPod returned error: $($response.error)"
        if ($response.traceback) {
            Write-Host "`nTraceback:" -ForegroundColor Red
            Write-Host $response.traceback -ForegroundColor Red
        }
    }
    else {
        Write-Warning "Unexpected response format"
    }
    
    # Save full response
    $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $outputFile = "runpod_response_$timestamp.json"
    $response | ConvertTo-Json -Depth 10 | Out-File $outputFile
    Write-Host "`n💾 Full response saved to: $outputFile" -ForegroundColor Yellow
}
catch {
    Write-Error "Request failed: $_"
    if ($_.Exception.Response) {
        $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
        $responseBody = $reader.ReadToEnd()
        Write-Host "Response body: $responseBody" -ForegroundColor Red
    }
    exit 1
}

Write-Host "`n🎉 Test completed!" -ForegroundColor Green