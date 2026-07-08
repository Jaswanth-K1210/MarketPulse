namespace MarketPulse.Gateway.Models;

public class AlertDto
{
    public string  Id            { get; set; } = string.Empty;
    public string  Ticker        { get; set; } = string.Empty;
    public string  Severity      { get; set; } = "medium";
    public double  ImpactPercent { get; set; }
    public double  Confidence    { get; set; }
    public string  Description   { get; set; } = string.Empty;
    public string  Timestamp     { get; set; } = string.Empty;
    public string  Source        { get; set; } = string.Empty;
}
