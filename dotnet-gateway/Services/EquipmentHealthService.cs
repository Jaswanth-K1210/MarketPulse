using MarketPulse.Gateway.Models;

namespace MarketPulse.Gateway.Services;

/// <summary>
/// Equipment health monitoring for the MTU engine fleet.
/// Health scores are derived from operating hours, maintenance status,
/// and simulated sensor readings (oil pressure, coolant temp, vibration).
/// </summary>
public class EquipmentHealthService
{
    private static readonly List<EquipmentHealth> _units = new()
    {
        new()
        {
            EngineId       = "MTU-4000-M93L-001",
            Model          = "MTU 16V 4000 M93L",
            Sector         = "Marine",
            HealthScore    = 91,
            Status         = "Healthy",
            LastServiceDate = DateTime.UtcNow.AddDays(-39),
            NextServiceDue = DateTime.UtcNow.AddDays(18),
            OperatingHours = 4_312,
            ActiveAlerts   = new List<string>(),
            SensorReadings = new()
            {
                ["oil_pressure_bar"]   = 4.2,
                ["coolant_temp_c"]     = 82.5,
                ["vibration_mm_s"]     = 1.1,
                ["exhaust_temp_c"]     = 410.0,
                ["fuel_consumption_lh"]= 185.0
            }
        },
        new()
        {
            EngineId       = "MTU-2000-M96-002",
            Model          = "MTU 12V 2000 M96",
            Sector         = "Marine",
            HealthScore    = 74,
            Status         = "Warning",
            LastServiceDate = DateTime.UtcNow.AddDays(-88),
            NextServiceDue = DateTime.UtcNow.AddDays(5),
            OperatingHours = 6_895,
            ActiveAlerts   = new List<string> { "Service due in 5 days", "Oil pressure slightly low" },
            SensorReadings = new()
            {
                ["oil_pressure_bar"]   = 3.6,
                ["coolant_temp_c"]     = 88.0,
                ["vibration_mm_s"]     = 1.9,
                ["exhaust_temp_c"]     = 435.0,
                ["fuel_consumption_lh"]= 142.0
            }
        },
        new()
        {
            EngineId       = "MTU-4000-G63-003",
            Model          = "MTU 20V 4000 G63",
            Sector         = "Generator",
            HealthScore    = 41,
            Status         = "Critical",
            LastServiceDate = DateTime.UtcNow.AddDays(-148),
            NextServiceDue = DateTime.UtcNow.AddDays(-8),
            OperatingHours = 9_240,
            ActiveAlerts   = new List<string>
            {
                "OVERDUE: Service 120h past interval",
                "High vibration detected (3.8 mm/s)",
                "Coolant temperature elevated",
                "Recommend immediate shutdown for inspection"
            },
            SensorReadings = new()
            {
                ["oil_pressure_bar"]   = 3.1,
                ["coolant_temp_c"]     = 96.5,
                ["vibration_mm_s"]     = 3.8,
                ["exhaust_temp_c"]     = 478.0,
                ["fuel_consumption_lh"]= 195.0
            }
        },
        new()
        {
            EngineId       = "MTU-2000-G65-004",
            Model          = "MTU 8V 2000 G65",
            Sector         = "Generator",
            HealthScore    = 78,
            Status         = "Warning",
            LastServiceDate = DateTime.UtcNow.AddDays(-59),
            NextServiceDue = DateTime.UtcNow.AddDays(4),
            OperatingHours = 3_110,
            ActiveAlerts   = new List<string> { "Service due in 4 days" },
            SensorReadings = new()
            {
                ["oil_pressure_bar"]   = 3.9,
                ["coolant_temp_c"]     = 85.0,
                ["vibration_mm_s"]     = 1.4,
                ["exhaust_temp_c"]     = 420.0,
                ["fuel_consumption_lh"]= 98.0
            }
        },
        new()
        {
            EngineId       = "MTU-2000-G65-005",
            Model          = "MTU 16V 2000 G65",
            Sector         = "Industrial",
            HealthScore    = 88,
            Status         = "Healthy",
            LastServiceDate = DateTime.UtcNow.AddDays(-73),
            NextServiceDue = DateTime.UtcNow.AddDays(12),
            OperatingHours = 5_560,
            ActiveAlerts   = new List<string>(),
            SensorReadings = new()
            {
                ["oil_pressure_bar"]   = 4.1,
                ["coolant_temp_c"]     = 81.0,
                ["vibration_mm_s"]     = 1.2,
                ["exhaust_temp_c"]     = 408.0,
                ["fuel_consumption_lh"]= 168.0
            }
        }
    };

    public FleetHealthSummary GetFleetSummary() => new()
    {
        TotalUnits         = _units.Count,
        Healthy            = _units.Count(u => u.Status == "Healthy"),
        Warning            = _units.Count(u => u.Status == "Warning"),
        Critical           = _units.Count(u => u.Status == "Critical"),
        AverageHealthScore = (int)_units.Average(u => u.HealthScore),
        CriticalUnit       = _units.FirstOrDefault(u => u.Status == "Critical")?.Model ?? "None",
        OverallStatus      = _units.Any(u => u.Status == "Critical") ? "Critical"
                           : _units.Any(u => u.Status == "Warning")  ? "Warning" : "Healthy",
        Units              = _units
    };

    public EquipmentHealth? GetById(string engineId)
        => _units.FirstOrDefault(u => u.EngineId.Equals(engineId, StringComparison.OrdinalIgnoreCase));

    public IReadOnlyList<EquipmentHealth> GetCritical()
        => _units.Where(u => u.Status == "Critical").ToList();

    public IReadOnlyList<EquipmentHealth> GetByStatus(string status)
        => _units.Where(u => u.Status.Equals(status, StringComparison.OrdinalIgnoreCase)).ToList();
}
