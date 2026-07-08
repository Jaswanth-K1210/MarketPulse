namespace MarketPulse.Gateway.Models;

public class AnalysisRequest
{
    public List<string> Tickers           { get; set; } = new();
    public string       EventDescription  { get; set; } = string.Empty;
    public string       UserName          { get; set; } = "enterprise_user";
}

public class AnalysisResponse
{
    public string  Status     { get; set; } = string.Empty;
    public bool    AlertCreated { get; set; }
    public string? AlertId    { get; set; }
    public object? Impact     { get; set; }
    public double  Confidence { get; set; }
    public string  ProcessedBy { get; set; } = "DotNet-Gateway";
}
