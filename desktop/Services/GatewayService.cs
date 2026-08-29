using System.Net.Http.Json;
using System.Text.Json;
using MarketPulse.Desktop.Models;

namespace MarketPulse.Desktop.Services;

public class GatewayService
{
    private readonly HttpClient _http;

    private static readonly JsonSerializerOptions _json = new()
    {
        PropertyNameCaseInsensitive = true
    };

    public string BaseUrl { get; }

    public GatewayService(string baseUrl = "http://localhost:5000")
    {
        BaseUrl = baseUrl;
        _http   = new HttpClient { BaseAddress = new Uri(baseUrl), Timeout = TimeSpan.FromSeconds(30) };
    }

    public async Task<AlertsResponse?> GetAlertsAsync(string? severity = null, int limit = 20)
    {
        var qs = $"?limit={limit}" + (severity != null ? $"&severity={severity}" : "");
        return await _http.GetFromJsonAsync<AlertsResponse>($"/api/alerts{qs}", _json);
    }

    public async Task<FleetHealthSummary?> GetFleetHealthAsync()
        => await _http.GetFromJsonAsync<FleetHealthSummary>("/api/equipment/health", _json);

    public async Task<List<MaintenanceSchedule>?> GetMaintenanceScheduleAsync()
        => await _http.GetFromJsonAsync<List<MaintenanceSchedule>>("/api/maintenance/schedule", _json);

    public async Task<(bool Success, string Message)> TriggerMaintenanceAsync(string engineId)
    {
        var resp = await _http.PostAsync($"/api/maintenance/trigger/{engineId}", null);
        var body = await resp.Content.ReadAsStringAsync();
        return (resp.IsSuccessStatusCode, body);
    }

    public async Task<(bool Success, string? Url, string? Error)> GenerateReportAsync(string type)
    {
        var payload = new { reportType = type, includeAlerts = true, includeMaintenance = true, includeRelationships = true };
        var resp = await _http.PostAsJsonAsync("/api/reports/generate", payload, _json);
        if (!resp.IsSuccessStatusCode)
            return (false, null, await resp.Content.ReadAsStringAsync());

        using var doc = JsonDocument.Parse(await resp.Content.ReadAsStringAsync());
        var url = doc.RootElement.TryGetProperty("downloadUrl", out var u) ? u.GetString() : null;
        return (true, url, null);
    }

    public async Task<bool> CheckHealthAsync()
    {
        try
        {
            var resp = await _http.GetAsync("/health");
            return resp.IsSuccessStatusCode;
        }
        catch { return false; }
    }
}
