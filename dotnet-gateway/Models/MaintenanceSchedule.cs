namespace MarketPulse.Gateway.Models;

public class MaintenanceSchedule
{
    public string   EngineId        { get; set; } = string.Empty;
    public string   Model           { get; set; } = string.Empty;
    public string   Sector          { get; set; } = string.Empty;   // Marine | Generator | Industrial
    public int      IntervalHours   { get; set; }
    public int      HoursRemaining  { get; set; }
    public DateTime NextServiceDue  { get; set; }
    public DateTime LastServiceDate { get; set; }
    public string   Status          { get; set; } = string.Empty;   // OnTrack | Warning | Overdue
    public string   Location        { get; set; } = string.Empty;
    public string   Technician      { get; set; } = string.Empty;
}
