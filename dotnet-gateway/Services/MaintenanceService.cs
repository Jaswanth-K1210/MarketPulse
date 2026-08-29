using MarketPulse.Gateway.Models;

namespace MarketPulse.Gateway.Services;

/// <summary>
/// MRO (Maintenance, Repair, Overhaul) scheduling for the MTU engine fleet.
/// Data is seeded with realistic MTU engine specs; in production this would
/// sync with a CMMS (Computerised Maintenance Management System).
/// </summary>
public class MaintenanceService
{
    private readonly ILogger<MaintenanceService> _log;

    public MaintenanceService(ILogger<MaintenanceService> log) => _log = log;

    private static readonly List<MaintenanceSchedule> _fleet = new()
    {
        new()
        {
            EngineId       = "MTU-4000-M93L-001",
            Model          = "MTU 16V 4000 M93L",
            Sector         = "Marine",
            IntervalHours  = 500,
            HoursRemaining = 312,
            NextServiceDue = DateTime.UtcNow.AddDays(18),
            LastServiceDate = DateTime.UtcNow.AddDays(-39),
            Status         = "OnTrack",
            Location       = "Hamburg, Germany",
            Technician     = "Hans Müller"
        },
        new()
        {
            EngineId       = "MTU-2000-M96-002",
            Model          = "MTU 12V 2000 M96",
            Sector         = "Marine",
            IntervalHours  = 750,
            HoursRemaining = 85,
            NextServiceDue = DateTime.UtcNow.AddDays(5),
            LastServiceDate = DateTime.UtcNow.AddDays(-88),
            Status         = "Warning",
            Location       = "Rotterdam, Netherlands",
            Technician     = "Jan de Vries"
        },
        new()
        {
            EngineId       = "MTU-4000-G63-003",
            Model          = "MTU 20V 4000 G63",
            Sector         = "Generator",
            IntervalHours  = 1000,
            HoursRemaining = -120,  // negative = overdue
            NextServiceDue = DateTime.UtcNow.AddDays(-8),
            LastServiceDate = DateTime.UtcNow.AddDays(-148),
            Status         = "Overdue",
            Location       = "Frankfurt, Germany",
            Technician     = "Unassigned"
        },
        new()
        {
            EngineId       = "MTU-2000-G65-004",
            Model          = "MTU 8V 2000 G65",
            Sector         = "Generator",
            IntervalHours  = 500,
            HoursRemaining = 80,
            NextServiceDue = DateTime.UtcNow.AddDays(4),
            LastServiceDate = DateTime.UtcNow.AddDays(-59),
            Status         = "Warning",
            Location       = "Munich, Germany",
            Technician     = "Klaus Weber"
        },
        new()
        {
            EngineId       = "MTU-2000-G65-005",
            Model          = "MTU 16V 2000 G65",
            Sector         = "Industrial",
            IntervalHours  = 750,
            HoursRemaining = 200,
            NextServiceDue = DateTime.UtcNow.AddDays(12),
            LastServiceDate = DateTime.UtcNow.AddDays(-73),
            Status         = "OnTrack",
            Location       = "Stuttgart, Germany",
            Technician     = "Erik Schmidt"
        }
    };

    public IReadOnlyList<MaintenanceSchedule> GetAll() => _fleet.AsReadOnly();

    public IReadOnlyList<MaintenanceSchedule> GetOverdue()
        => _fleet.Where(e => e.Status == "Overdue").ToList();

    public IReadOnlyList<MaintenanceSchedule> GetWarning()
        => _fleet.Where(e => e.Status == "Warning" || e.Status == "Overdue").ToList();

    public MaintenanceSchedule? GetById(string engineId)
        => _fleet.FirstOrDefault(e => e.EngineId.Equals(engineId, StringComparison.OrdinalIgnoreCase));

    public TriggerResult TriggerMaintenance(string engineId)
    {
        var eng = GetById(engineId);
        if (eng is null)
            return new TriggerResult { Success = false, Message = $"Engine {engineId} not found." };

        _log.LogInformation("Maintenance triggered for {EngineId} ({Model})", eng.EngineId, eng.Model);
        return new TriggerResult
        {
            Success   = true,
            EngineId  = eng.EngineId,
            Model     = eng.Model,
            Message   = $"Maintenance work order created for {eng.Model} at {eng.Location}.",
            WorkOrder = $"WO-{DateTime.UtcNow:yyyyMMdd}-{eng.EngineId.Split('-').Last()}"
        };
    }
}

public class TriggerResult
{
    public bool   Success   { get; set; }
    public string EngineId  { get; set; } = string.Empty;
    public string Model     { get; set; } = string.Empty;
    public string Message   { get; set; } = string.Empty;
    public string WorkOrder { get; set; } = string.Empty;
}
