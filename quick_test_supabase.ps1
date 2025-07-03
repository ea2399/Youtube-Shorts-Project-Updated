# Quick test script with Supabase URLs - YouTube Shorts Generator
# This version fetches both video and transcript JSON from Supabase

# Set your RunPod credentials
$env:RUNPOD_API_KEY = ""your_runpod_api_key""  # Replace with your actual API key
$env:ENDPOINT_ID    = "i3fvz5sqdc0e7p"   # Replace with your actual endpoint ID

# Supabase URLs (update these with your actual URLs)
$VIDEO_URL = "https://tiynbxfoapakpwpgbhyj.supabase.co/storage/v1/object/sign/media-assets/videos/1751026646251-125r3d.mp4?token=eyJraWQiOiJzdG9yYWdlLXVybC1zaWduaW5nLWtleV8zNmZlZDk5Ny02MzhiLTQ0NTUtYTE2NC1jNDllOTAzYWQwNDIiLCJhbGciOiJIUzI1NiJ9.eyJ1cmwiOiJtZWRpYS1hc3NldHMvdmlkZW9zLzE3NTEwMjY2NDYyNTEtMTI1cjNkLm1wNCIsImlhdCI6MTc1MTAyNjgzMiwiZXhwIjoxNzUxNjMxNjMyfQ.2cqfL8QwnpxMiagB5TndsiCw_d8jyeu5aREkyqN4D0s"
$TRANSCRIPT_JSON_URL = "https://tiynbxfoapakpwpgbhyj.supabase.co/storage/v1/object/sign/media-assets/transcripts/1751026646251-125r3d/1751026646251-125r3d.json?token=eyJraWQiOiJzdG9yYWdlLXVybC1zaWduaW5nLWtleV8zNmZlZDk5Ny02MzhiLTQ0NTUtYTE2NC1jNDllOTAzYWQwNDIiLCJhbGciOiJIUzI1NiJ9.eyJ1cmwiOiJtZWRpYS1hc3NldHMvdHJhbnNjcmlwdHMvMTc1MTAyNjY0NjI1MS0xMjVyM2QvMTc1MTAyNjY0NjI1MS0xMjVyM2QuanNvbiIsImlhdCI6MTc1MTAyNjg3NSwiZXhwIjoxNzUxNjMxNjc1fQ.oVJFQMU1i3GD6YG13oAeVciowSfsZVDuxVUBpfv7RWs"

Write-Host "Fetching transcript JSON from Supabase..." -ForegroundColor Cyan
try {
    $transcriptJson = Invoke-RestMethod -Uri $TRANSCRIPT_JSON_URL -Method Get
    Write-Host "Transcript loaded: $($transcriptJson.segments.Count) segments" -ForegroundColor Green
} catch {
    Write-Host "Failed to fetch transcript JSON: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "Make sure your Supabase JSON URL is correct and accessible" -ForegroundColor Yellow
    exit 1
}

# Build the payload
$payload = @{
    input = @{
        video_url = $VIDEO_URL
        transcript_json = $transcriptJson
        language = "he"
        num_clips = 3
        min_duration = 20
        max_duration = 45
        vertical = $true
        subtitles = $true
    }
} | ConvertTo-Json -Depth 10

Write-Host "Submitting YouTube Shorts generation job..." -ForegroundColor Cyan
Write-Host "Video URL: $VIDEO_URL" -ForegroundColor Gray
Write-Host "Transcript segments: $($transcriptJson.segments.Count)" -ForegroundColor Gray

# 1. Submit the job
$jobId = (
    Invoke-RestMethod `
        -Method Post `
        -Uri "https://api.runpod.ai/v2/$($env:ENDPOINT_ID)/run" `
        -Headers @{ Authorization = "Bearer $($env:RUNPOD_API_KEY)" } `
        -Body $payload `
        -ContentType "application/json"
).id

Write-Host "Queued job ID:" $jobId -ForegroundColor Green

# 2. Poll until finished
Write-Host "Processing video (this may take 5-15 minutes)..." -ForegroundColor Yellow

do {
    $job = Invoke-RestMethod `
        -Uri "https://api.runpod.ai/v2/$($env:ENDPOINT_ID)/status/$jobId" `
        -Headers @{ Authorization = "Bearer $($env:RUNPOD_API_KEY)" }

    $timestamp = Get-Date -Format "HH:mm:ss"
    Write-Host "$timestamp Status:" $job.status -ForegroundColor Cyan
    
    if ($job.status -eq "FAILED") {
        Write-Host "Job failed!" -ForegroundColor Red
        Write-Host $job.error -ForegroundColor Red
        exit 1
    }
    
    if ($job.status -notin @("COMPLETED", "FAILED")) {
        Start-Sleep 10
    }
} until ($job.status -eq "COMPLETED")

# 3. Save the results
Write-Host "Processing complete! Saving results..." -ForegroundColor Green

$job.output | ConvertTo-Json -Depth 10 |
    Out-File -FilePath "shorts_result.json" -Encoding utf8

# 4. Display summary
Write-Host "Results written to shorts_result.json" -ForegroundColor Green
Write-Host ""
Write-Host "SUMMARY:" -ForegroundColor Magenta
Write-Host "Clips generated: $($job.output.clips_generated)"
Write-Host "Language: $($job.output.transcription.language)"
Write-Host "Transcript segments: $($job.output.transcription.segments)"
Write-Host "Analysis method: $($job.output.analysis.method)"

if ($job.output.analysis.themes) {
    Write-Host "Main themes: $($job.output.analysis.themes -join ', ')"
}

Write-Host ""
Write-Host "GENERATED CLIPS:" -ForegroundColor Magenta
foreach ($clip in $job.output.clips) {
    Write-Host "   $($clip.index). $($clip.title)" -ForegroundColor White
    Write-Host "      Duration: $($clip.duration)s | Score: $($clip.score)/10" -ForegroundColor Gray
    Write-Host "      Context: $($clip.context_dependency)" -ForegroundColor Gray
}

Write-Host ""
Write-Host "Test completed! Check shorts_result.json for full details." -ForegroundColor Green