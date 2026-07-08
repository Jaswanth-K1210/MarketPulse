using System.Diagnostics;
using System.Text;
using System.Text.Json;

namespace MarketPulse.Gateway.Services;

/// <summary>
/// Thin async wrapper around the Python/FastAPI backend.
/// All calls are logged with duration so latency is visible in Serilog / App Insights.
/// </summary>
public class PythonBackendService
{
    private readonly IHttpClientFactory _factory;
    private readonly ILogger<PythonBackendService> _log;

    private static readonly JsonSerializerOptions _json = new()
    {
        PropertyNameCaseInsensitive = true,
        WriteIndented = false
    };

    public PythonBackendService(IHttpClientFactory factory, ILogger<PythonBackendService> log)
    {
        _factory = factory;
        _log     = log;
    }

    private HttpClient Client => _factory.CreateClient("PythonBackend");

    // ── GET helpers ──────────────────────────────────────────────────────────

    public async Task<string> GetRawAsync(string path, CancellationToken ct = default)
    {
        var sw = Stopwatch.StartNew();
        try
        {
            var response = await Client.GetAsync(path, ct);
            response.EnsureSuccessStatusCode();
            var body = await response.Content.ReadAsStringAsync(ct);
            _log.LogInformation("GET {Path} → {Status} in {Ms}ms", path, (int)response.StatusCode, sw.ElapsedMilliseconds);
            return body;
        }
        catch (Exception ex)
        {
            _log.LogError(ex, "GET {Path} failed after {Ms}ms", path, sw.ElapsedMilliseconds);
            throw;
        }
    }

    public async Task<T?> GetAsync<T>(string path, CancellationToken ct = default)
    {
        var json = await GetRawAsync(path, ct);
        return JsonSerializer.Deserialize<T>(json, _json);
    }

    // ── POST helpers ─────────────────────────────────────────────────────────

    public async Task<string> PostRawAsync(string path, object? body = null, CancellationToken ct = default)
    {
        var sw = Stopwatch.StartNew();
        try
        {
            var content  = body is null
                ? new StringContent("{}", Encoding.UTF8, "application/json")
                : new StringContent(JsonSerializer.Serialize(body, _json), Encoding.UTF8, "application/json");

            var response = await Client.PostAsync(path, content, ct);
            response.EnsureSuccessStatusCode();
            var result = await response.Content.ReadAsStringAsync(ct);
            _log.LogInformation("POST {Path} → {Status} in {Ms}ms", path, (int)response.StatusCode, sw.ElapsedMilliseconds);
            return result;
        }
        catch (Exception ex)
        {
            _log.LogError(ex, "POST {Path} failed after {Ms}ms", path, sw.ElapsedMilliseconds);
            throw;
        }
    }

    public async Task<T?> PostAsync<T>(string path, object? body = null, CancellationToken ct = default)
    {
        var json = await PostRawAsync(path, body, ct);
        return JsonSerializer.Deserialize<T>(json, _json);
    }

    // ── Named methods ────────────────────────────────────────────────────────

    public Task<string> GetAlertsAsync(string? severity = null, int limit = 15, CancellationToken ct = default)
    {
        var qs = $"?limit={limit}" + (severity is not null ? $"&severity={severity}" : "");
        return GetRawAsync($"/api/alerts{qs}", ct);
    }

    public Task<string> GetHealthAsync(CancellationToken ct = default)
        => GetRawAsync("/api/health", ct);

    public Task<string> GetStatsAsync(CancellationToken ct = default)
        => GetRawAsync("/api/stats", ct);

    public Task<string> GetRelationshipsAsync(string ticker, CancellationToken ct = default)
        => GetRawAsync($"/api/relationships?ticker={ticker}", ct);

    public Task<string> GetPortfolioAsync(string? userName = null, CancellationToken ct = default)
    {
        var qs = userName is not null ? $"?user_name={Uri.EscapeDataString(userName)}" : "";
        return GetRawAsync($"/api/portfolio{qs}", ct);
    }

    public Task<string> AnalyzeAsync(object request, CancellationToken ct = default)
        => PostRawAsync("/api/run-intelligence", request, ct);

    public Task<string> FetchAndAnalyzeAsync(int limit = 10, CancellationToken ct = default)
        => PostRawAsync($"/api/fetch-and-analyze?limit={limit}", null, ct);
}
