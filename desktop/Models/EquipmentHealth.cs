namespace MarketPulse.Desktop.Models;

public class EquipmentHealth
{
    public string   EngineId         { get; set; } = string.Empty;
    public string   Model            { get; set; } = string.Empty;
    public string   Sector           { get; set; } = string.Empty;
    public int      HealthScore      { get; set; }
    public string   Status           { get; set; } = string.Empty;
    public DateTime LastServiceDate  { get; set; }
    public DateTime NextServiceDue   { get; set; }
    public double   OperatingHours   { get; set; }
    public List<string>             ActiveAlerts   { get; set; } = new();
    public Dictionary<string,double> SensorReadings { get; set; } = new();

    public string AlertSummary => ActiveAlerts.Count > 0
        ? string.Join("; ", ActiveAlerts)
        : "None";

    public string NextServiceFormatted => NextServiceDue.ToString("yyyy-MM-dd");
}

public class FleetHealthSummary
{
    public int    TotalUnits         { get; set; }
    public int    Healthy            { get; set; }
    public int    Warning            { get; set; }
    public int    Critical           { get; set; }
    public int    AverageHealthScore { get; set; }
    public string CriticalUnit       { get; set; } = string.Empty;
    public string OverallStatus      { get; set; } = string.Empty;
    public List<EquipmentHealth> Units { get; set; } = new();
}
