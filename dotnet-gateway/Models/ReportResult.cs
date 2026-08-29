namespace MarketPulse.Gateway.Models;

public class ReportResult
{
    public string   ReportId      { get; set; } = string.Empty;
    public string   DownloadUrl   { get; set; } = string.Empty;
    public string   FileName      { get; set; } = string.Empty;
    public string   ReportType    { get; set; } = string.Empty;
    public long     FileSizeBytes { get; set; }
    public DateTime GeneratedAt   { get; set; } = DateTime.UtcNow;
    public string   Status        { get; set; } = "ready";
}
