using Microsoft.AspNetCore.Mvc;
using Microsoft.Extensions.Caching.Memory;
using MarketPulse.Gateway.Services;

namespace MarketPulse.Gateway.Controllers;

[ApiController]
[Route("api/[controller]")]
public class AlertsController : ControllerBase
{
    private readonly PythonBackendService _backend;
    private readonly IMemoryCache _cache;
    private readonly ILogger<AlertsController> _log;

    private static readonly TimeSpan CacheTtl = TimeSpan.FromSeconds(30);

    public AlertsController(
        PythonBackendService backend,
        IMemoryCache cache,
        ILogger<AlertsController> log)
    {
        _backend = backend;
        _cache   = cache;
        _log     = log;
    }

    /// <summary>Live supply-chain alerts — 30-second cache to avoid hammering the Python backend.</summary>
    [HttpGet]
    [ProducesResponseType(200)]
    [ProducesResponseType(502)]
    public async Task<IActionResult> GetAlerts(
        [FromQuery] string? severity = null,
        [FromQuery] int limit = 15,
        CancellationToken ct = default)
    {
        var cacheKey = $"alerts:{severity ?? "all"}:{limit}";

        if (_cache.TryGetValue(cacheKey, out string? cached))
        {
            _log.LogDebug("Alerts cache hit for key {Key}", cacheKey);
            return Content(cached!, "application/json");
        }

        try
        {
            var raw = await _backend.GetAlertsAsync(severity, limit, ct);
            _cache.Set(cacheKey, raw, CacheTtl);
            return Content(raw, "application/json");
        }
        catch (HttpRequestException ex)
        {
            _log.LogError(ex, "Python backend unreachable while fetching alerts");
            return StatusCode(502, new { error = "Alert feed unavailable.", detail = ex.Message });
        }
    }

    /// <summary>Portfolio-specific alerts for a given user.</summary>
    [HttpGet("portfolio/{userName}")]
    [ProducesResponseType(200)]
    [ProducesResponseType(502)]
    public async Task<IActionResult> GetPortfolioAlerts(string userName, CancellationToken ct)
    {
        var cacheKey = $"portfolio-alerts:{userName}";

        if (_cache.TryGetValue(cacheKey, out string? cached))
            return Content(cached!, "application/json");

        try
        {
            var raw = await _backend.GetPortfolioAsync(userName, ct);
            _cache.Set(cacheKey, raw, CacheTtl);
            return Content(raw, "application/json");
        }
        catch (HttpRequestException ex)
        {
            return StatusCode(502, new { error = "Portfolio alerts unavailable.", detail = ex.Message });
        }
    }

    /// <summary>Force-invalidate the alerts cache (e.g., after a pipeline run).</summary>
    [HttpPost("cache/invalidate")]
    [ProducesResponseType(200)]
    public IActionResult InvalidateCache()
    {
        // IMemoryCache doesn't support key enumeration; track evictable keys by prefix convention
        foreach (var limit in new[] { 10, 15, 20, 50 })
        {
            _cache.Remove($"alerts:all:{limit}");
            foreach (var sev in new[] { "low", "medium", "high", "critical" })
                _cache.Remove($"alerts:{sev}:{limit}");
        }

        _log.LogInformation("Alerts cache invalidated");
        return Ok(new { message = "Alert cache invalidated." });
    }
}
