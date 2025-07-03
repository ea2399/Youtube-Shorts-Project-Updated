# Quick test script - YouTube Shorts Generator
# Set your credentials and run!

# Set your RunPod credentials
$env:RUNPOD_API_KEY = ""your_runpod_api_key""  # Replace with your actual API key
$env:ENDPOINT_ID    = "i3fvz5sqdc0e7p"   # Replace with your actual endpoint ID (removed trailing space)

# 1. Run the job --> capture the ID
Write-Host "Submitting YouTube Shorts generation job..." -ForegroundColor Cyan

$jobId = (
    Invoke-RestMethod `
        -Method Post `
        -Uri "https://api.runpod.ai/v2/$($env:ENDPOINT_ID)/run" `
        -Headers @{ Authorization = "Bearer $($env:RUNPOD_API_KEY)" } `
        -Body (Get-Content -Raw "payloads\torah_lecture_basic.json") `
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