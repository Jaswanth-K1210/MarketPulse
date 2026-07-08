namespace MarketPulse.Gateway.Models;

public class ReportRequest
{
    /// <summary>excel | pdf</summary>
    public string ReportType           { get; set; } = "excel";
    public bool   IncludeAlerts        { get; set; } = true;
    public bool   IncludeRelationships { get; set; } = true;
    public bool   IncludeMaintenance   { get; set; } = true;
    public string Title                { get; set; } = "MarketPulse MTU Intelligence Report";
}
