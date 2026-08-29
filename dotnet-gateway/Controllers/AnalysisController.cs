using Microsoft.AspNetCore.Mvc;
using MarketPulse.Gateway.Models;
using MarketPulse.Gateway.Services;

namespace MarketPulse.Gateway.Controllers;

[ApiController]
[Route("api/[controller]")]
public class AnalysisController : ControllerBase
{
    private readonly PythonBackendService _backend;
    private readonly ILogger<AnalysisController> _log;

    public AnalysisController(PythonBackendService backend, ILogger<AnalysisController> log)
    {
        _backend = backend;
        _log     = log;
    }

    /// <summary>Run the LangGraph supply-chain intelligence pipeline.</summary>
    [HttpPost("run")]
    [ProducesResponseType(typeof(AnalysisResponse), 200)]
    [ProducesResponseType(400)]
    [ProducesResponseType(502)]
    public async Task<IActionResult> RunAnalysis([FromBody] AnalysisRequest req, CancellationToken ct)
    {
        if (req.Tickers is null || req.Tickers.Count == 0)
            return BadRequest(new { error = "At least one ticker is required." });

        try
        {
            _log.LogInformation("Analysis requested for {Count} tickers by {User}",
                req.Tickers.Count, req.UserName ?? "anonymous");

            var raw = await _backend.AnalyzeAsync(req, ct);
            return Content(raw, "application/json");
        }
        catch (HttpRequestException ex)
        {
            _log.LogError(ex, "Python backend unreachable during analysis");
            return StatusCode(502, new { error = "Intelligence pipeline unavailable.", detail = ex.Message });
        }
    }

    /// <summary>Fetch latest news and run the full pipeline automatically.</summary>
    [HttpPost("fetch-and-analyze")]
    [ProducesResponseType(200)]
    [ProducesResponseType(502)]
    public async Task<IActionResult> FetchAndAnalyze([FromQuery] int limit = 10, CancellationToken ct = default)
    {
        try
        {
            var raw = await _backend.FetchAndAnalyzeAsync(limit, ct);
            return Content(raw, "application/json");
        }
        catch (HttpRequestException ex)
        {
            _log.LogError(ex, "Python backend unreachable during fetch-and-analyze");
            return StatusCode(502, new { error = "Intelligence pipeline unavailable.", detail = ex.Message });
        }
    }

    /// <summary>Proxy live stats from the Python backend.</summary>
    [HttpGet("stats")]
    [ProducesResponseType(200)]
    public async Task<IActionResult> GetStats(CancellationToken ct)
    {
        try
        {
            var raw = await _backend.GetStatsAsync(ct);
            return Content(raw, "application/json");
        }
        catch (HttpRequestException ex)
        {
            return StatusCode(502, new { error = "Stats unavailable.", detail = ex.Message });
        }
    }

    /// <summary>Proxy ticker relationship graph from the Python backend.</summary>
    [HttpGet("relationships/{ticker}")]
    [ProducesResponseType(200)]
    public async Task<IActionResult> GetRelationships(string ticker, CancellationToken ct)
    {
        try
        {
            var raw = await _backend.GetRelationshipsAsync(ticker, ct);
            return Content(raw, "application/json");
        }
        catch (HttpRequestException ex)
        {
            return StatusCode(502, new { error = "Relationships unavailable.", detail = ex.Message });
        }
    }
}
