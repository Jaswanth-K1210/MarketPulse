namespace MarketPulse.Gateway.Models;

public class EquipmentHealth
{
    public string   EngineId        { get; set; } = string.Empty;
    public string   Model           { get; set; } = string.Empty;
    public string   Sector          { get; set; } = string.Empty;
    public int      HealthScore     { get; set; }   // 0-100
    public string   Status          { get; set; } = string.Empty;   // Healthy | Warning | Critical
    public DateTime LastServiceDate { get; set; }
    public DateTime NextServiceDue  { get; set; }
    public double   OperatingHours  { get; set; }
    public List<string> ActiveAlerts { get; set; } = new();
    public Dictionary<string, double> SensorReadings { get; set; } = new();
}

public class FleetHealthSummary
{
    public int    TotalUnits       { get; set; }
    public int    Healthy          { get; set; }
    public int    Warning          { get; set; }
    public int    Critical         { get; set; }
    public int    AverageHealthScore { get; set; }
    public string CriticalUnit     { get; set; } = string.Empty;
    public string OverallStatus    { get; set; } = string.Empty;
    public List<EquipmentHealth> Units { get; set; } = new();
}
