namespace MarketPulse.Desktop.Models;

public class MaintenanceSchedule
{
    public string   EngineId        { get; set; } = string.Empty;
    public string   Model           { get; set; } = string.Empty;
    public string   Sector          { get; set; } = string.Empty;
    public int      IntervalHours   { get; set; }
    public int      HoursRemaining  { get; set; }
    public DateTime NextServiceDue  { get; set; }
    public DateTime LastServiceDate { get; set; }
    public string   Status          { get; set; } = string.Empty;
    public string   Location        { get; set; } = string.Empty;
    public string   Technician      { get; set; } = string.Empty;

    public string NextServiceFormatted  => NextServiceDue.ToString("yyyy-MM-dd");
    public string LastServiceFormatted  => LastServiceDate.ToString("yyyy-MM-dd");
    public string HoursDisplay          => HoursRemaining < 0
        ? $"OVERDUE {-HoursRemaining}h"
        : $"{HoursRemaining}h left";
}
